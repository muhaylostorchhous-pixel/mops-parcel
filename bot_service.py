"""Telegram delivery. Only numeric, verified private chat IDs receive client files."""
from pathlib import Path
import io
from datetime import datetime, timezone
import requests

class Telegram:
    def __init__(self, app, db):
        self.app, self.db = app, db

    def call(self, method, payload, files=None):
        token = self.app.config.get('TELEGRAM_BOT_TOKEN')
        if not token:
            return None
        try:
            kwargs = {'data':payload,'files':files} if files else {'json':payload}
            response = requests.post('https://api.telegram.org/bot'+token+'/'+method, timeout=(5,15), **kwargs)
            response.raise_for_status()
            result = response.json()
            if result.get('ok'):
                return result.get('result', {})
        except (requests.RequestException, ValueError):
            # Do not put a bot token or an HTTP URL containing it in logs.
            self.app.logger.warning('Telegram operation failed: %s', method)
        return None

    def message(self, chat, text, keyboard=None):
        if not chat:
            return None
        service=self.app.extensions.get('services')
        if service: return service.queue_chat(chat,text,keyboard)
        payload = {'chat_id':str(chat), 'text':text[:4096]}
        if keyboard:
            payload['reply_markup'] = {'inline_keyboard':keyboard}
        return self.call('sendMessage',payload)

    def document(self, chat, name, caption):
        if not chat or not name or Path(name).name != name:
            return False
        token = self.app.config.get('TELEGRAM_BOT_TOKEN','')
        bot_id = token.split(':',1)[0]
        saved = self.db().execute('SELECT file_id FROM telegram_files WHERE name=? AND bot_id=?',(name,bot_id)).fetchone()
        payload = {'chat_id':str(chat), 'caption':caption[:1024]}
        if saved:
            result = self.call('sendDocument',dict(payload, document=saved['file_id']))
            if result is not None:
                self.record_delivery(chat,name,bot_id,result)
                return True
        service=self.app.extensions.get('services')
        path = Path(self.app.config['UPLOAD_FOLDER'])/name
        data=service.file_bytes(name) if service else path.read_bytes() if path.is_file() else None
        if data is None: return False
        with io.BytesIO(data) as stream:
            result = self.call('sendDocument',payload,files={'document':(name,stream)})
        if result is None:
            return False
        file_id = result.get('document',{}).get('file_id')
        if file_id:
            self.db().execute('INSERT INTO telegram_files(name,bot_id,file_id) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET bot_id=excluded.bot_id,file_id=excluded.file_id',(name,bot_id,file_id))
            self.db().commit()
        self.record_delivery(chat,name,bot_id,result)
        return True

    def record_delivery(self,chat,name,bot_id,result):
        """Only a complete Telegram Message is proof of delivery for cleanup."""
        if not isinstance(result,dict):return
        document=result.get('document') or {};message_id=result.get('message_id')
        file_id=document.get('file_id')
        if (not isinstance(message_id,int) or isinstance(message_id,bool) or message_id<=0
                or not isinstance(file_id,str) or not file_id or str((result.get('chat') or {}).get('id'))!=str(chat)):
            return
        c=self.db()
        c.execute('INSERT INTO telegram_deliveries(name,bot_id,chat_id,file_id,message_id,created) VALUES(?,?,?,?,?,?) ON CONFLICT(name,bot_id,chat_id) DO UPDATE SET file_id=excluded.file_id,message_id=excluded.message_id,created=excluded.created',(name,bot_id,str(chat),file_id,message_id,datetime.now(timezone.utc).isoformat(timespec='seconds')))
        # Reused file IDs can change; retain the latest valid ID for this bot.
        c.execute('INSERT INTO telegram_files(name,bot_id,file_id) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET bot_id=excluded.bot_id,file_id=excluded.file_id',(name,bot_id,file_id))
        c.commit()
