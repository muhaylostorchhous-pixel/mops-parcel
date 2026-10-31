"""Create a portable SQLite backup of persistent data, including uploaded files."""
import argparse,os,sqlite3
from pathlib import Path
from dotenv import load_dotenv

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args()
    out=Path(args.output).resolve()
    if out.exists():raise SystemExit('Output already exists; choose a new backup filename.')
    load_dotenv();os.environ['NOTIFICATION_WORKER']='false'
    from app import create_app
    app=create_app({'NOTIFICATION_WORKER':False})
    try:
        with app.app_context():
            c=app.extensions['services'].db()
            if not app.config.get('DATABASE_URL'):
                with sqlite3.connect(out) as target:c.backup(target)
            else:
                from psycopg import sql
                c.raw.rollback();c.raw.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
                tables=c.raw.execute("SELECT tablename FROM pg_tables WHERE schemaname=current_schema() ORDER BY tablename").fetchall()
                with sqlite3.connect(out) as target:
                    for (table,) in tables:
                        cols=c.raw.execute('SELECT column_name,data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s ORDER BY ordinal_position',(table,)).fetchall()
                        def q(s):return '"'+s.replace('"','""')+'"'
                        types={'bigint':'INTEGER','integer':'INTEGER','double precision':'REAL','bytea':'BLOB'}
                        target.execute('CREATE TABLE '+q(table)+'('+','.join(q(n)+' '+types.get(kind,'TEXT') for n,kind in cols)+')')
                        with c.raw.cursor(name='backup_'+table) as cursor:
                            cursor.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table)))
                            for row in cursor:target.execute('INSERT INTO '+q(table)+' VALUES('+','.join('?' for _ in cols)+')',tuple(bytes(v) if isinstance(v,memoryview) else v for v in row))
                c.rollback()
        print('Backup saved:',out)
    except Exception:
        print('Backup failed. Do not use an incomplete output file.');raise
if __name__=='__main__':main()
