"""End-to-end Flask scenarios on SQLite and a real PostgreSQL when TEST_DATABASE_URL is set."""
import os,re,uuid,secrets,sqlite3
from pathlib import Path
from unittest.mock import Mock
import pytest
from test_e2e import image,create_order
from app import create_app
from test_i18n import visible

BACKENDS=['sqlite']+(['postgres'] if os.getenv('TEST_DATABASE_URL') else [])
@pytest.fixture(params=BACKENDS)
def env(request,tmp_path,monkeypatch):
    monkeypatch.setenv('ADMIN_EMAIL','admin@mops.test');monkeypatch.setenv('ADMIN_PASSWORD','Mops-test-Admin-27!')
    url='';schema=None
    if request.param=='postgres':
        import psycopg
        from psycopg import sql
        from urllib.parse import urlencode
        schema='test_'+uuid.uuid4().hex
        with psycopg.connect(os.environ['TEST_DATABASE_URL'],autocommit=True) as c:c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        url=os.environ['TEST_DATABASE_URL']+('&' if '?' in os.environ['TEST_DATABASE_URL'] else '?')+urlencode({'options':'-csearch_path='+schema})
    mail=[]
    app=create_app({'TESTING':True,'CSRF_ENABLED':False,'SECRET_KEY':'test-secret-persistent-32-characters','DATABASE_URL':url,'DATABASE':str(tmp_path/'db.sqlite3'),'UPLOAD_FOLDER':str(tmp_path/'uploads'),'TELEGRAM_BOT_TOKEN':'','TELEGRAM_ADMIN_CHAT_ID':'','EMAIL_TRANSPORT':lambda email,subject,body:mail.append((email,body)) is None})
    client,admin=app.test_client(),app.test_client();admin.post('/login',data={'email':'admin@mops.test','password':'Mops-test-Admin-27!'})
    yield app,client,admin,mail
    if schema:
        with psycopg.connect(os.environ['TEST_DATABASE_URL'],autocommit=True) as c:c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

def query(app,sql,params=(),many=False):
    with app.app_context():
        cur=app.extensions['services'].db().execute(sql,params)
        return cur.fetchall() if many else cur.fetchone()
def execute(app,sql,params=()):
    with app.app_context():
        c=app.extensions['services'].db();c.execute(sql,params);c.commit()
def register(env,email='person@mops.test',client=None):
    app,c,admin,mail=env;c=client or c
    r=c.post('/register',data={'name':'Test Person','email':email,'password':'Client-pass-27!','telegram':'mops_person'})
    assert r.location.endswith('/verify-email')
    code=re.search(r'(?<!\d)\d{6}(?!\d)',mail[-1][1])[0]
    assert c.post('/verify-email',data={'code':code}).location.endswith('/profile')
    u=query(app,'SELECT * FROM users WHERE email=?',(email,));admin.post(f"/admin/users/{u['id']}/approve")
    return u['id']
def send(c,body,uid=None,nonce=None):return c.post('/support'+('?user='+str(uid) if uid else ''),data={'body':body,'nonce':nonce or secrets.token_urlsafe(24)},headers={'Accept':'application/json'})

def test_email_is_required_and_code_is_single_use(env):
    app,c,admin,mail=env
    c.post('/register',data={'name':'Person','email':'new@mops.test','password':'password123'})
    assert not query(app,"SELECT id FROM users WHERE email='new@mops.test'")
    row=query(app,'SELECT * FROM email_challenges');code=re.search(r'\d{6}',mail[-1][1])[0]
    assert row['code_hash']!=code and code not in row['code_hash']
    assert c.get('/dashboard').status_code==302
    c.post('/verify-email',data={'code':code})
    assert query(app,"SELECT email_verified FROM users WHERE email='new@mops.test'")[0]==1
    assert c.get('/dashboard').status_code==403
    assert c.post('/verify-email',data={'code':code}).location.endswith('/register')

def test_code_attempt_limit_expiry_resend(env):
    app,c,_,mail=env;c.post('/register',data={'name':'Person','email':'new@mops.test','password':'password123'})
    old=re.search(r'\d{6}',mail[-1][1])[0]
    for _ in range(5):c.post('/verify-email',data={'code':'wrong'})
    c.post('/verify-email',data={'code':old})
    assert not query(app,"SELECT id FROM users WHERE email='new@mops.test'")
    c.post('/verify-email/resend');assert len(mail)==1
    execute(app,'UPDATE email_challenges SET sent_at=0')
    c.post('/verify-email/resend');assert len(mail)==2
    execute(app,'UPDATE email_challenges SET expires=0')
    c.post('/verify-email',data={'code':re.search(r'\d{6}',mail[-1][1])[0]})
    assert not query(app,"SELECT id FROM users WHERE email='new@mops.test'")

