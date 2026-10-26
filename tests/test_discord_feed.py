import re
import sqlite3
import time
from copy import deepcopy
from unittest.mock import Mock
import pytest
import requests
from test_e2e import ctx,register_and_approve
from test_i18n import visible
from discord_feed import normalize,safe_url,image_url

CHANNEL='123456789012345678'
GUILD='223456789012345678'
WEBHOOK='323456789012345678'
def message(mid='423456789012345678',**changes):
    data={'id':mid,'channel_id':CHANNEL,'guild_id':GUILD,'webhook_id':WEBHOOK,'content':'','timestamp':'2026-10-26T18:00:00Z',
    'embeds':[{'title':'Vintage jacket','url':'https://www.vinted.co.uk/items/123-jacket','fields':[{'name':'Price','value':'£35'},{'name':'Size','value':'M'}],'image':{'url':'https://cdn.discordapp.com/attachments/1/2/photo.jpg?ex=abc'}}]}
    data.update(changes);return data

def response(body,status=200):return Mock(status_code=status,json=Mock(return_value=body))
def setup(ctx,monkeypatch,batch=None):
    app,client,admin=ctx;register_and_approve(ctx);feed=app.extensions['discord_feed'];feed.token='test-token-not-real';feed.channel=CHANNEL
    api=Mock(side_effect=[response({'id':CHANNEL,'guild_id':GUILD}),response(batch if batch is not None else [message()])])
    monkeypatch.setattr(feed,'api',api);return feed,api

def expire(app):
    with sqlite3.connect(app.config['DATABASE']) as c:c.execute('UPDATE discord_feed_state SET retry_at=0')

def test_01_webhook_embeds_price_photo_source():
    row=normalize(message(),CHANNEL)
    assert row['title']=='Vintage jacket' and row['price']=='£35'
    assert row['url'].startswith('https://www.vinted.co.uk/items/')
    assert row['image'].startswith('https://cdn.discordapp.com/')
    assert row['source']==f'https://discord.com/channels/{GUILD}/{CHANNEL}/{message()["id"]}'

def test_02_text_and_attachment_fallback():
    row=normalize(message(content='Shoes\nPrice: 700 UAH\nhttps://www.ebay.com/itm/123',embeds=[],attachments=[{'content_type':'image/png','url':'https://media.discordapp.net/attachments/a/photo.png'}]),CHANNEL)
    assert row['title']=='Shoes' and row['price']=='700 UAH' and row['image']
    assert row['url']=='https://www.ebay.com/itm/123'

def test_03_ignore_other_channels_and_human_messages():
    assert normalize(message(channel_id='999'),CHANNEL) is None
    assert normalize(message(webhook_id=None),CHANNEL) is None
    assert normalize(message(id='not-a-snowflake'),CHANNEL) is None
    assert normalize(message(content='',embeds=[],attachments=[]),CHANNEL) is None

@pytest.mark.parametrize('url',['javascript:alert(1)','http://example.com','https://localhost/test','https://127.0.0.1/test','https://192.168.0.1/test','https://foo.local/test','https://user:pass@example.com','https://example.com:444/path','https://example.com/\nsecret'])
def test_04_unsafe_links_rejected(url):assert safe_url(url)==''

def test_05_untrusted_image_host_rejected():
    assert image_url('https://evil.example/tracker.png')==''
    assert image_url('https://cdn.discordapp.com.evil.example/a.png')==''
    assert image_url('https://images1.vinted.net/a.jpg')

def test_06_login_and_approval_required(ctx,monkeypatch):
    app,client,_=ctx;feed=app.extensions['discord_feed'];api=Mock();monkeypatch.setattr(feed,'api',api)
    assert client.get('/parser').status_code==302 and client.get('/parser/data').status_code==302
    client.post('/register',data={'name':'Pending','email':'pending@test.example','password':'Testing-password'})
    assert client.get('/parser').status_code==403 and client.get('/parser/data').status_code==403
    api.assert_not_called()

def test_07_disabled_feed_safe_and_no_network(ctx,monkeypatch):
    app,client,_=ctx;register_and_approve(ctx);feed=app.extensions['discord_feed'];feed.token=''
    api=Mock();monkeypatch.setattr(feed,'api',api)
    data=client.get('/parser/data?lang=en').json
    assert data['cards']==[] and not data['enabled'] and 'not connected' in data['status']
    api.assert_not_called()

def test_08_import_deduplicate_refresh_edits_and_throttle(ctx,monkeypatch):
    app,client,_=ctx;feed,api=setup(ctx,monkeypatch)
    first=client.get('/parser/data').json
    assert len(first['cards'])==1 and api.call_count==2
    for _ in range(10):assert len(client.get('/parser/data').json['cards'])==1
    assert api.call_count==2
    expire(app);edited=message();edited['embeds'][0]['fields'][0]['value']='£30'
    api.side_effect=[response([]),response([edited])]
    second=client.get('/parser/data').json
    assert len(second['cards'])==1 and second['cards'][0]['price']=='£30'
    assert api.call_args_list[2].args[1]['after']==message()['id']

def test_09_rate_limit_and_cached_cards(ctx,monkeypatch):
    app,client,admin=ctx;feed,api=setup(ctx,monkeypatch);client.get('/parser/data');expire(app)
    api.side_effect=[response({'retry_after':120},429)]
    data=client.get('/parser/data?lang=en').json
    assert len(data['cards'])==1 and 'Could not refresh' in data['status'] and data['admin_error']==''
    with app.app_context():assert feed.state()['retry_at']>time.time()+100
    assert 'rate limited' in admin.get('/parser/data?lang=en').json['admin_error']
    assert api.call_count==3

