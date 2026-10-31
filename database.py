"""Small DB-API compatibility layer for the existing parameterized SQLite queries."""
import re
import sqlite3

class Row:
    def __init__(self, names, values): self.names,self.values=names,values
    def __getitem__(self, key): return self.values[key] if isinstance(key,int) else self.values[self.names.index(key)]
    def __iter__(self): return iter(self.values)
    def keys(self): return self.names

class Result:
    def __init__(self, cursor=None, rows=None, lastrowid=None):
        self.cursor,self.rows,self.lastrowid=cursor,rows,lastrowid
        self.rowcount=cursor.rowcount if cursor else len(rows or [])
    def fetchall(self):
        if self.rows is not None: rows,self.rows=self.rows,[];return rows
        names=[d.name for d in self.cursor.description]
        return [Row(names,r) for r in self.cursor.fetchall()]
    def fetchone(self):
        if self.rows is not None: return self.rows.pop(0) if self.rows else None
        r=self.cursor.fetchone()
        return Row([d.name for d in self.cursor.description],r) if r is not None else None
    def __iter__(self): return iter(self.fetchall())

class Postgres:
    dialect='postgres'
    def __init__(self,url):
        import psycopg
        self.driver=psycopg
        self.raw=psycopg.connect(url,connect_timeout=10)
    def execute(self,sql,params=()):
        pragma=re.fullmatch(r'PRAGMA table_info\((\w+)\)',sql.strip(),re.I)
        if pragma:
            cur=self.raw.execute('SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s ORDER BY ordinal_position',(pragma[1],))
            return Result(rows=[Row(['cid','name'],(i,r[0])) for i,r in enumerate(cur.fetchall())])
        if sql.strip().upper()=='BEGIN IMMEDIATE':
            # Call sites enter this before writes. Serialize legacy read-modify-write operations.
            self.raw.commit()
            return Result(self.raw.execute('SELECT pg_advisory_xact_lock(70271027)'))
        sql=re.sub(r'\bid INTEGER PRIMARY KEY\b','id BIGSERIAL PRIMARY KEY',sql,flags=re.I)
        sql=re.sub(r'\bBLOB\b','BYTEA',sql,flags=re.I)
        sql=re.sub(r'\bREAL\b','DOUBLE PRECISION',sql,flags=re.I)
        ignore=bool(re.search(r'INSERT OR IGNORE',sql,re.I))
        sql=re.sub(r'INSERT OR IGNORE','INSERT',sql,flags=re.I)
        if ignore: sql=sql.rstrip().rstrip(';')+' ON CONFLICT DO NOTHING'
        # Only replace placeholders outside SQL string literals.
        parts=re.split(r"('(?:''|[^'])*')",sql)
        for i in range(0,len(parts),2):
            parts[i]=re.sub(r'(?<!:):([a-zA-Z_]\w*)',r'%(\1)s',parts[i]) if isinstance(params,dict) else parts[i].replace('?','%s')
        sql=''.join(parts)
        insert=re.match(r'\s*INSERT INTO (\w+)',sql,re.I)
        with_id={'users','orders','changes','payment_requests','reviews','addresses','order_payments','order_audit','audit_events','support_messages','notification_outbox'}
        returning=bool(insert and insert[1] in with_id and 'RETURNING' not in sql.upper())
        if returning: sql=sql.rstrip().rstrip(';')+' RETURNING id'
        try:
            # A savepoint preserves SQLite's recoverable integrity-error behavior.
            if self.raw.info.transaction_status == self.driver.pq.TransactionStatus.IDLE:
                self.raw.execute("BEGIN")
            with self.raw.transaction():
                cur=self.raw.execute(sql,params or None)
                row=cur.fetchone() if returning else None
                return Result(cur,lastrowid=row[0] if row else None)
        except self.driver.IntegrityError as exc:
            raise sqlite3.IntegrityError('Database constraint violation') from None
    def executescript(self,script):
        for statement in script.split(';'):
            if statement.strip(): self.execute(statement)
        self.commit()
    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def close(self): self.raw.close()

def connect(config):
    url=config.get('DATABASE_URL','')
    if url:
        if not url.startswith(('postgres://','postgresql://')): raise RuntimeError('DATABASE_URL must be a PostgreSQL connection URL')
        return Postgres(url)
    c=sqlite3.connect(config['DATABASE'],timeout=20)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA journal_mode=WAL')
    return c
