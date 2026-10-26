"""Additive Mops Parcel features; legacy URLs, orders and accounts remain valid."""
import hashlib
import io
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

from flask import abort, flash, g, redirect, render_template, request, session, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash

from bot_service import Telegram
from domain import PRODUCTS, DELIVERIES, generate_code, migrate, rank_key
from i18n import CATALOG, t
from extra_i18n import EXTRA

CATALOG.update(EXTRA)

def install_features(app, db, stamp, login_required, admin_required):
    feature = Features(app, db, stamp)
    app.extensions['mops_features'] = feature
    with app.app_context():
        migrate(db(), app.config['DATABASE'])
    app.config.setdefault('CSRF_ENABLED', True)
    app.config.setdefault('TELEGRAM_WEBAPP_URL', (os.getenv('TELEGRAM_WEBAPP_URL') or os.getenv('RENDER_EXTERNAL_URL','')).rstrip('/'))
    app.config.setdefault('TELEGRAM_WEBHOOK_SECRET', os.getenv('TELEGRAM_WEBHOOK_SECRET',''))
    app.config['MAX_CONTENT_LENGTH'] = 26 * 1024 * 1024
    app.before_request(feature.guard)
    app.context_processor(feature.context)
    app.view_functions.update({
        'register': feature.register, 'login': feature.login,
        'new_order': login_required(feature.new_order),
        'update_order': admin_required(feature.update_order),
        'telegram_webhook': feature.webhook,
        'review_approve': admin_required(feature.review_approve),
        'approve': admin_required(feature.approve),
        'change': login_required(feature.change),
        'change_decision': admin_required(feature.change_decision),
        'payment_respond': admin_required(feature.payment_respond),
        'uploaded': login_required(feature.legacy_file),
    })
    app.add_url_rule('/start-delivery','start_delivery',feature.start_delivery)
    app.add_url_rule('/profile','profile',feature.signed_in(feature.profile),methods=['GET','POST'])
    app.add_url_rule('/profile/addresses','add_address',feature.signed_in(feature.add_address),methods=['POST'])
    app.add_url_rule('/onboarding/complete','onboarding_done',feature.signed_in(feature.onboarding_done),methods=['POST'])
    app.add_url_rule('/orders/<int:oid>/pay','pay_order',login_required(feature.pay_order),methods=['GET','POST'])
    app.add_url_rule('/orders/<int:oid>/files/<kind>/send','send_file',login_required(feature.send_file),methods=['POST'])
    app.add_url_rule('/admin/payment-proofs/<int:pid>/<decision>','payment_review',admin_required(feature.payment_review),methods=['POST'])
    app.add_url_rule('/admin/payment-proofs/<int:pid>/files/<kind>','payment_file',admin_required(feature.payment_file),methods=['POST'])

