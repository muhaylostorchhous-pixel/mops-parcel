"""Archive reports with Telegram receipts before removing database payloads.

No outbound calls run in migrations. Deletion requires both recipients, a current
bot, a private archive channel, a successful getFile, and a completed delivery.
"""
import os, re, secrets, time
from flask import flash, g, redirect, render_template, request, url_for
from i18n import CATALOG, t
from archive_i18n import STRINGS
CATALOG.update(STRINGS)
CATALOG.update({v['ru']:v for v in STRINGS.values()})

SCHEMA='''
CREATE TABLE IF NOT EXISTS telegram_deliveries(name TEXT NOT NULL,bot_id TEXT NOT NULL,chat_id TEXT NOT NULL,file_id TEXT NOT NULL,message_id INTEGER NOT NULL,created TEXT NOT NULL,PRIMARY KEY(name,bot_id,chat_id));
CREATE TABLE IF NOT EXISTS report_archives(name TEXT PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),state TEXT NOT NULL DEFAULT 'pending',bot_id TEXT NOT NULL DEFAULT '',archive_chat_id TEXT NOT NULL DEFAULT '',archive_file_id TEXT NOT NULL DEFAULT '',archive_message_id INTEGER NOT NULL DEFAULT 0,client_chat_id TEXT NOT NULL DEFAULT '',client_message_id INTEGER NOT NULL DEFAULT 0,lease_token TEXT NOT NULL DEFAULT '',lease_until REAL NOT NULL DEFAULT 0,next_try REAL NOT NULL DEFAULT 0,attempts INTEGER NOT NULL DEFAULT 0,last_error TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,confirmed_at TEXT NOT NULL DEFAULT '',cleaned_at TEXT NOT NULL DEFAULT '',removed_bytes INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS report_archive_queue ON report_archives(state,next_try);
'''


def install_archive(app, db, stamp, admin_required):
    archive=ReportArchive(app,db,stamp)
    app.extensions['report_archive']=archive
    with app.app_context():
        c=db()
        # Include existing reports, without purging or contacting Telegram at startup.
        c.execute("INSERT INTO report_archives(name,order_id,created) SELECT report,MIN(id),MIN(created) FROM orders WHERE report<>'' GROUP BY report ON CONFLICT(name) DO NOTHING")
        c.commit()

    @app.get('/admin/report-archive')
    @admin_required
    def report_archive():
        page=max(1,min(request.args.get('page',1,type=int) or 1,100000))
        rows=db().execute('SELECT a.*,o.item,o.parcel_code FROM report_archives a JOIN orders o ON o.id=a.order_id ORDER BY a.created DESC,a.name LIMIT 51 OFFSET ?',((page-1)*50,)).fetchall()
        total=db().execute('SELECT COALESCE(SUM(removed_bytes),0) FROM report_archives').fetchone()[0]
        return render_template('report_archive.html',archive_rows=rows[:50],has_more=len(rows)>50,page=page,archive_enabled=archive.enabled,archive_bot_id=archive.bot_id,archive_channel=archive.channel,removed_mb=round(total/1048576,2))

    @app.post('/admin/report-archive/retry')
    @admin_required
    def retry_report_archive():
        db().execute("UPDATE report_archives SET next_try=0,attempts=0,state=CASE WHEN confirmed_at<>'' THEN 'confirmed' ELSE 'pending' END WHERE state IN ('pending','failed','confirmed')")
        db().commit();app.extensions['services'].wake()
        flash(t('arc.queued'),'success')
        return redirect(url_for('report_archive'))

    @app.context_processor
    def report_archive_context():
        def cleaned(name):
            return bool(name and db().execute("SELECT 1 FROM report_archives WHERE name=? AND cleaned_at<>''",(name,)).fetchone())
        return {'report_cleaned':cleaned}