def test_email_failure_does_not_create_account(env):
    app,c,_,_=env;app.config['EMAIL_TRANSPORT']=lambda *a:False
    r=c.post('/register',data={'name':'Person','email':'new@mops.test','password':'password123'})
    assert r.status_code==200 and not query(app,'SELECT token FROM email_challenges')
    assert not query(app,"SELECT id FROM users WHERE email='new@mops.test'")

def test_email_cannot_be_changed_without_verification(env):
    app,c,_,_=env;uid=register(env)
    c.post('/profile',data={'name':'Person','email':'unverified@mops.test'})
    assert query(app,'SELECT email FROM users WHERE id=?',(uid,))[0]=='person@mops.test'

def test_support_private_bidirectional_deduplicated(env):
    app,c,admin,_=env;uid=register(env)
    other=app.test_client();register(env,'other@mops.test',other)
    nonce=secrets.token_urlsafe(24)
    assert send(c,'Where is my parcel?',nonce=nonce).status_code==200
    assert send(c,'Where is my parcel?',nonce=nonce).status_code==200
    assert query(app,'SELECT COUNT(*) FROM support_messages')[0]==1
    assert other.get('/support/messages?user='+str(uid)).status_code==403
    assert other.get('/support/messages').json['messages']==[]
    assert admin.get('/support/messages?user='+str(uid)).json['messages'][0]['body']=='Where is my parcel?'
    assert send(admin,'Your parcel is received.',uid).status_code==200
    assert len(c.get('/support/messages').json['messages'])==2
    assert query(app,"SELECT COUNT(*) FROM support_messages WHERE read_at=''")[0]==0

def test_chat_permission_validation_and_xss(env):
    app,c,admin,_=env;uid=register(env)
    assert c.get('/admin/users').status_code==403 and c.get('/admin/logs').status_code==403
    assert send(c,'x'*4001).status_code==400
    assert send(c,'').status_code==400
    assert send(c,'<script>alert(1)</script>').status_code==200
    assert '<script>alert(1)</script>' not in c.get('/support').get_data(as_text=True)
    assert c.get('/support/messages').json['messages'][0]['body']=='<script>alert(1)</script>'
    assert app.test_client().get('/support/messages').status_code==302

def test_csrf_enforced_on_chat_and_verification(env):
    app,c,_,_=env;register(env);app.config['CSRF_ENABLED']=True
    assert send(c,'blocked').status_code==400
    assert c.post('/verify-email/resend').status_code==400
    c.get('/support')
    with c.session_transaction() as s:token=s['csrf']
    r=c.post('/support',data={'body':'allowed','nonce':secrets.token_urlsafe(24),'csrf_token':token})
    assert r.status_code==302

def test_restart_preserves_accounts_parcels_chat_files_audit(env,tmp_path):
    app,c,admin,_=env;uid=register(env);create_order(c);send(c,'Keep this message')
    order=query(app,'SELECT * FROM orders');svc=app.extensions['services']
    with app.app_context():before=svc.file_bytes(order['item_photo'])
    assert before
    cfg=dict(app.config);cfg['UPLOAD_FOLDER']=str(tmp_path/'new-empty-filesystem')
    restarted=create_app(cfg);new=restarted.test_client()
    new.post('/login',data={'email':'person@mops.test','password':'Client-pass-27!'})
    assert new.get('/dashboard').status_code==200
    assert new.get('/support/messages').json['messages'][0]['body']=='Keep this message'
    with restarted.app_context():assert restarted.extensions['services'].file_bytes(order['item_photo'])==before
    assert query(restarted,'SELECT COUNT(*) FROM orders')[0]==1
    assert query(restarted,'SELECT COUNT(*) FROM audit_events')[0]>0

def test_notification_retry_and_link_after_status(env):
    app,c,admin,_=env;uid=register(env);create_order(c);oid=query(app,'SELECT id FROM orders')[0]
    admin.post(f'/admin/orders/{oid}/update',data={'status':'Одержано'})
    pending=query(app,'SELECT * FROM notification_outbox WHERE user_id=? ORDER BY id DESC',(uid,))
    assert pending['state']=='pending' and pending['last_error']=='link_telegram'
    execute(app,'UPDATE users SET telegram_chat_id=? WHERE id=?',('12345',uid));execute(app,'UPDATE notification_outbox SET next_try=0')
    app.config['TELEGRAM_BOT_TOKEN']='test:token';bot=app.extensions['mops_features'].telegram;bot.call=Mock(return_value=None)
    with app.app_context():app.extensions['services'].drain()
    assert query(app,'SELECT attempts FROM notification_outbox WHERE id=?',(pending['id'],))[0]==1
    execute(app,'UPDATE notification_outbox SET next_try=0');bot.call=Mock(return_value={'message_id':55})
    with app.app_context():app.extensions['services'].drain()
    sent=query(app,'SELECT * FROM notification_outbox WHERE id=?',(pending['id'],))
    assert sent['state']=='sent' and sent['sent_at']
    count=bot.call.call_count
    with app.app_context():app.extensions['services'].drain()
    assert bot.call.call_count==count

