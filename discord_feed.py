"""Read-only Discord bot channel feed; refreshes while the feed is open."""
import ipaddress
import os
import re
import threading
import time
from urllib.parse import urlsplit
import requests
from flask import g, jsonify, render_template, request
from i18n import CATALOG, t
from discord_i18n import STRINGS
CATALOG.update(STRINGS)
ID = re.compile(r'^[0-9]{1,22}$')
URL = re.compile(r'https://[^\s<>\[\]()"\'\x00-\x1f]+')
PRICE = re.compile(r'(?:[£€$₴]\s*\d[\d\s.,]*|\d[\d\s.,]*\s*(?:GBP|EUR|USD|UAH|PLN|грн|zł|£|€|\$|₴))',re.I)

def safe_url(value):
    if not isinstance(value,str) or len(value)>2048 or any(ord(c)<32 for c in value):return ''
    try:
        p=urlsplit(value);host=(p.hostname or '').lower()
        if p.scheme!='https' or not host or p.username or p.password or p.port not in (None,443):return ''
        if '.' not in host or host.endswith(('.localhost','.local','.internal')):return ''
        try:
            if not ipaddress.ip_address(host).is_global:return ''
        except ValueError:pass
        return value
    except ValueError:return ''

def image_url(value):
    url=safe_url(value);host=(urlsplit(url).hostname or '').lower()
    allowed=('discordapp.com','discordapp.net','vinted.net','ebayimg.com','grailed.com','depop.com')
    return url if any(host==d or host.endswith('.'+d) for d in allowed) else ''

def txt(value,limit=2000):return value[:limit] if isinstance(value,str) else ''

def normalize(message,channel):
    if not isinstance(message,dict) or str(message.get('channel_id',''))!=channel:return None
    mid=str(message.get('id',''))
    if not ID.fullmatch(mid) or not message.get('webhook_id'):return None
    content=txt(message.get('content'));title='';details=[content] if content else [];urls=[];images=[];price=''
    embeds=message.get('embeds') or []
    if not isinstance(embeds,list):return None
    for embed in embeds[:10]:
        if not isinstance(embed,dict):continue
        title=title or txt(embed.get('title'),200);description=txt(embed.get('description'))
        if description:details.append(description)
        urls += [safe_url(embed.get('url'))]+[safe_url(u) for u in URL.findall(description)]
        for field in (embed.get('fields') or [])[:25]:
            if not isinstance(field,dict):continue
            name,value=txt(field.get('name'),100),txt(field.get('value'),500)
            details.append(name+': '+value);urls += [safe_url(u) for u in URL.findall(value)]
            if re.search(r'price|cost|ц[еі]на|вартість|cena',name,re.I):price=price or value[:80]
        for key in ('image','thumbnail'):
            media=embed.get(key) or {}
            if isinstance(media,dict):images.append(image_url(media.get('url')))
    for a in (message.get('attachments') or [])[:10]:
        if isinstance(a,dict) and str(a.get('content_type','')).startswith('image/'):images.append(image_url(a.get('url')))
    urls += [safe_url(u) for u in URL.findall(content)];body='\n'.join(details)[:4000]
    if not (title or body or any(images)):return None
    match=PRICE.search(body);price=price or (match.group(0).strip()[:80] if match else '')
    title=title or next((line.strip()[:200] for line in content.splitlines() if line.strip() and not line.strip().startswith('https://')),'')
    listing=next((u for u in urls if u and not re.search(r'\.(?:png|jpe?g|webp|gif)(?:$|\?)',u,re.I) and (urlsplit(u).hostname or '') not in ('discord.com','discordapp.com','cdn.discordapp.com','media.discordapp.net')),'')
    guild=str(message.get('guild_id',''))
    source=f'https://discord.com/channels/{guild}/{channel}/{mid}' if ID.fullmatch(guild) else ''
    return dict(message_id=mid,channel_id=channel,webhook_id=str(message['webhook_id']),title=title,description=body,price=price,image=next((u for u in images if u),''),url=listing,source=source,posted=txt(message.get('timestamp'),40))

class FeedError(Exception):
    def __init__(self,key,delay=60):self.key,self.delay=key,delay