class Features:
    def __init__(self,app,db,stamp):
        self.app,self.db,self.stamp = app,db,stamp
        self.telegram = Telegram(app,db)

    def signed_in(self,fn):
        @wraps(fn)
        def inner(*args,**kwargs):
            if not g.user:
                return redirect(url_for('login',next=request.path))
            return fn(*args,**kwargs)
        return inner

    def guard(self):
        if request.endpoint == 'telegram_webhook':
            return
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        if request.method == 'POST' and self.app.config['CSRF_ENABLED']:
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token','')
            if not secrets.compare_digest(token,session['csrf']):
                abort(400)
        if g.user:
            chosen = request.args.get('lang')
            if chosen in ('ru','uk','en') and chosen != g.user['language']:
                self.db().execute('UPDATE users SET language=? WHERE id=?',(chosen,g.user['id']))
                self.db().commit()
                g.user = self.db().execute('SELECT * FROM users WHERE id=?',(g.user['id'],)).fetchone()
            elif not request.cookies.get('mops_language'):
                g.lang = g.user['language'] or 'ru'

    def statistics(self,uid):
        completed = self.db().execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND delivered_at<>''",(uid,)).fetchone()[0]
        return {'completed':completed, 'rank':rank_key(completed)}

    def context(self):
        user = g.get('user')
        c = self.db()
        invoices = c.execute("SELECT * FROM orders WHERE user_id=? AND report<>'' AND fee<>'' AND payment_status<>'paid' AND archived=0 AND status<>'Отклонено' ORDER BY id DESC",(user['id'],)).fetchall() if user and user['role']=='client' else []
        submissions = c.execute("SELECT p.*,o.item,o.parcel_code,u.name AS client_name FROM order_payments p JOIN orders o ON o.id=p.order_id JOIN users u ON u.id=p.user_id WHERE p.state='pending' ORDER BY p.id",()).fetchall() if user and user['role']=='admin' else []
        manager = os.getenv('UKRAINE_MANAGER_USERNAME','').strip().lstrip('@') or 'barujka032'
        if not re.fullmatch(r'[A-Za-z0-9_]{5,32}',manager): manager='barujka032'
        return {'products':PRODUCTS, 'delivery_types':DELIVERIES, 'open_invoices':invoices,
            'payment_submissions':submissions,'csrf_token':lambda:session.get('csrf',''),
            'manager_username':manager,'manager_is_admin':False,
            'profile_stats':self.statistics(user['id']) if user else None,
            'uk_settings':dict(c.execute('SELECT key,value FROM settings')),
            'onboarding_auto':bool(user and user['role']=='client' and not user['onboarding_completed'] and request.endpoint=='profile')}

    def start_delivery(self):
        return redirect(url_for('new_order') if g.user else url_for('login',next='/orders/new'))

    def register(self):
        if g.user: return redirect(url_for('new_order'))
        if request.method == 'POST':
            name=request.form.get('name','').strip()[:200]
            email=request.form.get('email','').strip().lower()[:254]
            password=request.form.get('password','')
            tg=request.form.get('telegram','').strip().lstrip('@')
            if not name or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(password)<8:
                flash('Проверьте имя, почту и пароль (не менее 8 символов).','error')
            elif tg and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{4,31}',tg):
                flash(t('error.telegram'),'error')
            else:
                try:
                    c=self.db()
                    uid=c.execute('INSERT INTO users(email,name,password,telegram,telegram_token,created,language,onboarding_completed) VALUES(?,?,?,?,?,?,?,0)',(email,name,generate_password_hash(password),tg,secrets.token_urlsafe(24),self.stamp(),g.lang)).lastrowid
                    c.commit()
                    session.clear();session['uid']=uid
                    self.telegram.message(self.app.config['TELEGRAM_ADMIN_CHAT_ID'],t('bot.new_account',name=name,email=email))
                    flash('Заявка отправлена администратору.','success')
                    return redirect(url_for('profile'))
                except sqlite3.IntegrityError:
                    self.db().rollback();flash('Пользователь с такой почтой уже есть.','error')
        return render_template('register.html')

    def login(self):
        if request.method=='POST':
            user=self.db().execute('SELECT * FROM users WHERE email=?',(request.form.get('email','').strip().lower(),)).fetchone()
            if user and check_password_hash(user['password'],request.form.get('password','')):
                session.clear();session['uid']=user['id']
                target=request.args.get('next','')
                if user['role']=='admin': target=url_for('admin')
                elif not user['onboarding_completed']: target=url_for('profile')
                elif target not in ('/orders/new','/profile','/dashboard'): target=url_for('dashboard')
                return redirect(target)
            flash('Неверная почта или пароль.','error')
        return render_template('login.html')

    def profile(self):
        c=self.db()
        if request.method=='POST':
            name=request.form.get('name','').strip()[:200]
            email=request.form.get('email','').strip().lower()[:254]
            phone=request.form.get('phone','').strip()
            tg=request.form.get('telegram','').strip().lstrip('@')
            if not name or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):
                flash(t('error.profile'),'error')
            elif phone and not re.fullmatch(r'[+\d ()-]{8,25}',phone): flash(t('error.phone'),'error')
            elif tg and not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{4,31}',tg): flash(t('error.telegram'),'error')
            else:
                try:
                    c.execute('UPDATE users SET name=?,email=?,phone=?,telegram=?,leaderboard_public=? WHERE id=?',(name,email,phone,tg,int(request.form.get('leaderboard_public')=='1'),g.user['id']))
                    c.commit();flash(t('profile.saved'),'success')
                    return redirect(url_for('profile'))
                except sqlite3.IntegrityError:
                    c.rollback();flash('Пользователь с такой почтой уже есть.','error')
        addresses=c.execute('SELECT * FROM addresses WHERE user_id=? ORDER BY id DESC',(g.user['id'],)).fetchall()
        return render_template('profile.html',addresses=addresses)

    def address_values(self,form):
        fields=[form.get(k,'').strip() for k in ('ua_name','ua_phone','ua_city','ua_branch')]
        if any(not v or len(v)>200 for v in fields): raise ValueError(t('error.address'))
        if not re.fullmatch(r'[+\d ()-]{8,25}',fields[1]): raise ValueError(t('error.phone'))
        return fields

    def add_address(self):
        try:
            values=self.address_values(request.form)
            self.db().execute('INSERT INTO addresses(user_id,name,phone,city,branch,created) VALUES(?,?,?,?,?,?)',(g.user['id'],*values,self.stamp()))
            self.db().commit();flash(t('address.saved'),'success')
        except ValueError as e: flash(str(e),'error')
        return redirect(url_for('profile')+'#ua-addresses')

    def onboarding_done(self):
        self.db().execute('UPDATE users SET onboarding_completed=1 WHERE id=?',(g.user['id'],));self.db().commit()
        return {'ok':True}

    def read_file(self,field,pdf=False):
        upload=request.files.get(field)
        if not upload or not upload.filename: raise ValueError(t('error.evidence' if pdf or field=='screenshot' else 'Прикрепите обязательное фото.'))
        ext=Path(upload.filename).suffix.lower()
        allowed={'.jpg','.jpeg','.png','.webp'}|({'.pdf'} if pdf else set())
        if ext not in allowed: raise ValueError(t('error.filetype'))
        data=upload.read(12*1024*1024+1)
        if not data or len(data)>12*1024*1024: raise ValueError(t('error.filesize'))
        if ext=='.pdf':
            if not data.startswith(b'%PDF-'): raise ValueError(t('error.filetype'))
        else:
            try:
                with Image.open(io.BytesIO(data)) as picture:
                    if picture.width*picture.height>24_000_000 or picture.format not in ('JPEG','PNG','WEBP'):
                        raise ValueError(t('error.filetype'))
                    picture.verify()
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
                raise ValueError(t('error.filetype'))
        return data,ext

    def save_file(self,validated,tag):
        data,ext=validated
        name=tag+'_'+secrets.token_hex(16)+ext
        (Path(self.app.config['UPLOAD_FOLDER'])/name).write_bytes(data)
        return name

    def new_order(self):
        c=self.db()
        addresses=c.execute('SELECT * FROM addresses WHERE user_id=? ORDER BY id DESC',(g.user['id'],)).fetchall()
        settings=dict(c.execute('SELECT key,value FROM settings'))
        if request.method=='POST':
            try:
                product=request.form.get('product_type','')
                if product not in PRODUCTS: raise ValueError(t('error.product'))
                item=request.form.get('item','').strip()[:200]
                delivery=request.form.get('delivery','')
                tg=request.form.get('telegram',g.user['telegram']).strip().lstrip('@')
                if not item or delivery not in DELIVERIES: raise ValueError(t('error.required'))
                if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{4,31}',tg): raise ValueError(t('error.telegram'))
                if request.form.get('shipped')!='1': raise ValueError(t('error.shipped'))
                address_id=request.form.get('address_id','')
                if address_id:
                    address=c.execute('SELECT * FROM addresses WHERE id=? AND user_id=?',(address_id,g.user['id'])).fetchone()
                    if not address: abort(403)
                    recipient=[address[k] for k in ('name','phone','city','branch')]
                else: recipient=self.address_values(request.form)
                proof=self.read_file('proof'); photo=self.read_file('item_photo')
                proof_name=self.save_file(proof,'proof'); photo_name=self.save_file(photo,'item')
                if not address_id and request.form.get('save_address')=='1':
                    c.execute('INSERT INTO addresses(user_id,name,phone,city,branch,created) VALUES(?,?,?,?,?,?)',(g.user['id'],*recipient,self.stamp()))
                oid=c.execute('INSERT INTO orders(user_id,item,phone,delivery,branch,telegram,proof,item_photo,created,updated,product_type,fee,ua_name,ua_phone,ua_city,ua_branch,uk_address) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(g.user['id'],item,recipient[1],delivery,request.form.get('branch','').strip()[:200],tg,proof_name,photo_name,self.stamp(),self.stamp(),product,str(PRODUCTS[product][1]),*recipient,settings.get(DELIVERIES[delivery],''))).lastrowid
                c.commit()
                self.telegram.message(self.app.config['TELEGRAM_ADMIN_CHAT_ID'],t('bot.new_order',id=oid,item=item))
                flash('Заявка создана и ожидает проверки статуса Shipped.','success')
                return redirect(url_for('dashboard'))
            except ValueError as e: flash(str(e),'error')
        return render_template('new_order.html',settings=settings,addresses=addresses)

    def owned_order(self,oid,admin=False):
        row=self.db().execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        if not row: abort(404)
        if row['user_id']!=g.user['id'] and not (admin and g.user['role']=='admin'): abort(403)
        return row

    def notify_user(self,uid,key,**values):
        user=self.db().execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
        if user: return self.telegram.message(user['telegram_chat_id'],t(key,user['language'],**values))

    def update_order(self,oid):
        c=self.db();o=c.execute('SELECT * FROM orders WHERE id=?',(oid,)).fetchone()
        if not o: abort(404)
        STATUSES=("В процессе","Отклонено","Одержано","Фотоотчёт готов","К отправке","Отправлено","Доставлено","Архив")
        status=request.form.get('status',o['status'])
        if status not in STATUSES: abort(400)
        try:
            fee=str(PRODUCTS[o['product_type']][1]) if o['product_type'] in PRODUCTS else request.form.get('fee',o['fee']).strip()
            if fee and (not fee.isdigit() or int(fee)<=0): raise ValueError(t('error.amount'))
            if o['payment_status'] in ('paid','pending') and fee!=o['fee']: raise ValueError(t('error.locked_amount'))
            if status in ('Отправлено','Доставлено') and o['product_type'] and o['payment_status']!='paid': raise ValueError(t('error.unpaid'))
            report=o['report']; new_report=request.files.get('report')
            if new_report and new_report.filename:
                report=self.save_file(self.read_file('report'),'report');status='Фотоотчёт готов'
            if status=='Фотоотчёт готов' and not report: raise ValueError(t('error.report'))
            deadline=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat(timespec='seconds') if report!=o['report'] else o['deadline']
            code=o['parcel_code']
            if status in ('Одержано','Фотоотчёт готов','К отправке','Отправлено','Доставлено') and not code: code=generate_code(c)
            decision='' if report!=o['report'] else o['photo_decision']
            delivered=o['delivered_at'] or (self.stamp() if status=='Доставлено' else '')
            c.execute('UPDATE orders SET status=?,fee=?,tracking=?,report=?,deadline=?,updated=?,archived=?,parcel_code=?,photo_decision=?,delivered_at=? WHERE id=?',(status,fee,request.form.get('tracking',o['tracking']).strip()[:100],report,deadline,self.stamp(),int(status in ('Доставлено','Архив')),code,decision,delivered,oid))
            c.execute('INSERT INTO order_audit(order_id,user_id,action,created) VALUES(?,?,?,?)',(oid,g.user['id'],status,self.stamp()));c.commit()
            user=c.execute('SELECT * FROM users WHERE id=?',(o['user_id'],)).fetchone()
            message=t('bot.status',user['language'],id=oid,item=o['item'],status=t(status,user['language']),code=code or '—')
            if report and fee and o['payment_status']!='paid':
                card=c.execute("SELECT value FROM settings WHERE key='payment_card'").fetchone()[0]
                message+='\n'+t('bot.invoice',user['language'],amount=fee,card=card or t('payment.ask_admin',user['language']))
            self.telegram.message(user['telegram_chat_id'],message)
            if report!=o['report'] and user['telegram_chat_id']:
                if not self.telegram.document(user['telegram_chat_id'],report,t('bot.report_file',user['language'],id=oid,item=o['item'])):
                    flash(t('file.failed'),'error')
            flash(t('Заявка #{id} обновлена.',id=oid),'success')
        except ValueError as e: flash(str(e),'error')
        return redirect(url_for('admin')+'#orders')

    def pay_order(self,oid):
        o=self.owned_order(oid)
        if not o['report'] or not o['fee'] or o['status']=='Отклонено': abort(409)
        c=self.db()
        if request.method=='POST':
            if o['payment_status'] in ('paid','pending'): abort(409)
            try:
                screenshot=self.read_file('screenshot');receipt=self.read_file('receipt',pdf=True)
                if hashlib.sha256(screenshot[0]).digest()==hashlib.sha256(receipt[0]).digest(): raise ValueError(t('error.same_evidence'))
                c.execute('BEGIN IMMEDIATE')
                fresh=c.execute('SELECT payment_status,fee FROM orders WHERE id=?',(oid,)).fetchone()
                if fresh['payment_status'] in ('paid','pending'): c.rollback();abort(409)
                screenshot_name=self.save_file(screenshot,'payment');receipt_name=self.save_file(receipt,'receipt')
                c.execute('INSERT INTO order_payments(order_id,user_id,amount,screenshot,receipt,created) VALUES(?,?,?,?,?,?)',(oid,g.user['id'],fresh['fee'],screenshot_name,receipt_name,self.stamp()))
                c.execute("UPDATE orders SET payment_status='pending' WHERE id=?",(oid,));c.commit()
                self.telegram.message(self.app.config['TELEGRAM_ADMIN_CHAT_ID'],t('bot.payment_review',id=oid,item=o['item']))
                flash(t('payment.submitted'),'success');return redirect(url_for('dashboard'))
            except ValueError as e: flash(str(e),'error')
            except sqlite3.IntegrityError: c.rollback();abort(409)
        history=c.execute('SELECT * FROM order_payments WHERE order_id=? ORDER BY id DESC',(oid,)).fetchall()
        card=c.execute("SELECT value FROM settings WHERE key='payment_card'").fetchone()[0]
        return render_template('payment.html',order=o,payments=history,payment_card=card)

    def payment_review(self,pid,decision):
        if decision not in ('approve','reject'): abort(404)
        c=self.db();c.execute('BEGIN IMMEDIATE')
        p=c.execute('SELECT * FROM order_payments WHERE id=?',(pid,)).fetchone()
        if not p: c.rollback();abort(404)
        if p['state']!='pending': c.rollback();abort(409)
        reason=request.form.get('reason','').strip()[:1000]
        if decision=='reject' and not reason:
            c.rollback();flash(t('error.reason'),'error');return redirect(url_for('admin')+'#payment-proofs')
        state='paid' if decision=='approve' else 'rejected'
        c.execute('UPDATE order_payments SET state=?,reason=?,reviewed=? WHERE id=?',(state,reason,self.stamp(),pid))
        c.execute('UPDATE orders SET payment_status=? WHERE id=?',('paid' if decision=='approve' else 'unpaid',p['order_id']))
        c.commit()
        self.notify_user(p['user_id'],'bot.payment_'+state,id=p['order_id'],reason=reason)
        flash(t('payment.'+state),'success');return redirect(url_for('admin')+'#payment-proofs')

    def change(self,oid):
        self.owned_order(oid)
        keys=('phone','delivery','branch','telegram','ua_name','ua_phone','ua_city','ua_branch')
        data={key:request.form.get(key,'').strip() for key in keys if request.form.get(key,'').strip()}
        try:
            if not data: raise ValueError(t('Укажите новые данные.'))
            if any('\n' in value or '\r' in value or len(value)>200 for value in data.values()): raise ValueError(t('error.required'))
            for key in ('phone','ua_phone'):
                if key in data and not re.fullmatch(r'[+\d ()-]{8,25}',data[key]): raise ValueError(t('error.phone'))
            if 'delivery' in data and data['delivery'] not in DELIVERIES: raise ValueError(t('error.required'))
            if 'telegram' in data:
                data['telegram']=data['telegram'].lstrip('@')
                if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{4,31}',data['telegram']): raise ValueError(t('error.telegram'))
            self.db().execute('INSERT INTO changes(order_id,user_id,payload,created) VALUES(?,?,?,?)',(oid,g.user['id'],'\n'.join(f'{k}: {v}' for k,v in data.items()),self.stamp()));self.db().commit()
            self.telegram.message(self.app.config['TELEGRAM_ADMIN_CHAT_ID'],t('bot.change_request',id=oid))
            flash('Запрос изменения отправлен администратору.','success')
        except ValueError as e: flash(str(e),'error')
        return redirect(url_for('dashboard'))

    def change_decision(self,cid,decision):
        if decision not in ('approve','reject'): abort(404)
        c=self.db();c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM changes WHERE id=?',(cid,)).fetchone()
        if not row or row['state']!='Ожидает подтверждения': c.rollback();abort(409)
        if decision=='approve':
            parsed=dict(line.split(': ',1) for line in row['payload'].splitlines() if ': ' in line)
            data={k:v for k,v in parsed.items() if k in ('phone','delivery','branch','telegram','ua_name','ua_phone','ua_city','ua_branch')}
            if 'ua_phone' in data: data['phone']=data['ua_phone']
            elif 'phone' in data: data['ua_phone']=data['phone']
            if data:c.execute('UPDATE orders SET '+','.join(k+'=?' for k in data)+',updated=? WHERE id=? AND user_id=?',(*data.values(),self.stamp(),row['order_id'],row['user_id']))
        state='Подтверждено' if decision=='approve' else 'Отклонено'
        c.execute('UPDATE changes SET state=? WHERE id=?',(state,cid));c.commit()
        user=c.execute('SELECT language FROM users WHERE id=?',(row['user_id'],)).fetchone()
        self.notify_user(row['user_id'],'bot.change_result',id=row['order_id'],status=t(state,user['language']))
        flash('Запрос подтверждено.' if decision=='approve' else 'Запрос отклонено.','success')
        return redirect(url_for('admin')+'#requests')

    def payment_respond(self,pid):
        c=self.db();row=c.execute('SELECT * FROM payment_requests WHERE id=?',(pid,)).fetchone()
        if not row: abort(404)
        msg=request.form.get('response','').strip()[:2000]
        if not msg: flash(t('error.required'),'error');return redirect(url_for('admin')+'#requests')
        self.notify_user(row['user_id'],'bot.payment_response',id=row['order_id'],message=msg)
        c.execute("UPDATE payment_requests SET state='Ответ отправлен' WHERE id=?",(pid,));c.commit()
        flash('Ответ отправлен.','success');return redirect(url_for('admin')+'#requests')

    def recipient_chat(self):
        return g.user['telegram_chat_id'] or (self.app.config['TELEGRAM_ADMIN_CHAT_ID'] if g.user['role']=='admin' else '')

    def send_file(self,oid,kind):
        if kind not in ('proof','item_photo','report'): abort(404)
        o=self.owned_order(oid,admin=True)
        if not o[kind]: abort(404)
        chat=self.recipient_chat()
        if not chat:
            flash(t('file.link_first'),'error');return redirect(url_for('profile'))
        ok=self.telegram.document(chat,o[kind],t('file.caption',id=oid,item=o['item']))
        flash(t('file.sent' if ok else 'file.failed'),'success' if ok else 'error')
        return redirect(url_for('admin')+'#orders' if g.user['role']=='admin' else url_for('dashboard'))

    def payment_file(self,pid,kind):
        if kind not in ('screenshot','receipt'): abort(404)
        p=self.db().execute('SELECT * FROM order_payments WHERE id=?',(pid,)).fetchone()
        if not p: abort(404)
        chat=self.recipient_chat()
        if not chat: flash(t('file.link_first'),'error')
        else:
            ok=self.telegram.document(chat,p[kind],t('payment.evidence_caption',id=p['order_id']))
            flash(t('file.sent' if ok else 'file.failed'),'success' if ok else 'error')
        return redirect(url_for('admin')+'#payment-proofs')

    def legacy_file(self,name):
        # Existing bookmarks resolve to an authenticated file-delivery page, never to raw media.
        if Path(name).name!=name: abort(404)
        o=self.db().execute('SELECT * FROM orders WHERE proof=? OR item_photo=? OR report=?',(name,name,name)).fetchone()
        if o:
            self.owned_order(o['id'],admin=True)
            kind=next(k for k in ('proof','item_photo','report') if o[k]==name)
            return render_template('telegram_file.html',order=o,kind=kind)
        # Review attachments remain downloadable for their owner/admin, not displayed inline.
        review=self.db().execute('SELECT * FROM reviews WHERE image=?',(name,)).fetchone()
        if not review or (g.user['role']!='admin' and review['user_id']!=g.user['id']): abort(403)
        from flask import send_from_directory
        return send_from_directory(self.app.config['UPLOAD_FOLDER'],name,as_attachment=True)

    def approve(self,uid):
        c=self.db();u=c.execute("SELECT * FROM users WHERE id=? AND role='client'",(uid,)).fetchone()
        if not u: abort(404)
        c.execute('UPDATE users SET approved=1 WHERE id=?',(uid,));c.commit()
        self.notify_user(uid,'bot.approved')
        flash(t('Доступ подтверждён: {email}',email=u['email']),'success');return redirect(url_for('admin')+'#users')

    def review_approve(self,rid):
        c=self.db();c.execute('BEGIN IMMEDIATE')
        r=c.execute('SELECT * FROM reviews WHERE id=?',(rid,)).fetchone()
        if not r: c.rollback();abort(404)
        if r['state']!='Ожидает проверки': c.rollback();abort(409)
        c.execute("UPDATE reviews SET state='Бонус подтверждён' WHERE id=?",(rid,))
        c.execute('UPDATE users SET bonus_balance=bonus_balance+1 WHERE id=?',(r['user_id'],));c.commit()
        self.notify_user(r['user_id'],'bot.bonus')
        flash('Бонус за отзыв подтверждён.','success');return redirect(url_for('admin')+'#reviews')

    def webapp_keyboard(self,lang):
        url=self.app.config['TELEGRAM_WEBAPP_URL']
        parsed=urlparse(url)
        rows=[]
        if parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password:
            rows.append([{'text':t('bot.open',lang),'web_app':{'url':url}}])
        rows.append([{'text':t('bot.leaders',lang),'callback_data':'leaders'},{'text':t('Язык',lang),'callback_data':'language'}])
        return rows

    def webhook(self):
        expected=self.app.config['TELEGRAM_WEBHOOK_SECRET']
        if not expected or not secrets.compare_digest(request.headers.get('X-Telegram-Bot-Api-Secret-Token',''),expected): abort(403)
        payload=request.get_json(silent=True) or {}
        if not isinstance(payload,dict): abort(400)
        update_id=payload.get('update_id')
        if isinstance(update_id,int) and self.db().execute('SELECT 1 FROM bot_updates WHERE update_id=?',(update_id,)).fetchone(): return {'ok':True}
        callback=payload.get('callback_query') or {}
        message=payload.get('message') or callback.get('message') or {}
        sender=callback.get('from') or message.get('from') or {}
        chat=message.get('chat') or {}
        if chat.get('type')!='private' or sender.get('is_bot') or str(chat.get('id'))!=str(sender.get('id')): return {'ok':True}
        chat_id=str(chat['id'])
        c=self.db();user=c.execute('SELECT * FROM users WHERE telegram_chat_id=?',(chat_id,)).fetchone()
        preference=c.execute('SELECT language FROM bot_preferences WHERE chat_id=?',(chat_id,)).fetchone()
        lang=(user['language'] if user else preference['language'] if preference else sender.get('language_code','en').split('-')[0])
        if lang not in ('ru','uk','en'): lang='en'
        command=callback.get('data') or message.get('text','').strip()
        match=re.fullmatch(r'/start(?:@\w+)? mp_(\d+)_([A-Za-z0-9_-]+)',command)
        if match:
            candidate=c.execute('SELECT * FROM users WHERE id=?',(int(match.group(1)),)).fetchone()
            if not candidate or not candidate['telegram_token'] or not secrets.compare_digest(candidate['telegram_token'],match.group(2)) or (user and user['id']!=candidate['id']) or (candidate['telegram_chat_id'] and candidate['telegram_chat_id']!=chat_id):
                self.telegram.message(chat_id,t('bot.bad_link',lang));return {'ok':True}
            c.execute('UPDATE users SET telegram_chat_id=? WHERE id=?',(chat_id,candidate['id']));c.commit()
            user=c.execute('SELECT * FROM users WHERE id=?',(candidate['id'],)).fetchone();lang=user['language'];command='/start'
        command=command.split('@',1)[0] if command.startswith('/') and ' ' not in command else command
        if command.startswith('lang:') and command[5:] in ('ru','uk','en'):
            lang=command[5:]
            c.execute('INSERT INTO bot_preferences(chat_id,language) VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET language=excluded.language',(chat_id,lang))
            if user: c.execute('UPDATE users SET language=? WHERE id=?',(lang,user['id']))
            c.commit();command='/start'
        if command in ('/language','language'):
            self.telegram.message(chat_id,t('bot.choose_language',lang),[[{'text':'Русский','callback_data':'lang:ru'},{'text':'Українська','callback_data':'lang:uk'},{'text':'English','callback_data':'lang:en'}]])
        elif command in ('/leaders','leaders'):
            rows=c.execute("SELECT u.id,u.telegram,u.leaderboard_public,COUNT(o.id) AS completed FROM users u JOIN orders o ON u.id=o.user_id AND o.delivered_at<>'' WHERE u.role='client' AND u.approved=1 GROUP BY u.id ORDER BY completed DESC,u.id LIMIT 10").fetchall()
            lines=[t('bot.leaders_title',lang)]
            for i,row in enumerate(rows,1):
                label='@'+row['telegram'] if row['leaderboard_public'] and row['telegram'] else t('bot.member',lang,id=row['id'])
                lines.append(f"{i}. {label} — {row['completed']} · {t(rank_key(row['completed']),lang)}")
            if not rows: lines.append(t('bot.no_leaders',lang))
            self.telegram.message(chat_id,'\n'.join(lines),self.webapp_keyboard(lang))
        elif command=='/orders' and user:
            orders=c.execute('SELECT item,status,parcel_code FROM orders WHERE user_id=? AND archived=0 ORDER BY id DESC LIMIT 10',(user['id'],)).fetchall()
            lines=[t('Мои посылки',lang)]+[f"{o['parcel_code'] or '—'} · {o['item']} · {t(o['status'],lang)}" for o in orders]
            self.telegram.message(chat_id,'\n'.join(lines),self.webapp_keyboard(lang))
        else:
            if user:
                stats=self.statistics(user['id'])
                text=t('bot.account',lang,name=user['name'],completed=stats['completed'],bonus=user['bonus_balance'],rank=t(stats['rank'],lang))
                if not user['approved']: text+='\n'+t('bot.pending',lang)
            else: text=t('bot.welcome',lang)
            text+='\n\n'+t('bot.help',lang)
            self.telegram.message(chat_id,text,self.webapp_keyboard(lang))
        if callback.get('id'): self.telegram.call('answerCallbackQuery',{'callback_query_id':callback['id']})
        if isinstance(update_id,int):
            c.execute('INSERT OR IGNORE INTO bot_updates(update_id,created) VALUES(?,?)',(update_id,self.stamp()));c.commit()
        return {'ok':True}