def test_user_directory_contains_admin_and_client(env):
    app,c,admin,_=env;uid=register(env)
    html=admin.get('/admin/users').get_data(as_text=True)
    assert 'person@mops.test' in html and 'admin@mops.test' in html
    assert 'person@mops.test' not in admin.get('/admin/users?q=notfound').get_data(as_text=True)
    assert 'test:token' not in admin.get('/admin/logs').get_data(as_text=True)

@pytest.mark.parametrize('lang',['ru','uk','en'])
def test_all_service_pages_and_translations(env,lang):
    app,c,admin,_=env;register(env)
    for agent,path in [(c,'/support'),(admin,'/admin/users'),(admin,'/admin/logs'),(admin,'/support')]:
        r=agent.get(path+'?lang='+lang);text=visible(r)
        assert r.status_code==200 and not re.search(r'\bsvc\.\w+',text)
        if lang=='en':assert not re.search('[А-Яа-яІіЇїЄє]',text)

def test_postgres_integrity_rollback_and_named_bindings(env):
    app,_,_,_=env
    with app.app_context():
        c=app.extensions['services'].db()
        c.execute('INSERT INTO settings(key,value) VALUES(:key,:value)',{'key':'pg-test','value':'first'})
        c.rollback();assert not c.execute("SELECT 1 FROM settings WHERE key='pg-test'").fetchone()
        c.execute("INSERT INTO settings(key,value) VALUES('pg-test','second')")
        with pytest.raises(sqlite3.IntegrityError):c.execute("INSERT INTO settings(key,value) VALUES('pg-test','duplicate')")
        assert c.execute("SELECT value FROM settings WHERE key='pg-test'").fetchone()[0]=='second'
        c.commit()

@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='Set TEST_DATABASE_URL for real PostgreSQL transfer test')
def test_sqlite_import_preserves_ids_files_and_backup(tmp_path,monkeypatch):
    import psycopg,subprocess,sys
    from psycopg import sql
    from urllib.parse import urlencode
    from werkzeug.security import generate_password_hash
    from migrate_to_postgres import transfer
    monkeypatch.setenv('ADMIN_EMAIL','');monkeypatch.setenv('NOTIFICATION_WORKER','false')
    base={'TESTING':True,'DATABASE_URL':'','DATABASE':str(tmp_path/'source.sqlite3'),'UPLOAD_FOLDER':str(tmp_path/'empty'),'SECRET_KEY':'migration-test-32-character-secret'}
    local=create_app(base)
    execute(local,"INSERT INTO users(id,email,name,password,role,approved,email_verified,created) VALUES(17,'owner@example.test','Owner',?,'admin',1,2,'2026')",(generate_password_hash('Owner-password'),))
    execute(local,"INSERT INTO orders(id,user_id,item,phone,delivery,telegram,proof,item_photo,status,created,updated) VALUES(40,17,'Keep parcel','123456789','Home','owner_name','proof.png','item.png','В процессе','2026','2026')")
    execute(local,"INSERT INTO file_objects(name,data,created) VALUES('item.png',?,'2026')",(b'preserved-file-bytes',))
    execute(local,"INSERT INTO report_archives(name,order_id,state,created,cleaned_at,archive_file_id,bot_id) VALUES('report.png',40,'cleaned','2026','2026','persistent-telegram-id','123')")
    execute(local,"INSERT INTO telegram_deliveries(name,bot_id,chat_id,file_id,message_id,created) VALUES('report.png','123','456','persistent-telegram-id',9,'2026')")
    schema='test_'+uuid.uuid4().hex
    with psycopg.connect(os.environ['TEST_DATABASE_URL'],autocommit=True) as c:c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    url=os.environ['TEST_DATABASE_URL']+'?'+urlencode({'options':'-csearch_path='+schema})
    try:
        target=create_app(dict(base,DATABASE_URL=url))
        with target.app_context(),sqlite3.connect(base['DATABASE']) as src:
            db=target.extensions['services'].db();transfer(src,db)
            assert db.execute('SELECT id FROM users').fetchone()[0]==17
            assert db.execute('SELECT id FROM orders').fetchone()[0]==40
            assert target.extensions['services'].file_bytes('item.png')==b'preserved-file-bytes'
            assert db.execute('SELECT archive_file_id FROM report_archives').fetchone()[0]=='persistent-telegram-id'
            assert db.execute('SELECT message_id FROM telegram_deliveries').fetchone()[0]==9
            with pytest.raises(RuntimeError):transfer(src,db)
            assert db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==1
            uid=db.execute("INSERT INTO users(email,name,password,created) VALUES('next@example.test','Next','hash','2026')").lastrowid;db.commit();assert uid>17
        output=tmp_path/'backup.sqlite3';environ=dict(os.environ,DATABASE_URL=url,SECRET_KEY=base['SECRET_KEY'],ADMIN_EMAIL='',UPLOAD_FOLDER=str(tmp_path/'empty'))
        r=subprocess.run([sys.executable,'backup_database.py','--output',str(output)],env=environ,capture_output=True,text=True,timeout=60)
        assert r.returncode==0,r.stderr
        with sqlite3.connect(output) as backup:
            assert backup.execute('SELECT id FROM orders').fetchone()[0]==40
            assert backup.execute("SELECT data FROM file_objects WHERE name='item.png'").fetchone()[0]==b'preserved-file-bytes'
            assert backup.execute('SELECT archive_file_id FROM report_archives').fetchone()[0]=='persistent-telegram-id'
            assert backup.execute('SELECT message_id FROM telegram_deliveries').fetchone()[0]==9
    finally:
        with psycopg.connect(os.environ['TEST_DATABASE_URL'],autocommit=True) as c:c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