class DiscordFeed:
    def __init__(self,app,db):
        self.app,self.db=app,db;self.lock=threading.Lock()
        self.token=app.config.setdefault('DISCORD_BOT_TOKEN',os.getenv('DISCORD_BOT_TOKEN','').strip())
        self.channel=app.config.setdefault('DISCORD_CHANNEL_ID',os.getenv('DISCORD_CHANNEL_ID','').strip())
        self.webhook=app.config.setdefault('DISCORD_WEBHOOK_ID',os.getenv('DISCORD_WEBHOOK_ID','').strip())
        with app.app_context():
            db().executescript("""
            CREATE TABLE IF NOT EXISTS discord_listings(channel_id TEXT NOT NULL,message_id TEXT NOT NULL,
            webhook_id TEXT DEFAULT '',title TEXT,description TEXT,price TEXT,image TEXT,url TEXT,source TEXT,posted TEXT,PRIMARY KEY(channel_id,message_id));
            CREATE TABLE IF NOT EXISTS discord_feed_state(channel_id TEXT PRIMARY KEY,cursor TEXT DEFAULT '',
            retry_at REAL DEFAULT 0,last_success REAL DEFAULT 0,error TEXT DEFAULT '',guild_id TEXT DEFAULT '');
            """);db().commit()
    @property
    def enabled(self):return bool(self.token and ID.fullmatch(self.channel))
    def state(self):
        row=self.db().execute('SELECT * FROM discord_feed_state WHERE channel_id=?',(self.channel,)).fetchone()
        return dict(row) if row else dict(cursor='',retry_at=0,last_success=0,error='',guild_id='')
    def api(self,path,params=None):
        return requests.get('https://discord.com/api/v10/'+path,params=params,headers={'Authorization':'Bot '+self.token,'User-Agent':'MopsParcel/1.0'},timeout=(3,8),allow_redirects=False)
    def data(self,response):
        if response.status_code==429:
            try:delay=float(response.json().get('retry_after',60))
            except (ValueError,TypeError,AttributeError):delay=60
            raise FeedError('feed.error_limit',max(60,min(delay,86400)))
        if response.status_code in (401,403,404):raise FeedError('feed.error_access')
        if response.status_code!=200:raise FeedError('feed.error_network')
        try:return response.json()
        except ValueError:raise FeedError('feed.error_network')
    def refresh(self):
        if not self.enabled or self.state()['retry_at']>time.time() or not self.lock.acquire(blocking=False):return
        try:
            c=self.db();state=self.state();cursor=state['cursor'];guild=state['guild_id']
            c.execute('INSERT INTO discord_feed_state(channel_id,retry_at) VALUES(?,?) ON CONFLICT(channel_id) DO UPDATE SET retry_at=excluded.retry_at',(self.channel,time.time()+60));c.commit()
            if not guild:
                meta=self.data(self.api('channels/'+self.channel))
                if not isinstance(meta,dict) or str(meta.get('id',''))!=self.channel or not ID.fullmatch(str(meta.get('guild_id',''))):raise FeedError('feed.error_access')
                guild=str(meta['guild_id'])
            params={'limit':100}
            if cursor:params['after']=cursor
            batch=self.data(self.api('channels/'+self.channel+'/messages',params))
            if not isinstance(batch,list):raise FeedError('feed.error_network')
            recent=[]
            if cursor and len(batch)<100:
                recent=self.data(self.api('channels/'+self.channel+'/messages',{'limit':100}))
                if not isinstance(recent,list):raise FeedError('feed.error_network')
            messages={str(m.get('id')):m for m in recent+batch if isinstance(m,dict) and ID.fullmatch(str(m.get('id',''))) and str(m.get('channel_id',''))==self.channel}
            empty=False;count=0
            for mid,m in messages.items():
                if self.webhook and str(m.get('webhook_id',''))!=self.webhook:continue
                m=dict(m,guild_id=guild);card=normalize(m,self.channel)
                if not card:
                    if not m.get('content') and not m.get('embeds') and not m.get('attachments'):empty=True
                    continue
                count+=1
                c.execute("""INSERT INTO discord_listings(channel_id,message_id,webhook_id,title,description,price,image,url,source,posted)
                  VALUES(:channel_id,:message_id,:webhook_id,:title,:description,:price,:image,:url,:source,:posted)
                  ON CONFLICT(channel_id,message_id) DO UPDATE SET webhook_id=excluded.webhook_id,title=excluded.title,description=excluded.description,
                  price=excluded.price,image=excluded.image,url=excluded.url,source=excluded.source,posted=excluded.posted""",card)
            ids=[int(m['id']) for m in batch if isinstance(m,dict) and ID.fullmatch(str(m.get('id',''))) and str(m.get('channel_id',''))==self.channel]
            if ids:cursor=str(max([int(cursor or 0),*ids]))
            error='feed.error_content' if empty and not count else ''
            c.execute('UPDATE discord_feed_state SET cursor=?,last_success=?,error=?,guild_id=? WHERE channel_id=?',(cursor,time.time(),error,guild,self.channel));c.commit()
        except FeedError as exc:self.db().rollback();self.failure(exc.key,exc.delay)
        except (requests.RequestException,ValueError,TypeError):self.db().rollback();self.failure('feed.error_network',60)
        finally:self.lock.release()
    def failure(self,key,delay):
        self.db().execute('UPDATE discord_feed_state SET retry_at=?,error=? WHERE channel_id=?',(time.time()+delay,key,self.channel));self.db().commit()
    def page_data(self):
        self.refresh()
        try:page=max(1,min(int(request.args.get('page',1)),100000))
        except ValueError:page=1
        q=request.args.get('q','').strip()[:100];like='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        rows=self.db().execute("SELECT * FROM discord_listings WHERE channel_id=? AND (?='' OR webhook_id=?) AND (title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\') ORDER BY length(message_id) DESC,message_id DESC LIMIT 25 OFFSET ?",(self.channel if self.enabled else '',self.webhook,self.webhook,like,like,(page-1)*24)).fetchall()
        state=self.state();status='feed.unconfigured' if not self.enabled else 'feed.unavailable' if state['error'] else ''
        return dict(cards=[dict(row) for row in rows[:24]],page=page,q=q,has_more=len(rows)>24,status=t(status) if status else '',
            admin_error=t(state['error']) if state['error'] and g.user['role']=='admin' else '',enabled=self.enabled,last_success=state['last_success'])

def install_discord(app,db,login_required):
    feed=DiscordFeed(app,db);app.extensions['discord_feed']=feed
    @app.get('/parser')
    @login_required
    def parser_feed():
        response=app.make_response(render_template('parser.html',**feed.page_data()))
        response.headers['Cache-Control']='private, no-store';return response
    @app.get('/parser/data')
    @login_required
    def parser_data():
        response=jsonify(feed.page_data());response.headers['Cache-Control']='private, no-store';return response
