"""Stable product codes, additive schema migration and shipment identifiers."""
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

PRODUCTS = {
    'shoes_no_box': ('product.shoes_no_box', 650),
    'shoes_box': ('product.shoes_box', 700),
    'outerwear': ('product.outerwear', 500),
    'small': ('product.small', 300),
}
DELIVERIES = {'Домашняя доставка':'home_delivery', 'InPost locker':'inpost',
              'Evri пункт выдачи':'evri', 'Royal Mail отделение':'royal_mail', 'Другой':'other_delivery'}

def rank_key(completed):
    return ('rank.new','rank.regular','rank.lower','rank.middle','rank.cool','rank.boss')[min(max(int(completed),0)//10,5)]

def generate_code(db):
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    for _ in range(100):
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        if not db.execute('SELECT 1 FROM orders WHERE parcel_code=?',(code,)).fetchone():
            return code
    raise RuntimeError('Unable to allocate shipment identifier')

def migrate(db, database):
    user_columns = {row[1] for row in db.execute('PRAGMA table_info(users)')}
    if getattr(db,'dialect','sqlite')=='sqlite' and 'onboarding_completed' not in user_columns and db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
        folder = Path(database).parent/'backups'
        folder.mkdir(parents=True, exist_ok=True)
        backup = folder/(Path(database).stem+'-before-v2-'+datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')+'.sqlite3')
        with sqlite3.connect(backup) as dest:
            db.backup(dest)
    additions = {
        'users': {'phone':"TEXT DEFAULT ''", 'language':"TEXT DEFAULT 'ru'", 'onboarding_completed':'INTEGER DEFAULT 1', 'leaderboard_public':'INTEGER DEFAULT 0'},
        'orders': {'submission_key':"TEXT DEFAULT ''", 'product_type':"TEXT DEFAULT ''", 'ua_name':"TEXT DEFAULT ''", 'ua_phone':"TEXT DEFAULT ''", 'ua_city':"TEXT DEFAULT ''", 'ua_branch':"TEXT DEFAULT ''", 'uk_address':"TEXT DEFAULT ''", 'parcel_code':"TEXT DEFAULT ''", 'payment_status':"TEXT DEFAULT 'unpaid'", 'delivered_at':"TEXT DEFAULT ''"},
    }
    db.execute('BEGIN IMMEDIATE')
    try:
        for table, columns in additions.items():
            existing = {row[1] for row in db.execute('PRAGMA table_info('+table+')')}
            for column, definition in columns.items():
                if column not in existing:
                    db.execute('ALTER TABLE '+table+' ADD COLUMN '+column+' '+definition)
        statements = [
            "CREATE UNIQUE INDEX IF NOT EXISTS order_submission_unique ON orders(user_id,submission_key) WHERE submission_key<>''",
            "CREATE INDEX IF NOT EXISTS orders_owner_archive ON orders(user_id,archived,id)",
            "CREATE TABLE IF NOT EXISTS addresses(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),name TEXT NOT NULL,phone TEXT NOT NULL,city TEXT NOT NULL,branch TEXT NOT NULL,created TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS order_payments(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),user_id INTEGER NOT NULL REFERENCES users(id),amount TEXT NOT NULL,screenshot TEXT NOT NULL,receipt TEXT NOT NULL,state TEXT DEFAULT 'pending',reason TEXT DEFAULT '',created TEXT NOT NULL,reviewed TEXT DEFAULT '')",
            "CREATE UNIQUE INDEX IF NOT EXISTS payment_one_pending ON order_payments(order_id) WHERE state='pending'",
            "CREATE UNIQUE INDEX IF NOT EXISTS parcel_code_unique ON orders(parcel_code) WHERE parcel_code<>''",
            "CREATE TABLE IF NOT EXISTS bot_preferences(chat_id TEXT PRIMARY KEY,language TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS bot_updates(update_id INTEGER PRIMARY KEY,created TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS telegram_files(name TEXT PRIMARY KEY,bot_id TEXT NOT NULL,file_id TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS order_audit(id INTEGER PRIMARY KEY,order_id INTEGER,user_id INTEGER,action TEXT,created TEXT)",
            "CREATE INDEX IF NOT EXISTS order_audit_history ON order_audit(order_id,id)",
        ]
        for sql in statements:
            db.execute(sql)
        db.execute("UPDATE orders SET delivered_at=updated WHERE status='Доставлено' AND delivered_at=''")
        for row in db.execute("SELECT id FROM users WHERE telegram_token='' OR telegram_token IS NULL").fetchall():
            db.execute('UPDATE users SET telegram_token=? WHERE id=?',(secrets.token_urlsafe(24),row[0]))
        for row in db.execute("SELECT id FROM orders WHERE parcel_code='' AND status IN ('Одержано','Фотоотчёт готов','К отправке','Отправлено','Доставлено')").fetchall():
            db.execute('UPDATE orders SET parcel_code=? WHERE id=?',(generate_code(db),row[0]))
        db.commit()
    except Exception:
        db.rollback()
        raise
