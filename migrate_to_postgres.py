"""One-time safe import into an EMPTY PostgreSQL database. Source remains unchanged."""
import argparse,os,sqlite3,re
from pathlib import Path
from dotenv import load_dotenv

def transfer(source,target):
    tables=[r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    order=['users','orders','settings','changes','payment_requests','reviews','addresses','order_payments','order_audit','bot_preferences','bot_updates','telegram_files','discord_listings','discord_feed_state','file_objects','email_challenges','rate_limits','audit_events','support_messages','notification_outbox','telegram_deliveries','report_archives']
    tables=[t for t in order if t in tables]
    for table in order:
        if table!='settings' and target.execute('SELECT 1 FROM '+table+' LIMIT 1').fetchone():
            raise RuntimeError('Target database is not empty; import cancelled without changes.')
    count=0
    try:
        for table in tables:
            available={r[1] for r in target.execute('PRAGMA table_info('+table+')')}
            cols=[r[1] for r in source.execute('PRAGMA table_info('+table+')') if r[1] in available]
            sql='INSERT INTO '+table+'('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')'
            if table=='settings':sql+=' ON CONFLICT(key) DO UPDATE SET value=excluded.value'
            for row in source.execute('SELECT '+','.join(cols)+' FROM '+table):target.execute(sql,tuple(row));count+=1
            if table=='users' and 'email_verified' not in cols:target.execute('UPDATE users SET email_verified=2')
            if 'id' in cols:
                # Reset sequences after preserving original primary keys.
                target.raw.execute("SELECT setval(pg_get_serial_sequence(%s,'id'),COALESCE((SELECT MAX(id) FROM "+table+"),1),(SELECT COUNT(*)>0 FROM "+table+"))",(table,))
        target.commit()
    except Exception:target.rollback();raise
    return count

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite',required=True);parser.add_argument('--uploads')
    args=parser.parse_args();load_dotenv()
    path=Path(args.sqlite).resolve()
    if not path.is_file():raise SystemExit('Source SQLite file not found')
    if not os.getenv('DATABASE_URL','').startswith(('postgres://','postgresql://')):raise SystemExit('Set DATABASE_URL in .env first')
    # Prevent automatic seeding: import must preserve the original admin and identifiers.
    os.environ['ADMIN_EMAIL']='';os.environ['NOTIFICATION_WORKER']='false'
    os.environ['UPLOAD_FOLDER']=str(Path('instance/import-empty').resolve())
    from app import create_app
    app=create_app({'NOTIFICATION_WORKER':False,'UPLOAD_FOLDER':str(Path('instance/import-empty').resolve())})
    source=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    with app.app_context():
        service=app.extensions['services'];c=service.db();count=transfer(source,c)
        if args.uploads:
            folder=Path(args.uploads).resolve()
            for f in folder.iterdir():
                if f.is_file() and f.suffix.lower() in ('.jpg','.jpeg','.png','.webp','.pdf') and f.stat().st_size<=12*1024*1024:
                    if c.execute("SELECT 1 FROM report_archives WHERE name=? AND cleaned_at<>''",(f.name,)).fetchone():continue
                    c.execute('INSERT OR IGNORE INTO file_objects(name,data,created) VALUES(?,?,?)',(f.name,f.read_bytes(),service.stamp()))
            c.commit()
    source.close();print('Import complete. Rows:',count,'Source files were not modified.')
if __name__=='__main__':main()
