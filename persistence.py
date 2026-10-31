"""Persistent accounts, email challenges, support inbox, audit log and delivery queue."""
import hashlib, hmac, io, json, os, re, secrets, threading, time
from pathlib import Path
import requests
from flask import abort, flash, g, jsonify, redirect, render_template, request, session, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from i18n import CATALOG, t
from service_i18n import STRINGS
CATALOG.update(STRINGS)
CATALOG.update({row["ru"]:row for row in STRINGS.values()})

SCHEMA='''
CREATE TABLE IF NOT EXISTS file_objects(name TEXT PRIMARY KEY,data BLOB NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS email_challenges(token TEXT PRIMARY KEY,email TEXT NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,telegram TEXT NOT NULL,language TEXT NOT NULL,code_hash TEXT NOT NULL,expires REAL NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,sent_at REAL NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rate_limits(key TEXT PRIMARY KEY,window_start REAL NOT NULL,count INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY,user_id INTEGER,action TEXT NOT NULL,target TEXT NOT NULL DEFAULT '',result INTEGER NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS support_messages(id INTEGER PRIMARY KEY,client_id INTEGER NOT NULL REFERENCES users(id),sender_id INTEGER NOT NULL REFERENCES users(id),body TEXT NOT NULL,created TEXT NOT NULL,read_at TEXT NOT NULL DEFAULT '',nonce TEXT NOT NULL,UNIQUE(sender_id,nonce));
CREATE INDEX IF NOT EXISTS support_thread ON support_messages(client_id,id);
CREATE TABLE IF NOT EXISTS notification_outbox(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),chat_id TEXT NOT NULL DEFAULT '',payload TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,next_try REAL NOT NULL DEFAULT 0,lease_until REAL NOT NULL DEFAULT 0,last_error TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,sent_at TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS notification_pending ON notification_outbox(state,next_try);
'''

def install_persistence(app,db,stamp,login_required,admin_required):
    service=Services(app,db,stamp)
    app.extensions['services']=service
    with app.app_context(): service.migrate()
    f=app.extensions['mops_features']
    app.view_functions['register']=service.register
    app.view_functions['profile']=f.signed_in(service.profile)
    app.view_functions['approve']=admin_required(service.approve)
    app.add_url_rule('/verify-email','verify_email',service.verify_email,methods=['GET','POST'])
    app.add_url_rule('/verify-email/resend','resend_email',service.resend_email,methods=['POST'])
    app.add_url_rule('/support','support',f.signed_in(service.support),methods=['GET','POST'])
    app.add_url_rule('/support/messages','support_messages',f.signed_in(service.support_messages))
    app.add_url_rule('/admin/users','all_users',admin_required(service.all_users))
    app.add_url_rule('/admin/logs','audit_log',admin_required(service.audit_log))
    app.add_url_rule('/admin/notifications/retry','retry_notifications',admin_required(service.retry_notifications),methods=['POST'])
    app.before_request(service.before)
    app.after_request(service.after)
    app.context_processor(service.context)
    # Old files are imported once when present; new files are stored transactionally in the database.
    f.save_file=service.save_file
    from archive_storage import install_archive
    install_archive(app,db,stamp,admin_required)

