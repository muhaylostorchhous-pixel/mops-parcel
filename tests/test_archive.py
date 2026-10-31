"""Destructive cleanup is exercised only on isolated test databases."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from test_services import env, register, query, execute
from test_e2e import create_order, image
from test_i18n import visible

CHANNEL='-1001234567890'
CLIENT='123456789'


def prepare(env, delivered=True):
    app,client,admin,_=env;uid=register(env);create_order(client)
    oid=query(app,'SELECT id FROM orders')[0]
    admin.post(f'/admin/orders/{oid}/update',data={'report':image('report.png')})
    execute(app,'UPDATE users SET telegram_chat_id=? WHERE id=?',(CLIENT,uid))
    if delivered:
        execute(app,"UPDATE orders SET status='Доставлено',archived=1,delivered_at=updated,payment_status='paid' WHERE id=?",(oid,))
    app.config.update(TELEGRAM_BOT_TOKEN='123456:test-only',TELEGRAM_ARCHIVE_CHAT_ID=CHANNEL)
    calls=[]
    def api(method,payload,files=None):
        calls.append((method,dict(payload),bool(files)))
        if method=='getChat':return {'id':int(CHANNEL),'type':'channel'}
        if method=='getFile':return {'file_id':payload['file_id'],'file_path':'documents/report.png'}
        if method=='sendDocument':return {'message_id':len(calls),'chat':{'id':int(payload['chat_id'])},'document':{'file_id':'document-test-id'}}
        return {'message_id':len(calls)}
    app.extensions['mops_features'].telegram.call=api
    return query(app,'SELECT * FROM orders WHERE id=?',(oid,)),calls,api


def process(app,name):
    with app.app_context():app.extensions['report_archive'].process(name)


def row(app):return query(app,'SELECT * FROM report_archives')
def has_report(app,o):return bool(query(app,'SELECT name FROM file_objects WHERE name=?',(o['report'],)))


def test_delivered_report_removed_only_after_both_receipts(env):
    app,client,_,_=env;o,calls,_=prepare(env);process(app,o['report'])
    assert row(app)['state']=='cleaned' and row(app)['removed_bytes']>0
    assert not has_report(app,o)
    assert query(app,'SELECT COUNT(*) FROM file_objects')[0]==2
    assert query(app,'SELECT report FROM orders')[0]==o['report']
    assert {r['chat_id'] for r in query(app,'SELECT * FROM telegram_deliveries',many=True)}=={CHANNEL,CLIENT}
    assert any(method=='getFile' for method,_,_ in calls)
    assert 'stored in Telegram' in visible(client.get(f"/orders/{o['id']}?lang=en"))


def test_no_cleanup_before_actual_delivery_even_if_archived(env):
    app,_,_,_=env;o,calls,_=prepare(env,False)
    execute(app,"UPDATE orders SET status='Архив',archived=1,delivered_at=''")
    process(app,o['report'])
    assert row(app)['state']=='confirmed' and has_report(app,o)
    assert not any(method=='getFile' for method,_,_ in calls)


def test_confirmed_then_delivered_cleans_without_duplicate_documents(env):
    app,_,admin,_=env;o,calls,_=prepare(env,False);process(app,o['report'])
    assert row(app)['state']=='confirmed'
    execute(app,"UPDATE orders SET payment_status='paid'")
    admin.post(f"/admin/orders/{o['id']}/update",data={'status':'Доставлено'})
    process(app,o['report'])
    assert row(app)['state']=='cleaned'
    assert sum(method=='sendDocument' for method,_,_ in calls)==2


@pytest.mark.parametrize('failure',['channel','archive','client','download','incomplete_receipt'])
def test_failures_never_delete_report(env,failure):
    app,_,_,_=env;o,_,base=prepare(env)
    def api(method,payload,files=None):
        if failure=='channel' and method=='getChat':return None
        if failure=='archive' and method=='sendDocument' and payload['chat_id']==CHANNEL:return None
        if failure=='client' and method=='sendDocument' and payload['chat_id']==CLIENT:return None
        if failure=='download' and method=='getFile':return None
        if failure=='incomplete_receipt' and method=='sendDocument':return {'document':{'file_id':'id-without-message'}}
        return base(method,payload,files)
    app.extensions['mops_features'].telegram.call=api;process(app,o['report'])
    assert has_report(app,o) and not row(app)['cleaned_at']
    assert row(app)['last_error']


@pytest.mark.parametrize('chat_info',[{'type':'supergroup'},{'username':'public_channel'},{'active_usernames':['public_alias']},{'message_auto_delete_time':86400}])
def test_public_or_disappearing_archive_rejected(env,chat_info):
    app,_,_,_=env;o,calls,base=prepare(env)
    def api(method,payload,files=None):
        if method=='getChat':return {'id':int(CHANNEL),'type':'channel',**chat_info}
        return base(method,payload,files)
    app.extensions['mops_features'].telegram.call=api;process(app,o['report'])
    assert row(app)['last_error']=='channel_invalid' and has_report(app,o)
    assert not any(method=='sendDocument' for method,_,_ in calls)


def test_unlinked_client_keeps_bytes_then_link_allows_cleanup(env):
    app,_,_,_=env;o,calls,_=prepare(env);execute(app,"UPDATE users SET telegram_chat_id='' WHERE id=?",(o['user_id'],))
    process(app,o['report']);assert row(app)['last_error']=='link_telegram' and has_report(app,o)
    execute(app,'UPDATE users SET telegram_chat_id=? WHERE id=?',(CLIENT,o['user_id']))
    with app.app_context():app.extensions['services'].linked(o['user_id'])
    process(app,o['report']);assert row(app)['state']=='cleaned'
    assert sum(method=='sendDocument' and payload['chat_id']==CHANNEL for method,payload,_ in calls)==1


def test_missing_archive_config_makes_no_calls_or_deletes(env):
    app,_,_,_=env;o,calls,_=prepare(env);app.config['TELEGRAM_ARCHIVE_CHAT_ID']=''
    process(app,o['report']);assert not calls and has_report(app,o)


def test_purged_file_resends_after_restart_without_local_uploads(env,tmp_path):
    app,client,_,_=env;o,calls,api=prepare(env);process(app,o['report'])
    from app import create_app
    restarted=create_app(dict(app.config,UPLOAD_FOLDER=str(tmp_path/'empty-uploads')))
    restarted.extensions['mops_features'].telegram.call=api
    calls.clear()
    with restarted.app_context():
        assert restarted.extensions['services'].file_bytes(o['report']) is None
        assert restarted.extensions['mops_features'].telegram.document(CLIENT,o['report'],'Archived report')
    assert calls==[('sendDocument',{'chat_id':CLIENT,'caption':'Archived report','document':'document-test-id'},False)]
    # Startup must not re-import a legacy copy of an intentionally removed report.
    (Path(restarted.config['UPLOAD_FOLDER'])/o['report']).write_bytes(b'legacy local copy')
    again=create_app(dict(restarted.config))
    assert not has_report(again,o)


def test_reopened_order_during_probe_is_not_purged(env):
    app,_,_,_=env;o,_,base=prepare(env)
    def api(method,payload,files=None):
        if method=='getFile':execute(app,"UPDATE orders SET status='Одержано',archived=0")
        return base(method,payload,files)
    app.extensions['mops_features'].telegram.call=api;process(app,o['report'])
    assert has_report(app,o) and row(app)['state']=='confirmed'


def test_bot_changed_during_probe_preserves_original(env):
    app,_,_,_=env;o,_,base=prepare(env)
    def api(method,payload,files=None):
        if method=='getFile':app.config['TELEGRAM_BOT_TOKEN']='654321:another-test-bot'
        return base(method,payload,files)
    app.extensions['mops_features'].telegram.call=api;process(app,o['report'])
    assert has_report(app,o) and row(app)['last_error']=='bot_changed'


@pytest.mark.parametrize('bad', ['wrong_recipient','zero_message'])
def test_receipt_must_match_destination_and_persisted_message(env,bad):
    app,_,_,_=env;o,_,base=prepare(env)
    def api(method,payload,files=None):
        result=base(method,payload,files)
        if method=='sendDocument':
            if bad=='wrong_recipient':result['chat']['id']=998877
            else:result['message_id']=0
        return result
    app.extensions['mops_features'].telegram.call=api;process(app,o['report'])
    assert has_report(app,o) and not query(app,'SELECT name FROM telegram_deliveries')


def test_replaced_versions_are_tracked_and_only_cleaned_after_delivery(env):
    app,_,admin,_=env;o,_,_=prepare(env,False)
    admin.post(f"/admin/orders/{o['id']}/update",data={'report':image('second-report.png')})
    names=[r['name'] for r in query(app,'SELECT name FROM report_archives',many=True)]
    assert len(names)==2
    for name in names:process(app,name)
    assert query(app,"SELECT COUNT(*) FROM report_archives WHERE state='confirmed'")[0]==2
    execute(app,"UPDATE orders SET payment_status='paid'")
    admin.post(f"/admin/orders/{o['id']}/update",data={'status':'Доставлено'})
    for name in names:process(app,name)
    assert query(app,"SELECT COUNT(*) FROM report_archives WHERE state='cleaned'")[0]==2
    assert query(app,'SELECT COUNT(*) FROM file_objects')[0]==2


def test_shared_payment_or_item_file_never_purged(env):
    app,_,_,_=env;o,_,_=prepare(env);execute(app,'UPDATE orders SET item_photo=?',(o['report'],))
    process(app,o['report']);assert has_report(app,o) and row(app)['last_error']=='shared_file'


def test_double_processing_sends_once_and_removes_once(env):
    app,_,_,_=env;o,calls,base=prepare(env);entered=Event();release=Event()
    def api(method,payload,files=None):
        if method=='getChat':entered.set();assert release.wait(10)
        return base(method,payload,files)
    app.extensions['mops_features'].telegram.call=api
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(process,app,o['report']);assert entered.wait(10)
        second=pool.submit(process,app,o['report']);second.result(timeout=10);release.set();first.result(timeout=10)
    process(app,o['report'])
    assert sum(method=='sendDocument' for method,_,_ in calls)==2
    assert query(app,"SELECT COUNT(*) FROM audit_events WHERE action='report_archived'")[0]==1


def test_expired_worker_lease_recovers(env):
    app,_,_,_=env;o,_,_=prepare(env)
    execute(app,"UPDATE report_archives SET state='sending',lease_token='old',lease_until=0")
    process(app,o['report']);assert row(app)['state']=='cleaned'


def test_admin_page_permissions_csrf_and_languages(env):
    app,client,admin,_=env;prepare(env)
    assert client.get('/admin/report-archive').status_code==403
    for lang,label in [('ru','Архив фотоотчётов'),('uk','Архів фотозвітів'),('en','Photo report archive')]:
        response=admin.get('/admin/report-archive?lang='+lang)
        assert response.status_code==200 and label in visible(response)
        assert 'arc.' not in visible(response)
    app.config['CSRF_ENABLED']=True
    assert admin.post('/admin/report-archive/retry').status_code==400
    with admin.session_transaction() as s:csrf=s['csrf']
    assert admin.post('/admin/report-archive/retry',data={'csrf_token':csrf}).status_code==302
    assert app.extensions['services'].wake_event.is_set()


def test_health_check_and_assets_do_not_open_database(env,monkeypatch):
    app,client,_,_=env;register(env)
    import database
    def fail(*a,**kw):raise AssertionError('Probe opened a database connection')
    monkeypatch.setattr(database,'connect',fail)
    assert client.get('/healthz').json=={'status':'ok'}
    assert not client.get('/healthz').headers.getlist('Set-Cookie')
    assert client.get('/static/workspace.css').status_code==200


def test_background_waits_without_holding_db_and_wakes_on_events(env):
    app,_,_,_=env;svc=app.extensions['services'];assert svc.check_interval==3600
    class Wake:
        waits=[]
        def clear(self):pass
        def wait(self,seconds):self.waits.append(seconds);svc.stop_event.set()
    wake=Wake();svc.wake_event=wake
    # No bot token: there must not even be an idle database query.
    svc.db=lambda:(_ for _ in ()).throw(AssertionError('Idle worker queried database'))
    svc.worker();assert wake.waits==[3600]


def test_archiveid_only_for_admin(env):
    app,client,_,_=env;register(env)
    app.config.update(TELEGRAM_WEBHOOK_SECRET='test-webhook',TELEGRAM_ADMIN_CHAT_ID='777')
    bot=app.extensions['mops_features'].telegram;messages=[]
    bot.message=lambda chat,text,keyboard=None:messages.append(text)
    def post(uid,update,origin=None):
        m={'chat':{'id':uid,'type':'private'},'from':{'id':uid,'language_code':'en'},'text':'/archiveid'}
        if origin:m['forward_origin']=origin
        return client.post('/telegram/webhook',json={'update_id':update,'message':m},headers={'X-Telegram-Bot-Api-Secret-Token':'test-webhook'})
    assert post(777,1).status_code==200 and 'Forward a message' in messages[-1]
    post(777,2,{'type':'channel','chat':{'id':int(CHANNEL),'type':'channel'}})
    assert 'TELEGRAM_ARCHIVE_CHAT_ID='+CHANNEL in messages[-1]
    post(888,3);assert CHANNEL not in messages[-1]
