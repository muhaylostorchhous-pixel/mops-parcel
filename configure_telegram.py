"""Run once after deployment. Tokens are read from env, never printed."""
import os
import re
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

COMMANDS={
 'ru':[('parser','Лента объявлений'),('start','Профиль и мини-приложение'),('orders','Мои посылки'),('leaders','Таблица лидеров'),('language','Сменить язык'),('help','Помощь')],
 'uk':[('parser','Стрічка оголошень'),('start','Профіль та мінізастосунок'),('orders','Мої посилки'),('leaders','Таблиця лідерів'),('language','Змінити мову'),('help','Допомога')],
 'en':[('parser','Listing feed'),('start','Profile and mini app'),('orders','My parcels'),('leaders','Leaderboard'),('language','Change language'),('help','Help')],
}

def configure():
 load_dotenv()
 token=os.getenv('TELEGRAM_BOT_TOKEN','')
 secret=os.getenv('TELEGRAM_WEBHOOK_SECRET','')
 url=(os.getenv('TELEGRAM_WEBAPP_URL') or os.getenv('RENDER_EXTERNAL_URL','')).rstrip('/')
 if not token or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',secret) or urlparse(url).scheme!='https' or not urlparse(url).hostname:
  raise SystemExit('Заполните TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET и TELEGRAM_WEBAPP_URL (HTTPS). На Render URL определяется автоматически.')
 def call(method,payload):
  try:
   response=requests.post('https://api.telegram.org/bot'+token+'/'+method,json=payload,timeout=(5,20))
   response.raise_for_status();result=response.json()
   if not result.get('ok'):raise ValueError('API error')
   return result.get('result')
  except (requests.RequestException,ValueError):raise SystemExit('Telegram не подтвердил '+method+'. Проверьте ENV и доступность сети. Токен не выведен в журнал.') from None
 call('setWebhook',{'url':url+'/telegram/webhook','secret_token':secret,'allowed_updates':['message','callback_query'],'drop_pending_updates':False})
 for lang,commands in [('',COMMANDS['en']),*COMMANDS.items()]:
  call('setMyCommands',{'language_code':lang,'commands':[{'command':command,'description':description} for command,description in commands]})
 call('setChatMenuButton',{'menu_button':{'type':'web_app','text':'Mops Parcel','web_app':{'url':url}}})
 print('Готово: webhook, команды RU/UK/EN и кнопка мини-приложения подключены.')

if __name__=='__main__':configure()
