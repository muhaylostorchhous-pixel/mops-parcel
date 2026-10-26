"""Additive feature regressions. Real Flask requests + SQLite; Telegram mocked."""
import ast
import re
import sqlite3
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
import pytest
from werkzeug.security import generate_password_hash
from test_e2e import ctx,create_order,first_order_id,register_and_approve,image,confirm_payment
from test_i18n import visible
from domain import PRODUCTS,rank_key,migrate,generate_code
from i18n import CATALOG,t

def query(app,sql,args=(),all=False):
    with sqlite3.connect(app.config['DATABASE']) as c:
        c.row_factory=sqlite3.Row
        result=c.execute(sql,args)
        return result.fetchall() if all else result.fetchone()

def execute(app,sql,args=()):
    with sqlite3.connect(app.config['DATABASE']) as c:c.execute(sql,args)

def report(ctx):
    app,client,admin=ctx;register_and_approve(ctx);create_order(client);oid=first_order_id(app)
    assert 'invoice-banner' not in client.get('/dashboard').get_data(as_text=True)
    admin.post(f'/admin/orders/{oid}/update',data={'status':'Одержано','report':image('report.png')},content_type='multipart/form-data')
    return oid

def pay(client,oid,**extra):
    data={'screenshot':image('transfer.png'),'receipt':(BytesIO(b'%PDF-1.4\nBank transfer record'),'bank.pdf')};data.update(extra)
    return client.post(f'/orders/{oid}/pay',data=data,content_type='multipart/form-data',follow_redirects=True)

def test_existing_account_cta_and_new_account_tour(ctx):
    app,client,_=ctx
    assert client.get('/start-delivery').location=='/login?next=/orders/new'
    register_and_approve(ctx)
    assert client.get('/start-delivery').location=='/orders/new'
    assert 'data-auto="1"' in client.get('/profile').get_data(as_text=True)
    client.post('/onboarding/complete')
    assert 'data-auto="0"' in client.get('/profile').get_data(as_text=True)
    client.post('/logout')
    assert client.post('/login?next=/orders/new',data={'email':'client@mops.test','password':'Client-pass-27!'}).location=='/orders/new'
    assert client.post('/login?next=https://invalid.example',data={'email':'client@mops.test','password':'Client-pass-27!'}).location=='/dashboard'

@pytest.mark.parametrize('product,fee',[(k,v[1]) for k,v in PRODUCTS.items()])
def test_all_four_prices_are_enforced_by_server(ctx,product,fee):
    app,client,_=ctx;register_and_approve(ctx)
    create_order(client,product_type=product,fee='1')
    row=query(app,'SELECT * FROM orders')
    assert row['fee']==str(fee) and row['product_type']==product
    assert row['ua_name']=='Test Client' and row['ua_branch']=='101'

@pytest.mark.parametrize('field,value,message',[('product_type','','error.product'),('shipped','0','error.shipped'),('ua_city','','error.address'),('ua_name','','error.address'),('ua_branch','','error.address'),('ua_phone','abc','error.phone'),('telegram','bad name','error.telegram')])
def test_required_fields_rejected_on_server(ctx,field,value,message):
    app,client,_=ctx;register_and_approve(ctx)
    response=create_order(client,**{field:value})
    assert t(message) in visible(response)
    assert not query(app,'SELECT id FROM orders')

@pytest.mark.parametrize('field',['proof','item_photo'])
def test_fake_images_rejected(ctx,field):
    app,client,_=ctx;register_and_approve(ctx)
    response=create_order(client,**{field:(BytesIO(b'<script>bad</script>'),'picture.png')})
    assert t('error.filetype') in visible(response)
    assert not query(app,'SELECT id FROM orders')
    assert not list(Path(app.config['UPLOAD_FOLDER']).iterdir())