class ReportArchive:
    def __init__(self,app,db,stamp):
        self.app,self.db,self.stamp=app,db,stamp
        app.config.setdefault('TELEGRAM_ARCHIVE_CHAT_ID',os.getenv('TELEGRAM_ARCHIVE_CHAT_ID','').strip())

    @property
    def channel(self):return str(self.app.config.get('TELEGRAM_ARCHIVE_CHAT_ID','')).strip()
    @property
    def bot_id(self):return self.app.config.get('TELEGRAM_BOT_TOKEN','').split(':',1)[0]
    @property
    def enabled(self):return bool(self.bot_id and re.fullmatch(r'-100\d{5,}',self.channel))
    @property
    def telegram(self):return self.app.extensions['mops_features'].telegram

    def register(self,oid,name):
        if name:
            self.db().execute('INSERT OR IGNORE INTO report_archives(name,order_id,created) VALUES(?,?,?)',(name,oid,self.stamp()))

    def touch(self,oid):
        self.db().execute("UPDATE report_archives SET next_try=0 WHERE order_id=? AND state IN ('pending','confirmed')",(oid,))

    def receipt(self,name,chat):
        return self.db().execute('SELECT * FROM telegram_deliveries WHERE name=? AND bot_id=? AND chat_id=?',(name,self.bot_id,str(chat))).fetchone()

    def finish(self,name,lease,error='',state='pending'):
        c=self.db()
        c.execute("UPDATE report_archives SET state=?,last_error=?,next_try=?,lease_until=0,lease_token='',attempts=attempts+? WHERE name=? AND lease_token=?",(state,error,time.time()+3600,int(bool(error)),name,lease))
        c.commit()

    def process(self,name):
        if not self.enabled:return
        c=self.db();now=time.time();lease=secrets.token_hex(16)
        claimed=c.execute("UPDATE report_archives SET state='sending',lease_token=?,lease_until=? WHERE name=? AND cleaned_at='' AND next_try<=? AND state<>'failed' AND (state<>'sending' OR lease_until<?)",(lease,now+300,name,now,now)).rowcount;c.commit()
        if not claimed:return
        try:
            a=c.execute('SELECT * FROM report_archives WHERE name=?',(name,)).fetchone()
            o=c.execute('SELECT o.*,u.telegram_chat_id,u.language FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=?',(a['order_id'],)).fetchone();c.commit()
            if not o:self.finish(name,lease,'shared_file','failed');return
            channel=self.channel;bot=self.bot_id
            chat=self.telegram.call('getChat',{'chat_id':channel})
            if not isinstance(chat,dict):self.finish(name,lease,'telegram_failed');return
            if str(chat.get('id'))!=channel or chat.get('type')!='channel' or chat.get('username') or chat.get('active_usernames') or chat.get('message_auto_delete_time',0):
                self.finish(name,lease,'channel_invalid');return
            receipt=self.receipt(name,channel);c.commit()
            if not receipt:
                self.telegram.document(channel,name,t('arc.caption','ru',id=o['id'],item=o['item'],code=o['parcel_code'] or '—'))
                receipt=self.receipt(name,channel);c.commit()
            if not receipt:self.finish(name,lease,'telegram_failed');return
            # Persist the archive receipt even when the client has not linked the bot yet.
            c.execute('UPDATE report_archives SET bot_id=?,archive_chat_id=?,archive_file_id=?,archive_message_id=? WHERE name=? AND lease_token=?',(bot,channel,receipt['file_id'],receipt['message_id'],name,lease));c.commit()
            client=o['telegram_chat_id']
            if not client:self.finish(name,lease,'link_telegram');return
            customer=self.receipt(name,client);c.commit()
            if not customer:
                self.telegram.document(client,name,t('bot.report_file',o['language'],id=o['id'],item=o['item']))
                customer=self.receipt(name,client);c.commit()
            if not customer:self.finish(name,lease,'client_failed');return
            c.execute('UPDATE report_archives SET client_chat_id=?,client_message_id=?,confirmed_at=? WHERE name=? AND lease_token=?',(str(client),customer['message_id'],self.stamp(),name,lease));c.commit()
            if o['status'] not in ('Доставлено','Архив') or not o['delivered_at'] or not o['archived']:
                self.finish(name,lease,state='confirmed');return
            # Confirm that this bot can still retrieve the file before deleting any bytes.
            probe=self.telegram.call('getFile',{'file_id':receipt['file_id']})
            if not isinstance(probe,dict) or not probe.get('file_path') or not probe.get('file_id'):
                self.finish(name,lease,'file_unavailable');return
            c.execute('BEGIN IMMEDIATE')
            fresh=c.execute('SELECT o.*,u.telegram_chat_id FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=?',(o['id'],)).fetchone()
            job=c.execute('SELECT * FROM report_archives WHERE name=?',(name,)).fetchone()
            if not job or job['lease_token']!=lease:c.rollback();return
            if self.bot_id!=bot or self.channel!=channel or str(fresh['telegram_chat_id'])!=str(client):
                c.rollback();self.finish(name,lease,'bot_changed');return
            if fresh['status'] not in ('Доставлено','Архив') or not fresh['delivered_at'] or not fresh['archived']:
                c.rollback();self.finish(name,lease,state='confirmed');return
            shared=c.execute('SELECT 1 FROM orders WHERE proof=? OR item_photo=? OR (report=? AND id<>?) UNION SELECT 1 FROM reviews WHERE image=? UNION SELECT 1 FROM order_payments WHERE screenshot=? OR receipt=?',(name,name,name,o['id'],name,name,name)).fetchone()
            if shared:c.rollback();self.finish(name,lease,'shared_file','failed');return
            size=c.execute('SELECT LENGTH(data) FROM file_objects WHERE name=?',(name,)).fetchone()
            c.execute('DELETE FROM file_objects WHERE name=?',(name,))
            c.execute("UPDATE report_archives SET state='cleaned',cleaned_at=?,removed_bytes=?,last_error='',lease_token='',lease_until=0 WHERE name=? AND lease_token=?",(self.stamp(),size[0] if size else 0,name,lease))
            c.execute('INSERT INTO audit_events(user_id,action,target,result,created) VALUES(?,?,?,?,?)',(None,'report_archived',str(o['id']),200,self.stamp()))
            c.commit()
        except Exception:
            c.rollback()
            self.app.logger.warning('Report archiving deferred; database copy retained unless cleanup already committed')
            self.finish(name,lease,'telegram_failed')

    def drain(self,limit=10):
        if not self.enabled:return
        c=self.db();now=time.time()
        rows=c.execute("SELECT a.name FROM report_archives a JOIN orders o ON o.id=a.order_id WHERE a.cleaned_at='' AND a.state<>'failed' AND a.next_try<=? AND (a.state<>'sending' OR a.lease_until<?) AND (a.state<>'confirmed' OR (o.archived=1 AND o.delivered_at<>'' AND o.status IN ('Доставлено','Архив')) OR a.bot_id<>? OR a.archive_chat_id<>?) ORDER BY a.next_try,a.created LIMIT ?",(now,now,self.bot_id,self.channel,limit)).fetchall();c.commit()
        for row in rows:self.process(row['name'])