class Services:
    def __init__(self,app,db,stamp):
        self.app,self.db,self.stamp=app,db,stamp
        for key,default in [('EMAIL_PROVIDER','resend'),('EMAIL_API_KEY',''),('EMAIL_FROM',''),('EMAIL_FROM_NAME','Mops Parcel')]:
            app.config.setdefault(key,os.getenv(key,default))
        self.lock=threading.Lock()
        self.wake_event=threading.Event()
        self.stop_event=threading.Event()
        # Periodic checks must leave enough idle time for serverless PostgreSQL.
        try: interval=int(app.config.get('BACKGROUND_CHECK_SECONDS',os.getenv('BACKGROUND_CHECK_SECONDS','3600')))
        except (TypeError,ValueError): interval=3600
        self.check_interval=max(600,min(interval,86400))
    def start_worker(self):
        enabled=self.app.config.get('NOTIFICATION_WORKER',os.getenv('NOTIFICATION_WORKER','true'))
        if not self.app.testing and str(enabled).lower()=='true':
            threading.Thread(target=self.worker,name='mops-background',daemon=True).start()
    def wake(self):self.wake_event.set()
    def linked(self,uid):
        c=self.db()
        c.execute("UPDATE notification_outbox SET next_try=0 WHERE user_id=? AND state='pending'",(uid,))
        c.execute("UPDATE report_archives SET next_try=0 WHERE order_id IN (SELECT id FROM orders WHERE user_id=?) AND state IN ('pending','confirmed')",(uid,))
        c.commit();self.wake()
    def migrate(self):
        from archive_storage import SCHEMA as ARCHIVE_SCHEMA
        c=self.db();c.executescript(SCHEMA+ARCHIVE_SCHEMA)
        c.execute('BEGIN IMMEDIATE')
        if 'window_start' not in {r[1] for r in c.execute('PRAGMA table_info(rate_limits)')}:
            c.execute('ALTER TABLE rate_limits ADD COLUMN window_start REAL NOT NULL DEFAULT 0')
        columns={r[1] for r in c.execute('PRAGMA table_info(users)')}
        if 'email_verified' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0')
            # Existing accounts keep access, but are explicitly marked legacy (2), not falsely verified (1).
            c.execute('UPDATE users SET email_verified=2')
        c.commit()
        folder=Path(self.app.config['UPLOAD_FOLDER'])
        for file in folder.iterdir():
            if file.is_file() and file.suffix.lower() in ('.jpg','.jpeg','.png','.webp','.pdf') and file.stat().st_size<=12*1024*1024:
                if c.execute("SELECT 1 FROM report_archives WHERE name=? AND cleaned_at<>''",(file.name,)).fetchone():continue
                if not c.execute('SELECT 1 FROM file_objects WHERE name=?',(file.name,)).fetchone():
                    c.execute('INSERT INTO file_objects(name,data,created) VALUES(?,?,?)',(file.name,file.read_bytes(),self.stamp()))
        c.commit()
    def save_file(self,validated,tag):
        data,ext=validated;name=tag+'_'+secrets.token_hex(16)+ext
        self.db().execute('INSERT INTO file_objects(name,data,created) VALUES(?,?,?)',(name,data,self.stamp()))
        return name
    def file_bytes(self,name):
        if Path(name).name!=name: return None
        row=self.db().execute('SELECT data FROM file_objects WHERE name=?',(name,)).fetchone()
        if row: return bytes(row[0])
        p=Path(self.app.config['UPLOAD_FOLDER'])/name
        return p.read_bytes() if p.is_file() else None
    def digest(self,value): return hmac.new(self.app.secret_key.encode(),value.encode(),hashlib.sha256).hexdigest()
    def limited(self,key,limit,seconds):
        c=self.db();now=time.time();c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT window_start,count FROM rate_limits WHERE key=?',(key,)).fetchone()
        if row and row['window_start']>now-seconds and row['count']>=limit:
            c.rollback();return True
        if row and row['window_start']>now-seconds:
            c.execute('UPDATE rate_limits SET count=count+1 WHERE key=?',(key,))
        else:
            c.execute('INSERT INTO rate_limits(key,window_start,count) VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET window_start=excluded.window_start,count=1',(key,now))
        c.commit();return False
    def ip_key(self):
        # Do not trust arbitrary forwarded headers; use the server's peer identity.
        return self.digest(request.remote_addr or 'unknown')
    def email_send(self,email,code,lang):
        subject=t('svc.email_subject',lang);body=t('svc.email_body',lang,code=code)
        transport=self.app.config.get('EMAIL_TRANSPORT') if self.app.testing else None
        if transport: return bool(transport(email,subject,body))
        key=self.app.config['EMAIL_API_KEY'];sender=self.app.config['EMAIL_FROM']
        if not key or not sender: return False
        try:
            if self.app.config['EMAIL_PROVIDER']=='brevo':
                r=requests.post('https://api.brevo.com/v3/smtp/email',headers={'api-key':key},json={'sender':{'email':sender,'name':self.app.config['EMAIL_FROM_NAME']},'to':[{'email':email}],'subject':subject,'textContent':body},timeout=(5,15))
            else:
                r=requests.post('https://api.resend.com/emails',headers={'Authorization':'Bearer '+key},json={'from':self.app.config['EMAIL_FROM_NAME']+' <'+sender+'>','to':[email],'subject':subject,'text':body},timeout=(5,15))
            return 200<=r.status_code<300
        except requests.RequestException: return False
    def register(self):
        if g.user: return redirect(url_for('profile'))
        if request.method=='POST':
            name=request.form.get('name','').strip()[:200];email=request.form.get('email','').strip().lower()
            password=request.form.get('password','');tg=request.form.get('telegram','').strip().lstrip('@')
            if not name or len(email)>254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or not 8<=len(password)<=256 or (tg and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{4,31}',tg)):
                flash(t('svc.invalid_registration'),'error')
            elif self.limited('register:'+self.ip_key(),20,3600) or self.limited('email:'+self.digest(email),5,3600):
                flash(t('svc.rate_limit'),'error')
            elif self.db().execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
                flash(t('svc.email_exists'),'error')
            else:
                token=secrets.token_urlsafe(32);code=f'{secrets.randbelow(1000000):06d}';now=time.time()
                c=self.db()
                c.execute('DELETE FROM email_challenges WHERE created<?',(now-86400,))
                c.execute('INSERT INTO email_challenges(token,email,name,password,telegram,language,code_hash,expires,sent_at,created) VALUES(?,?,?,?,?,?,?,?,?,?)',(token,email,name,generate_password_hash(password),tg,g.lang,self.digest(token+code),now+600,now,now));c.commit()
                if self.email_send(email,code,g.lang):
                    session['email_challenge']=token;return redirect(url_for('verify_email'))
                c.execute('DELETE FROM email_challenges WHERE token=?',(token,));c.commit()
                flash(t('svc.email_failed'),'error')
        return render_template('register.html')
    def challenge(self):
        return self.db().execute('SELECT * FROM email_challenges WHERE token=?',(session.get('email_challenge',''),)).fetchone()
    def verify_email(self):
        row=self.challenge()
        if not row: return redirect(url_for('register'))
        if request.method=='POST':
            c=self.db();c.execute('BEGIN IMMEDIATE');row=self.challenge();now=time.time()
            if not row: c.rollback();return redirect(url_for('login'))
            code=request.form.get('code','').strip()
            if row['attempts']>=5 or row['expires']<now:
                c.rollback();flash(t('svc.code_expired'),'error')
            elif not re.fullmatch(r'\d{6}',code) or not hmac.compare_digest(row['code_hash'],self.digest(row['token']+code)):
                c.execute('UPDATE email_challenges SET attempts=attempts+1 WHERE token=?',(row['token'],));c.commit();flash(t('svc.code_wrong'),'error')
            else:
                try:
                    uid=c.execute('INSERT INTO users(email,name,password,telegram,telegram_token,created,language,onboarding_completed,email_verified) VALUES(?,?,?,?,?,?,?,0,1)',(row['email'],row['name'],row['password'],row['telegram'],secrets.token_urlsafe(24),self.stamp(),row['language'])).lastrowid
                    c.execute('DELETE FROM email_challenges WHERE email=?',(row['email'],));c.commit()
                except __import__('sqlite3').IntegrityError:
                    c.rollback();session.pop('email_challenge',None);flash(t('svc.email_exists'),'error');return redirect(url_for('login'))
                session.clear();session['uid']=uid
                self.queue_chat(self.app.config['TELEGRAM_ADMIN_CHAT_ID'],t('bot.new_account',name=row['name'],email=row['email']))
                flash(t('svc.verified_pending'),'success');return redirect(url_for('profile'))
        return render_template('verify_email.html',email=row['email'])
    def resend_email(self):
        row=self.challenge()
        if not row:return redirect(url_for('register'))
        if time.time()-row['sent_at']<60 or self.limited('email:'+self.digest(row['email']),5,3600):
            flash(t('svc.rate_limit'),'error');return redirect(url_for('verify_email'))
        code=f'{secrets.randbelow(1000000):06d}';now=time.time();c=self.db()
        changed=c.execute('UPDATE email_challenges SET code_hash=?,expires=?,sent_at=?,attempts=0 WHERE token=? AND sent_at=?',(self.digest(row['token']+code),now+600,now,row['token'],row['sent_at'])).rowcount
        c.commit()
        if not changed:
            flash(t('svc.rate_limit'),'error');return redirect(url_for('verify_email'))
        flash(t('svc.code_sent' if self.email_send(row['email'],code,row['language']) else 'svc.email_failed'),'success')
        return redirect(url_for('verify_email'))
    def profile(self):
        # Do not allow bypassing email verification via an editable profile email.
        if request.method=='POST' and request.form.get('email','').lower().strip()!=g.user['email']:
            flash(t('svc.email_locked'),'error');return redirect(url_for('profile'))
        return self.app.extensions['mops_features'].profile()
    def approve(self,uid):
        user=self.db().execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        if not user or user['email_verified']==0: abort(409)
        return self.app.extensions['mops_features'].approve(uid)
    def before(self):
        if g.user and g.user['role']!='admin' and g.user['email_verified']==0 and request.endpoint not in ('logout','static','telegram_webhook'):
            abort(403)
        if request.endpoint=='login' and request.method=='POST' and self.limited('login:'+self.ip_key(),30,900):
            abort(429)
    def after(self,response):
        if request.method=='POST' and request.endpoint not in ('telegram_webhook',None):
            try:
                c=self.db();c.rollback()
                c.execute('INSERT INTO audit_events(user_id,action,target,result,created) VALUES(?,?,?,?,?)',(g.user['id'] if g.get('user') else None,request.endpoint,request.path[:200],response.status_code,self.stamp()));c.commit()
            except Exception:
                self.db().rollback();self.app.logger.warning('Could not persist audit event')
        if g.get('user'):response.headers['Cache-Control']='private, no-store'
        return response
    def context(self):
        u=g.get('user');unread=0
        if u:
            if u['role']=='admin':unread=self.db().execute("SELECT COUNT(*) FROM support_messages m JOIN users u ON u.id=m.sender_id WHERE u.role='client' AND m.read_at='' ").fetchone()[0]
            else:unread=self.db().execute("SELECT COUNT(*) FROM support_messages WHERE client_id=? AND sender_id<>? AND read_at=''",(u['id'],u['id'])).fetchone()[0]
        return {'support_unread':unread}
    def thread_user(self):
        if g.user['role']=='admin':
            uid=request.args.get('user',type=int)
            if uid is None:return None
            u=self.db().execute("SELECT * FROM users WHERE id=? AND role='client'",(uid,)).fetchone()
            if not u:abort(404)
            return u
        if request.args.get('user') and request.args.get('user')!=str(g.user['id']):abort(403)
        return g.user
    def support(self):
        u=self.thread_user();c=self.db()
        if request.method=='POST':
            if not u:abort(400)
            body=request.form.get('body','').strip();nonce=request.form.get('nonce','')
            if not 1<=len(body)<=4000 or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',nonce):abort(400)
            existing=c.execute('SELECT id FROM support_messages WHERE sender_id=? AND nonce=?',(g.user['id'],nonce)).fetchone()
            if not existing:
                if self.limited('chat:'+str(g.user['id']),20,60):abort(429)
                try:
                    mid=c.execute('INSERT INTO support_messages(client_id,sender_id,body,created,nonce) VALUES(?,?,?,?,?)',(u['id'],g.user['id'],body,self.stamp(),nonce)).lastrowid;c.commit()
                except __import__('sqlite3').IntegrityError:c.rollback();mid=None
                if mid:
                    if g.user['role']=='admin': self.queue_user(u['id'],t('svc.bot_reply',u['language']))
                    else:self.queue_chat(self.app.config['TELEGRAM_ADMIN_CHAT_ID'],t('svc.bot_support',name=u['name'],id=u['id']))
            if request.headers.get('Accept')=='application/json':return jsonify(ok=True,nonce=secrets.token_urlsafe(24))
            return redirect(url_for('support',user=u['id']) if g.user['role']=='admin' else url_for('support'))
        threads=[]
        if g.user['role']=='admin':
            threads=c.execute("SELECT u.id,u.name,u.email,MAX(m.id) AS last_id,SUM(CASE WHEN m.read_at='' AND m.sender_id=u.id THEN 1 ELSE 0 END) AS unread FROM users u JOIN support_messages m ON m.client_id=u.id GROUP BY u.id,u.name,u.email ORDER BY last_id DESC LIMIT 100").fetchall()
        return render_template('support.html',thread_user=u,threads=threads,nonce=secrets.token_urlsafe(24))
    def support_messages(self):
        u=self.thread_user()
        if not u:return jsonify(messages=[],has_more=False)
        after=max(request.args.get('after',0,type=int) or 0,0);c=self.db()
        rows=c.execute('SELECT m.*,u.role FROM support_messages m JOIN users u ON u.id=m.sender_id WHERE m.client_id=? AND m.id>? ORDER BY m.id LIMIT 101',(u['id'],after)).fetchall()
        rows=rows[:100];last=rows[-1]['id'] if rows else after
        if g.user['role']=='admin':c.execute("UPDATE support_messages SET read_at=? WHERE client_id=? AND sender_id=? AND id<=? AND read_at=''",(self.stamp(),u['id'],u['id'],last))
        else:c.execute("UPDATE support_messages SET read_at=? WHERE client_id=? AND sender_id<>? AND id<=? AND read_at=''",(self.stamp(),u['id'],u['id'],last))
        c.commit()
        return jsonify(messages=[{'id':r['id'],'body':r['body'],'created':r['created'],'mine':r['sender_id']==g.user['id'],'role':r['role']} for r in rows],has_more=len(rows)==100)
    def page(self):return max(1,min(request.args.get('page',1,type=int) or 1,100000))
    def all_users(self):
        page=self.page();q=request.args.get('q','').strip()[:100];pattern='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        rows=self.db().execute("SELECT u.*,(SELECT COUNT(*) FROM orders o WHERE o.user_id=u.id) AS parcels FROM users u WHERE LOWER(u.name) LIKE ? ESCAPE '\\' OR LOWER(u.email) LIKE ? ESCAPE '\\' OR LOWER(u.telegram) LIKE ? ESCAPE '\\' ORDER BY u.id DESC LIMIT 51 OFFSET ?",(pattern.lower(),pattern.lower(),pattern.lower(),(page-1)*50)).fetchall()
        return render_template('users.html',members=rows[:50],has_more=len(rows)>50,page=page,q=q)
    def audit_log(self):
        page=self.page();rows=self.db().execute('SELECT a.*,u.name FROM audit_events a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 51 OFFSET ?',((page-1)*50,)).fetchall()
        failed=self.db().execute("SELECT n.id,n.state,n.attempts,n.last_error,n.created,u.name FROM notification_outbox n LEFT JOIN users u ON u.id=n.user_id WHERE n.state<>'sent' ORDER BY n.id DESC LIMIT 50").fetchall()
        return render_template('audit.html',events=rows[:50],has_more=len(rows)>50,page=page,notifications=failed,persistent=bool(self.app.config.get('DATABASE_URL')))
    def retry_notifications(self):
        self.db().execute("UPDATE notification_outbox SET state='pending',next_try=0,lease_until=0,attempts=0 WHERE state='failed'");self.db().commit()
        self.drain(5);return redirect(url_for('audit_log'))
    def queue_chat(self,chat,text,keyboard=None):
        if not chat:return None
        return self.enqueue(None,str(chat),text,keyboard)
    def queue_user(self,uid,text):return self.enqueue(uid,'',text)
    def enqueue(self,uid,chat,text,keyboard=None):
        payload={'text':text[:4096]}
        if keyboard:payload['reply_markup']={'inline_keyboard':keyboard}
        c=self.db();nid=c.execute('INSERT INTO notification_outbox(user_id,chat_id,payload,created) VALUES(?,?,?,?)',(uid,chat,json.dumps(payload,ensure_ascii=False),self.stamp())).lastrowid;c.commit()
        self.deliver(nid)
        self.wake()
        return {'queued':True,'id':nid}
    def deliver(self,nid):
        c=self.db();now=time.time()
        changed=c.execute("UPDATE notification_outbox SET state='sending',lease_until=? WHERE id=? AND next_try<=? AND (state='pending' OR (state='sending' AND lease_until<?))",(now+60,nid,now,now)).rowcount;c.commit()
        if not changed:return
        n=c.execute('SELECT * FROM notification_outbox WHERE id=?',(nid,)).fetchone();chat=n['chat_id']
        if n['user_id']:
            u=c.execute('SELECT telegram_chat_id FROM users WHERE id=?',(n['user_id'],)).fetchone();chat=u[0] if u else ''
        c.commit()
        if not chat or not self.app.config.get('TELEGRAM_BOT_TOKEN'):
            c.execute("UPDATE notification_outbox SET state='pending',lease_until=0,next_try=?,last_error=? WHERE id=?",(now+self.check_interval,'link_telegram' if not chat else 'configure_bot',nid));c.commit();return
        payload=json.loads(n['payload']);payload['chat_id']=chat
        result=self.app.extensions['mops_features'].telegram.call('sendMessage',payload)
        if result is not None:
            c.execute("UPDATE notification_outbox SET state='sent',sent_at=?,lease_until=0,last_error='' WHERE id=?",(self.stamp(),nid))
        else:
            attempts=n['attempts']+1
            c.execute('UPDATE notification_outbox SET state=?,attempts=?,next_try=?,lease_until=0,last_error=? WHERE id=?',('failed' if attempts>=10 else 'pending',attempts,now+min(3600,15*2**min(attempts,8)),'telegram_delivery_failed',nid))
        c.commit()
    def drain(self,limit=10):
        if not self.lock.acquire(blocking=False):return
        try:
            now=time.time();rows=self.db().execute("SELECT id FROM notification_outbox WHERE next_try<=? AND (state='pending' OR (state='sending' AND lease_until<?)) ORDER BY id LIMIT ?",(now,now,limit)).fetchall();self.db().commit()
            for row in rows:self.deliver(row['id'])
        finally:self.lock.release()
    def worker(self):
        while not self.stop_event.is_set():
            self.wake_event.clear()
            try:
                if self.app.config.get('TELEGRAM_BOT_TOKEN'):
                    with self.app.app_context():
                        self.drain()
                        self.app.extensions['report_archive'].drain()
            except Exception:self.app.logger.warning('Notification worker will retry')
            # No database connection is held while waiting; new events wake us immediately.
            self.wake_event.wait(self.check_interval)