def test_profile_addresses_owned_and_order_snapshot(ctx):
    app,client,_=ctx;uid=register_and_approve(ctx)
    client.post('/profile',data={'name':'Renamed Client','email':'changed@mops.test','phone':'+380501234567','telegram':'changed_user','role':'admin','approved':'1'})
    assert query(app,'SELECT role FROM users WHERE id=?',(uid,))['role']=='client'
    client.post('/profile/addresses',data={'ua_name':'Recipient A','ua_phone':'+380501234567','ua_city':'Lviv','ua_branch':'12'})
    address=query(app,'SELECT * FROM addresses')
    create_order(client,address_id=str(address['id']),ua_city='',ua_name='',ua_branch='',ua_phone='')
    assert query(app,'SELECT ua_city FROM orders')['ua_city']=='Lviv'
    execute(app,'UPDATE addresses SET city=? WHERE id=?',('Kyiv',address['id']))
    assert query(app,'SELECT ua_city FROM orders')['ua_city']=='Lviv'
    execute(app,'UPDATE addresses SET user_id=1 WHERE id=?',(address['id'],))
    assert create_order(client,address_id=str(address['id'])).status_code==403

@pytest.mark.parametrize('missing',['screenshot','receipt'])
def test_payment_requires_both_documents(ctx,missing):
    app,client,_=ctx;oid=report(ctx)
    response=pay(client,oid,**{missing:(BytesIO(b''),'')})
    assert t('error.evidence') in visible(response)
    assert not query(app,'SELECT id FROM order_payments')
    assert query(app,'SELECT payment_status FROM orders')['payment_status']=='unpaid'

def test_invoice_review_reject_resubmit_approve_and_replays(ctx):
    app,client,admin=ctx;oid=report(ctx)
    page=client.get('/dashboard').get_data(as_text=True)
    assert 'invoice-banner' in page and 'Оплатить · 500 ₴' in page
    response=pay(client,oid,receipt=image('receipt.png'))
    assert t('error.same_evidence') in visible(response)
    assert not query(app,'SELECT id FROM order_payments')
    assert t('payment.submitted') in visible(pay(client,oid))
    assert client.post(f'/orders/{oid}/pay').status_code==409
    pid=query(app,'SELECT id FROM order_payments')['id']
    assert client.post(f'/admin/payment-proofs/{pid}/approve').status_code==403
    admin.post(f'/admin/payment-proofs/{pid}/reject',data={'reason':'Unreadable receipt'})
    assert query(app,'SELECT payment_status FROM orders')['payment_status']=='unpaid'
    pay(client,oid)
    pid=query(app,'SELECT id FROM order_payments ORDER BY id DESC')['id']
    assert admin.post(f'/admin/payment-proofs/{pid}/approve').status_code==302
    for _ in range(10):assert admin.post(f'/admin/payment-proofs/{pid}/approve').status_code==409
    assert query(app,'SELECT payment_status FROM orders')['payment_status']=='paid'
    assert 'invoice-banner' not in client.get('/dashboard').get_data(as_text=True)
    assert t('payment.paid') in visible(client.get(f'/orders/{oid}/pay'))

def test_dispatch_requires_payment_codes_unique_and_stable(ctx):
    app,client,admin=ctx;uid=register_and_approve(ctx)
    for _ in range(3):create_order(client)
    rows=query(app,'SELECT * FROM orders',all=True)
    codes=[]
    for row in rows:
        oid=row['id'];admin.post(f'/admin/orders/{oid}/update',data={'status':'Одержано'})
        code=query(app,'SELECT parcel_code FROM orders WHERE id=?',(oid,))['parcel_code'];codes.append(code)
        assert re.fullmatch('[A-Z2-9]{8}',code)
        response=admin.post(f'/admin/orders/{oid}/update',data={'status':'Отправлено'},follow_redirects=True)
        assert t('error.unpaid') in visible(response)
    assert len(set(codes))==3
    oid=rows[0]['id'];confirm_payment(ctx,oid)
    for _ in range(10):admin.post(f'/admin/orders/{oid}/update',data={'status':'Доставлено'})
    assert query(app,'SELECT parcel_code FROM orders WHERE id=?',(oid,))['parcel_code']==codes[0]
    assert query(app,"SELECT COUNT(*) n FROM orders WHERE delivered_at<>''")['n']==1
    assert query(app,'SELECT archived FROM orders WHERE id=?',(oid,))['archived']==1