def test_full_parcel_payment_archive_and_persistent_report(env):
    from io import BytesIO
    app,c,admin,_=env;uid=register(env);create_order(c);oid=query(app,'SELECT id FROM orders')[0]
    admin.post(f'/admin/orders/{oid}/update',data={'status':'Одержано','report':image('report.png')},content_type='multipart/form-data')
    order=query(app,'SELECT * FROM orders');assert order['status']=='Фотоотчёт готов' and len(order['parcel_code'])==8
    assert c.post(f'/orders/{oid}/pay',data={'screenshot':image('transfer.png'),'receipt':(BytesIO(b'%PDF-1.4\nBank receipt'),'receipt.pdf')},content_type='multipart/form-data').status_code==302
    pid=query(app,'SELECT id FROM order_payments')[0]
    assert admin.post(f'/admin/payment-proofs/{pid}/approve').status_code==302
    assert admin.post(f'/admin/payment-proofs/{pid}/approve').status_code==409
    admin.post(f'/admin/orders/{oid}/update',data={'status':'Отправлено','tracking':'UK-TEST'})
    admin.post(f'/admin/orders/{oid}/update',data={'status':'Доставлено','tracking':'UK-TEST'})
    row=query(app,'SELECT * FROM orders');assert row['payment_status']=='paid' and row['archived']==1 and row['delivered_at']
    with app.app_context():assert app.extensions['services'].file_bytes(row['report'])
    assert [r['action'] for r in query(app,'SELECT action FROM order_audit ORDER BY id',many=True)]==['Фотоотчёт готов','payment.paid','Отправлено','Доставлено']
    assert query(app,'SELECT COUNT(*) FROM notification_outbox WHERE user_id=?',(uid,))[0]>=4

def test_rate_limits_and_file_delivery_after_restart(env,tmp_path):
    app,c,admin,_=env;uid=register(env);create_order(c);o=query(app,'SELECT * FROM orders')
    execute(app,'UPDATE users SET telegram_chat_id=? WHERE id=?',('12345',uid));app.config['TELEGRAM_BOT_TOKEN']='test:token'
    restarted=create_app(dict(app.config,UPLOAD_FOLDER=str(tmp_path/'fresh-folder')))
    bot=restarted.extensions['mops_features'].telegram
    sent=[]
    def capture(method,payload,files=None):
        if files:sent.append(files['document'][1].read())
        return {'document':{'file_id':'tg-file-123'}}
    bot.call=capture
    with restarted.app_context():assert bot.document('12345',o['item_photo'],'Parcel')
    assert sent and sent[0].startswith(b'\x89PNG')
    with app.test_request_context('/'):
        svc=app.extensions['services'];assert not svc.limited('test-limit',2,60);assert not svc.limited('test-limit',2,60);assert svc.limited('test-limit',2,60)
