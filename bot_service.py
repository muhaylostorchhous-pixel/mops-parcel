"""Telegram delivery. Only numeric, verified private chat IDs receive client files."""
from pathlib import Path
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
                return True
        path = Path(self.app.config['UPLOAD_FOLDER'])/name
        if not path.is_file():
            return False
        with path.open('rb') as stream:
            result = self.call('sendDocument',payload,files={'document':(name,stream)})
        if result is None:
            return False
        file_id = result.get('document',{}).get('file_id')
        if file_id:
            self.db().execute('INSERT INTO telegram_files(name,bot_id,file_id) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET bot_id=excluded.bot_id,file_id=excluded.file_id',(name,bot_id,file_id))
            self.db().commit()
        return True