@pytest.mark.parametrize('count,key',[(0,'new'),(9,'new'),(10,'regular'),(19,'regular'),(20,'lower'),(29,'lower'),(30,'middle'),(39,'middle'),(40,'cool'),(49,'cool'),(50,'boss'),(500,'boss')])
def test_rank_boundaries(count,key):assert rank_key(count)=='rank.'+key

def webhook(client,text,chat=555,update=1,lang='en',**override):
    body={'update_id':update,'message':{'text':text,'from':{'id':chat,'language_code':lang},'chat':{'id':chat,'type':'private'}}};body.update(override)
    return client.post('/telegram/webhook',json=body,headers={'X-Telegram-Bot-Api-Secret-Token':'test-webhook-secret'})

def test_bot_start_link_commands_language_and_secure_binding(ctx,monkeypatch):
    app,client,_=ctx;uid=register_and_approve(ctx)
    app.config.update(TELEGRAM_WEBHOOK_SECRET='test-webhook-secret',TELEGRAM_WEBAPP_URL='https://mops.example.test')
    tg=app.extensions['mops_features'].telegram;send=Mock(return_value={'message_id':1});monkeypatch.setattr(tg,'message',send);monkeypatch.setattr(tg,'call',Mock(return_value=True))
    assert client.post('/telegram/webhook',json={}).status_code==403
    assert webhook(client,'/start').status_code==200
    assert 'mini app' in send.call_args.args[1]
    assert send.call_args.args[2][0][0]['web_app']['url']=='https://mops.example.test'
    token=query(app,'SELECT telegram_token FROM users WHERE id=?',(uid,))['telegram_token']
    webhook(client,f'/start mp_{uid}_{token}',update=2)
    assert query(app,'SELECT telegram_chat_id FROM users WHERE id=?',(uid,))['telegram_chat_id']=='555'
    assert 'Бонусы' in send.call_args.args[1] and 'Новичок' in send.call_args.args[1]
    webhook(client,f'/start mp_{uid}_{token}',chat=666,update=3)
    assert query(app,'SELECT telegram_chat_id FROM users WHERE id=?',(uid,))['telegram_chat_id']=='555'
    webhook(client,'/start',update=4,callback_query={'id':'cb1','data':'lang:uk','from':{'id':555},'message':{'chat':{'id':555,'type':'private'}}},message=None)
    assert query(app,'SELECT language FROM users WHERE id=?',(uid,))['language']=='uk'
    assert 'ваш профіль' in send.call_args.args[1]
    count=send.call_count;webhook(client,'/start',update=4);assert send.call_count==count
    webhook(client,'/orders',update=5);assert 'Мої посилки' in send.call_args.args[1]
    webhook(client,'/language',update=6);assert len(send.call_args.args[2][0])==3

def test_leaders_use_delivered_counts_and_opt_in_names(ctx,monkeypatch):
    app,client,_=ctx;uid=register_and_approve(ctx);create_order(client)
    app.config['TELEGRAM_WEBHOOK_SECRET']='test-webhook-secret'
    send=Mock();monkeypatch.setattr(app.extensions['mops_features'].telegram,'message',send)
    webhook(client,'/leaders');assert 'first completed' in send.call_args.args[1]
    execute(app,"UPDATE orders SET delivered_at='2026-10-26',archived=1,status='Архив'")
    webhook(client,'/leaders',update=2);text=send.call_args.args[1]
    assert f'Customer #{uid}' in text and '— 1' in text
    assert 'Test Client' not in text and 'mops_client' not in text
    execute(app,'UPDATE users SET leaderboard_public=1 WHERE id=?',(uid,))
    webhook(client,'/leaders',update=3);assert '@mops_client' in send.call_args.args[1]