@pytest.mark.parametrize('status',[401,403,404,500])
def test_10_api_failure_explained_to_admin_without_token(ctx,monkeypatch,status):
    app,client,admin=ctx;feed,api=setup(ctx,monkeypatch);api.side_effect=[response({},status)]
    data=admin.get('/parser/data?lang=en').json
    assert data['status'] and data['admin_error'] and 'test-token' not in str(data)
    assert data['cards']==[]

def test_11_missing_content_intent(ctx,monkeypatch):
    _,_,admin=ctx;setup(ctx,monkeypatch,[message(embeds=[])])
    data=admin.get('/parser/data?lang=en').json
    assert 'Message Content Intent' in data['admin_error'] and data['cards']==[]

def test_12_xss_escaped_and_all_languages(ctx,monkeypatch):
    _,client,_=ctx;m=message();m['embeds'][0]['title']='<script>alert(1)</script>';m['embeds'][0]['url']='javascript:alert(1)'
    setup(ctx,monkeypatch,[m])
    for lang in ['ru','uk','en']:
        result=client.get('/parser?lang='+lang);html=result.get_data(as_text=True)
        assert result.status_code==200 and '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;' in html and 'javascript:alert' not in html
        assert not re.search(r'feed\.[a-z_]+',visible(result))
        if lang=='en':assert not re.search('[А-Яа-яІіЇїЄє]',visible(result))

def test_13_pagination_search_webhook_filter(ctx,monkeypatch):
    app,client,_=ctx
    batch=[message(str(423456789012345678+i)) for i in range(30)]
    setup(ctx,monkeypatch,batch)
    data=client.get('/parser/data').json;assert len(data['cards'])==24 and data['has_more']
    page=client.get('/parser/data?page=2').json;assert len(page['cards'])==6 and not page['has_more']
    assert not client.get('/parser/data?q=missing').json['cards']
    assert not client.get('/parser/data?q=%25').json['cards']
    assert len(client.get('/parser/data?q=Vintage').json['cards'])==24
    app.extensions['discord_feed'].webhook='999'
    assert client.get('/parser/data').json['cards']==[]

def test_14_network_error_does_not_delete_cache_or_advance_cursor(ctx,monkeypatch):
    app,client,_=ctx;feed,api=setup(ctx,monkeypatch);client.get('/parser/data');expire(app)
    api.side_effect=requests.Timeout('do not log token')
    assert len(client.get('/parser/data').json['cards'])==1
    with app.app_context():assert feed.state()['cursor']==message()['id']

def test_15_restart_keeps_cached_feed(ctx,monkeypatch):
    from app import create_app
    app,client,_=ctx;feed,api=setup(ctx,monkeypatch);client.get('/parser/data')
    config=dict(app.config,DISCORD_BOT_TOKEN='fake',DISCORD_CHANNEL_ID=CHANNEL)
    second=create_app(config);cached=second.extensions['discord_feed'];mock=Mock();monkeypatch.setattr(cached,'api',mock)
    user=second.test_client()
    with user.session_transaction() as session:session['uid']=2
    assert len(user.get('/parser/data').json['cards'])==1
    mock.assert_not_called()

def test_16_telegram_parser_button_and_command(ctx,monkeypatch):
    app,client,_=ctx;register_and_approve(ctx)
    app.config.update(TELEGRAM_WEBAPP_URL='https://mops.example',TELEGRAM_WEBHOOK_SECRET='test-secret')
    feature=app.extensions['mops_features'];send=Mock();monkeypatch.setattr(feature.telegram,'message',send)
    result=client.post('/telegram/webhook',headers={'X-Telegram-Bot-Api-Secret-Token':'test-secret'},json={'update_id':101,'message':{'text':'/parser','chat':{'id':555,'type':'private'},'from':{'id':555,'language_code':'en'}}})
    assert result.status_code==200
    assert any(button.get('web_app',{}).get('url')=='https://mops.example/parser' for row in send.call_args.args[2] for button in row)

def test_17_bot_auth_uses_fixed_discord_api(ctx,monkeypatch):
    app,_,_=ctx;feed=app.extensions['discord_feed'];feed.token='fake-token'
    get=Mock(return_value=response([]));monkeypatch.setattr('discord_feed.requests.get',get)
    feed.api('channels/'+CHANNEL+'/messages',{'limit':100})
    assert get.call_args.args[0]=='https://discord.com/api/v10/channels/'+CHANNEL+'/messages'
    assert get.call_args.kwargs['headers']['Authorization']=='Bot fake-token'
    assert get.call_args.kwargs['allow_redirects'] is False

def test_18_grailed_listing_is_not_mistaken_for_photo():
    m=message();m['embeds'][0]['url']='https://www.grailed.com/listings/123-jacket'
    assert normalize(m,CHANNEL)['url']=='https://www.grailed.com/listings/123-jacket'

def test_19_full_batch_cursor_does_not_skip_to_latest(ctx,monkeypatch):
    app,client,_=ctx
    batch=[message(str(423456789012345678+i)) for i in range(100)]
    feed,api=setup(ctx,monkeypatch,batch)
    client.get('/parser/data')
    with app.app_context():assert feed.state()['cursor']==str(423456789012345777)
    expire(app);api.side_effect=[response([message('423456789012345778')]),response([message('423456789012345800')])]
    client.get('/parser/data')
    with app.app_context():assert feed.state()['cursor']=='423456789012345778'