def test_files_sent_as_documents_cached_and_private(ctx,monkeypatch):
    app,client,admin=ctx;uid=register_and_approve(ctx);create_order(client);oid=first_order_id(app)
    file=query(app,'SELECT item_photo FROM orders')['item_photo'];tg=app.extensions['mops_features'].telegram
    execute(app,"UPDATE users SET telegram_chat_id='555' WHERE id=?",(uid,));app.config['TELEGRAM_BOT_TOKEN']='123:fake-test-only'
    call=Mock(return_value={'document':{'file_id':'cached-document-id'}});monkeypatch.setattr(tg,'call',call)
    assert client.post(f'/orders/{oid}/files/item_photo/send').status_code==302
    assert call.call_args.args[0]=='sendDocument' and 'files' in call.call_args.kwargs
    client.post(f'/orders/{oid}/files/item_photo/send')
    assert call.call_args.args[1]['document']=='cached-document-id' and not call.call_args.kwargs
    response=client.get('/uploads/'+file)
    assert response.mimetype=='text/html' and '<img' not in response.get_data(as_text=True)
    execute(app,'UPDATE orders SET user_id=1 WHERE id=?',(oid,))
    assert client.post(f'/orders/{oid}/files/item_photo/send').status_code==403
    assert client.get('/uploads/'+file).status_code==403
    assert admin.get('/uploads/'+file).status_code==200

def test_csrf_protects_forms_but_webhook_uses_own_secret(ctx):
    app,client,_=ctx;app.config['CSRF_ENABLED']=True
    response=client.get('/login');token=re.search('name="csrf_token" value="([^"]+)"',response.get_data(as_text=True)).group(1)
    data={'email':'admin@mops.test','password':'Mops-test-Admin-27!'}
    assert client.post('/login',data=data).status_code==400
    assert client.post('/login',data=dict(data,csrf_token=token)).status_code==302
    assert client.get('/admin').status_code==200
    assert client.post('/admin/settings',data={'payment_card':'bad'}).status_code==400
    assert client.post('/logout',data={'csrf_token':token}).status_code==400 # session rotated at login

def test_address_change_approval_updates_shipping_snapshot_once(ctx):
    app,client,admin=ctx;register_and_approve(ctx);create_order(client);oid=first_order_id(app)
    client.post(f'/orders/{oid}/change',data={'ua_name':'New Recipient','ua_phone':'+380671112233','ua_city':'Odesa','ua_branch':'42'})
    assert query(app,'SELECT ua_city FROM orders')['ua_city']=='Kyiv'
    cid=query(app,'SELECT id FROM changes')['id']
    admin.post(f'/admin/changes/{cid}/approve')
    row=query(app,'SELECT * FROM orders');assert row['ua_city']=='Odesa' and row['phone']==row['ua_phone']=='+380671112233'
    assert admin.post(f'/admin/changes/{cid}/approve').status_code==409
    client.post(f'/orders/{oid}/change',data={'ua_name':'Injected\ntelegram: attacker'})
    assert query(app,'SELECT COUNT(*) n FROM changes')['n']==1

def test_bonus_approval_is_not_repeatable(ctx):
    app,client,admin=ctx;uid=register_and_approve(ctx)
    client.post('/reviews',data={'review_image':image()})
    rid=query(app,'SELECT id FROM reviews')['id']
    admin.post(f'/admin/reviews/{rid}/approve')
    for _ in range(10):assert admin.post(f'/admin/reviews/{rid}/approve').status_code==409
    assert query(app,'SELECT bonus_balance FROM users WHERE id=?',(uid,))['bonus_balance']==1

@pytest.mark.parametrize('lang',['ru','uk','en'])
def test_new_pages_complete_translation_and_forms_csrf(ctx,lang):
    app,client,admin=ctx;oid=report(ctx)
    for agent,path in [(client,'/profile'),(client,'/orders/new'),(client,'/dashboard'),(client,f'/orders/{oid}/pay'),(admin,'/admin')]:
        response=agent.get(path+'?lang='+lang);html=response.get_data(as_text=True)
        assert response.status_code==200
        assert not re.search(r'\b(?:profile|address|payment|product|tracking|tutorial|rank|file)\.[a-z_]+\b',visible(response)),visible(response)
        if lang=='en':assert not re.search('[А-Яа-яІіЇїЄє]',visible(response)),visible(response)
        forms=re.findall(r'<form\b[^>]*method="post".*?</form>',html,re.S)
        assert all('name="csrf_token"' in form for form in forms)
        assert not re.search('[✳✦★☆⭐🌟✨]',visible(response))

def test_migration_preserves_legacy_accounts_files_and_orders(tmp_path,monkeypatch):
    from app import create_app
    tree=ast.parse(Path('app.py').read_text(encoding='utf-8-sig'))
    schema=next(n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='executescript')
    path=tmp_path/'legacy.sqlite3';uploads=tmp_path/'uploads';uploads.mkdir();(uploads/'legacy.png').write_bytes(b'original-image')
    password=generate_password_hash('legacy-password')
    with sqlite3.connect(path) as c:
        c.executescript(schema)
        c.execute("INSERT INTO users(id,email,name,password,role,approved,telegram_token,created) VALUES(77,'owner@test.example','Owner',?,'admin',1,'old-token','2020')",(password,))
        c.execute("INSERT INTO orders(id,user_id,item,phone,delivery,telegram,proof,item_photo,status,fee,tracking,report,created,updated) VALUES(90,77,'Old parcel','12345678','Домашняя доставка','old_user','oldproof.png','legacy.png','Доставлено','450','OLD-TRACK','old-report.png','2020','2021')")
    config={'TESTING':True,'SECRET_KEY':'migration-test','DATABASE':str(path),'UPLOAD_FOLDER':str(uploads)}
    app=create_app(config)
    assert query(app,'SELECT password FROM users WHERE id=77')['password']==password
    row=query(app,'SELECT * FROM orders WHERE id=90');assert row['tracking']=='OLD-TRACK' and row['fee']=='450' and row['report']=='old-report.png' and row['delivered_at']=='2021'
    assert len(row['parcel_code'])==8 and query(app,'SELECT onboarding_completed FROM users WHERE id=77')[0]==1
    backups=list((tmp_path/'backups').glob('*.sqlite3'));assert len(backups)==1
    with sqlite3.connect(backups[0]) as c:assert 'parcel_code' not in {r[1] for r in c.execute('PRAGMA table_info(orders)')}
    create_app(config)
    assert query(app,'SELECT parcel_code FROM orders WHERE id=90')[0]==row['parcel_code']
    assert len(list((tmp_path/'backups').glob('*.sqlite3')))==1
    assert (uploads/'legacy.png').read_bytes()==b'original-image'

def test_generated_local_session_secret_is_private_and_persistent(tmp_path):
    from app import create_app
    config={'TESTING':True,'SECRET_KEY':'replace-this','DATABASE':str(tmp_path/'db.sqlite3'),'UPLOAD_FOLDER':str(tmp_path/'uploads')}
    first=create_app(config);second=create_app(config)
    assert len(first.secret_key)>=48 and first.secret_key==second.secret_key
    if __import__('os').name=='posix':
        assert (tmp_path/'session.secret').stat().st_mode & 0o077==0

def test_tracking_generator_retries_collision(ctx,monkeypatch):
    app,client,_=ctx;register_and_approve(ctx);create_order(client)
    execute(app,"UPDATE orders SET parcel_code='AAAAAAAA'")
    values=iter('AAAAAAAABBBBBBBB');monkeypatch.setattr('domain.secrets.choice',lambda alphabet:next(values))
    with sqlite3.connect(app.config['DATABASE']) as c:assert generate_code(c)=='BBBBBBBB'

def test_bot_does_not_offer_insecure_mini_app_link(ctx):
    app,_,_=ctx;feature=app.extensions['mops_features']
    for url in ['http://mops.example.test','javascript:alert(1)','https://name:secret@mops.example.test']:
        app.config['TELEGRAM_WEBAPP_URL']=url
        assert not any('web_app' in button for row in feature.webapp_keyboard('ru') for button in row)

def test_document_failure_is_reported_without_exposing_token(ctx,monkeypatch):
    app,client,_=ctx;uid=register_and_approve(ctx);create_order(client);oid=first_order_id(app)
    execute(app,"UPDATE users SET telegram_chat_id='555' WHERE id=?",(uid,))
    app.config['TELEGRAM_BOT_TOKEN']='123:super-secret-test'
    monkeypatch.setattr(app.extensions['mops_features'].telegram,'call',Mock(return_value=None))
    response=client.post(f'/orders/{oid}/files/item_photo/send',follow_redirects=True)
    assert t('file.failed') in visible(response) and 'super-secret-test' not in response.get_data(as_text=True)

def test_admin_role_survives_restart_and_username_changes(ctx,monkeypatch):
    from app import create_app
    app,client,admin=ctx;uid=register_and_approve(ctx)
    client.post('/profile',data={'name':'Fake Admin','email':'client@mops.test','telegram':'amrbasota','role':'admin'})
    assert client.get('/admin').status_code==403
    monkeypatch.setenv('ADMIN_PASSWORD','changed-env-not-a-password-reset')
    restarted=create_app(dict(app.config));admin2=restarted.test_client()
    assert admin2.post('/login',data={'email':'admin@mops.test','password':'Mops-test-Admin-27!'}).status_code==302
    assert admin2.get('/admin').status_code==200

def test_source_has_no_star_glyphs_or_missing_translation_keys():
    CATALOG.update(__import__('extra_i18n').EXTRA)
    paths=[*Path('templates').glob('*.html'),*Path('static').glob('*')]
    for path in paths:
        source=path.read_text(encoding='utf-8-sig')
        assert not re.search('[✳✦★☆⭐🌟✨]',source)
        keys=re.findall(r"\b(?:t|tr)\('([^']+)'",source)
        assert all(key in CATALOG or key.endswith('.') for key in keys)

def test_every_rendered_internal_link_and_form_resolves(ctx):
    from html.parser import HTMLParser
    from urllib.parse import urlsplit
    app,client,admin=ctx;oid=report(ctx);pay(client,oid)
    class Controls(HTMLParser):
        def __init__(self):super().__init__();self.targets=[];self.form_depth=0;self.ids=set()
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if 'id' in a:assert a['id'] not in self.ids;self.ids.add(a['id'])
            if tag=='form':
                assert self.form_depth==0,'Nested form breaks browser submissions';self.form_depth+=1
                self.targets.append((a.get('action',''),a.get('method','get').upper()))
            if tag=='a':self.targets.append((a.get('href',''),'GET'))
        def handle_endtag(self,tag):
            if tag=='form':self.form_depth-=1
    routes=app.url_map.bind('localhost')
    for agent,page in [(client,'/'),(client,'/profile'),(client,'/dashboard'),(client,'/orders/new'),(client,f'/orders/{oid}/pay'),(admin,'/admin')]:
        controls=Controls();controls.feed(agent.get(page).get_data(as_text=True));assert controls.form_depth==0
        for target,method in controls.targets:
            path=urlsplit(target).path
            if target.startswith('https:') or target.startswith('#'):continue
            endpoint,values=routes.match(path or page,method=method)
            assert endpoint in app.view_functions
