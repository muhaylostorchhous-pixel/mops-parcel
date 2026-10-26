from __future__ import annotations
import os, re, sqlite3, secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from functools import wraps
import requests
from flask import Flask, abort, flash, g, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from i18n import CATALOG, t
from werkzeug.exceptions import HTTPException

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/".env")
STATUSES=("В процессе","Отклонено","Одержано","Фотоотчёт готов","К отправке","Отправлено","Доставлено","Архив")
def create_app(config=None):
 app=Flask(__name__)
 app.config.update(SECRET_KEY=os.getenv("SECRET_KEY","replace-this"), DATABASE=os.getenv("DATABASE_PATH",str(ROOT/"instance/mops.sqlite3")), UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER",str(ROOT/"uploads")), MAX_CONTENT_LENGTH=12*1024*1024, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.getenv("RENDER","").lower()=="true", TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN",""), TELEGRAM_ADMIN_CHAT_ID=os.getenv("TELEGRAM_ADMIN_CHAT_ID",""), PAYMENT_CARD=os.getenv("PAYMENT_CARD",""))
 if config: app.config.update(config)
 Path(app.config["DATABASE"]).parent.mkdir(parents=True,exist_ok=True); Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True,exist_ok=True)
 if app.config["SECRET_KEY"] in ("", "replace-this", "replace-with-long-random-secret"):
  secret_file=Path(app.config["DATABASE"]).parent/"session.secret"
  try:
   descriptor=os.open(secret_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   with os.fdopen(descriptor,"w") as stream: stream.write(secrets.token_urlsafe(48))
  except FileExistsError: pass
  app.config["SECRET_KEY"]=secret_file.read_text().strip()

 def db():
  if "db" not in g: g.db=sqlite3.connect(app.config["DATABASE"]); g.db.row_factory=sqlite3.Row; g.db.execute("PRAGMA foreign_keys=ON")
  return g.db
 def stamp(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
 @app.teardown_appcontext
 def close(_e=None):
  c=g.pop("db",None)
  if c: c.close()
 def initialize():
  c=db(); c.executescript("""
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT DEFAULT 'client',approved INTEGER DEFAULT 0,telegram TEXT DEFAULT '',telegram_token TEXT DEFAULT '',telegram_chat_id TEXT DEFAULT '',bonus_balance INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),item TEXT NOT NULL,phone TEXT NOT NULL,delivery TEXT NOT NULL,branch TEXT DEFAULT '',telegram TEXT NOT NULL,proof TEXT NOT NULL,item_photo TEXT NOT NULL,status TEXT DEFAULT 'В процессе',fee TEXT DEFAULT '',tracking TEXT DEFAULT '',report TEXT DEFAULT '',deadline TEXT DEFAULT '',photo_decision TEXT DEFAULT '',created TEXT NOT NULL,updated TEXT NOT NULL,archived INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT DEFAULT '');
  CREATE TABLE IF NOT EXISTS changes(id INTEGER PRIMARY KEY,order_id INTEGER REFERENCES orders(id),user_id INTEGER REFERENCES users(id),payload TEXT,state TEXT DEFAULT 'Ожидает подтверждения',created TEXT);
  CREATE TABLE IF NOT EXISTS payment_requests(id INTEGER PRIMARY KEY,order_id INTEGER REFERENCES orders(id),user_id INTEGER REFERENCES users(id),message TEXT,state TEXT DEFAULT 'Ожидает ответа',created TEXT);
  CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),image TEXT,state TEXT DEFAULT 'Ожидает проверки',created TEXT);
  """)
  for k in ("home_delivery","inpost","evri","royal_mail","other_delivery","payment_card"): c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,app.config["PAYMENT_CARD"] if k=="payment_card" else ""))
  email,pw=os.getenv("ADMIN_EMAIL"),os.getenv("ADMIN_PASSWORD")
  if email and pw and not c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone(): c.execute("INSERT OR IGNORE INTO users(email,name,password,role,approved,created) VALUES(?,?,?,'admin',1,?)",(email.lower().strip(),"Mops Parcel Admin",generate_password_hash(pw),stamp()))
  c.commit()
 def send_tg(chat,msg):
  token=app.config["TELEGRAM_BOT_TOKEN"]
  if not token or not chat: return
  try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage",json={"chat_id":chat,"text":msg},timeout=5).raise_for_status()
  except requests.RequestException: app.logger.warning("Telegram delivery failed")
 def admin_msg(msg): send_tg(app.config["TELEGRAM_ADMIN_CHAT_ID"],msg)
 def client_msg(contact,msg):
  # Numeric Telegram chat ID is required; @username alone is not enough for bot messages.
  row=db().execute("SELECT telegram_chat_id FROM users WHERE telegram=?",(contact,)).fetchone()
  if row and row["telegram_chat_id"]: send_tg(row["telegram_chat_id"],msg)
 def login_required(fn):
  @wraps(fn)
  def inner(*a,**kw):
   if not g.user: return redirect(url_for("login"))
   if not g.user["approved"] and g.user["role"]!="admin": return render_template("pending.html"),403
   return fn(*a,**kw)
  return inner
 def admin_required(fn):
  @wraps(fn)
  @login_required
  def inner(*a,**kw):
   if g.user["role"]!="admin": abort(403)
   return fn(*a,**kw)
  return inner
 def upload(field,tag):
  if "mops_features" in app.extensions:
   feature=app.extensions["mops_features"]; return feature.save_file(feature.read_file(field),tag)
  f=request.files.get(field); ext=(f.filename.rsplit(".",1)[-1].lower() if f and "." in f.filename else "")
  if not f or not f.filename: raise ValueError("Прикрепите обязательное фото.")
  if ext not in {"jpg","jpeg","png","webp"}: raise ValueError("Формат: JPG, PNG или WEBP.")
  name=secure_filename(f"{tag}_{secrets.token_hex(12)}.{ext}"); f.save(Path(app.config["UPLOAD_FOLDER"])/name); return name
 @app.before_request
 def load_user():
  requested=request.args.get("lang")
  saved=request.cookies.get("mops_language","ru")
  g.lang=requested if requested in ("ru","uk","en") else (saved if saved in ("ru","uk","en") else "ru")
  uid=session.get("uid"); g.user=db().execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone() if uid else None
 @app.after_request
 def language_cookie(response):
  response.headers["Content-Language"]=getattr(g,"lang","ru")
  if request.cookies.get("mops_language")!=getattr(g,"lang","ru"):
   response.set_cookie("mops_language",getattr(g,"lang","ru"),max_age=31536000,samesite="Lax",httponly=True,secure=app.config["SESSION_COOKIE_SECURE"])
  return response
 def localized_changes(payload):
  result=[]
  for line in payload.splitlines():
   if ": " in line:
    key,value=line.split(": ",1)
    result.append(f"{t(key)}: {t(value) if key=='delivery' else value}")
   else:
    result.append(line)
  return "\n".join(result)
 @app.context_processor
 def localizations():
  manager=os.getenv("UKRAINE_MANAGER_USERNAME","").lstrip("@")
  manager=manager if re.fullmatch(r"[A-Za-z0-9_]{5,32}",manager or "") else "amrbasota"
  return {"t":t,"lang":getattr(g,"lang","ru"),"ui_strings":{k:t(k) for k in CATALOG},"localized_changes":localized_changes,"manager_username":manager,"manager_is_admin":manager=="amrbasota"}
 @app.errorhandler(HTTPException)
 def http_error(error):
  titles={403:"Недостаточно прав",404:"Страница не найдена",409:"Действие недоступно",410:"Срок ответа истёк"}
  return render_template("error.html",error_code=error.code,error_title=titles.get(error.code,"Не удалось выполнить запрос")),error.code
 @app.context_processor
 def common(): return {"user":g.get("user"),"statuses":STATUSES,"review_url":"https://t.me/resalecommunityy/975","telegram_bot_url":("https://t.me/"+os.getenv("TELEGRAM_BOT_USERNAME","").lstrip("@")) if os.getenv("TELEGRAM_BOT_USERNAME") else None}
 @app.route("/")
 def index(): return render_template("index.html")
 @app.route("/register",methods=["GET","POST"])
 def register():
  if request.method=="POST":
   name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); pw=request.form.get("password",""); tg=request.form.get("telegram","").strip().removeprefix("@")
   if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email) or len(pw)<8: flash("Проверьте имя, почту и пароль (не менее 8 символов).","error")
   else:
    try:
     db().execute("INSERT INTO users(email,name,password,telegram,telegram_token,created) VALUES(?,?,?,?,?,?)",(email,name,generate_password_hash(pw),tg,secrets.token_urlsafe(24),stamp())); db().commit(); admin_msg(f"Заявка на доступ: {name}, {email}, @{tg}"); flash("Заявка отправлена администратору.","success"); return redirect(url_for("login"))
    except sqlite3.IntegrityError: flash("Пользователь с такой почтой уже есть.","error")
  return render_template("register.html")
 @app.route("/login",methods=["GET","POST"])
 def login():
  if request.method=="POST":
   u=db().execute("SELECT * FROM users WHERE email=?",(request.form.get("email","").lower().strip(),)).fetchone()
   if u and check_password_hash(u["password"],request.form.get("password","")):
    session.clear(); session["uid"]=u["id"]; return redirect(url_for("admin" if u["role"]=="admin" else "dashboard"))
   flash("Неверная почта или пароль.","error")
  return render_template("login.html")
 @app.post("/logout")
 def logout(): session.clear(); return redirect(url_for("index"))
 @app.post("/telegram/webhook")
 def telegram_webhook():
  expected=os.getenv("TELEGRAM_WEBHOOK_SECRET","")
  if expected and request.headers.get("X-Telegram-Bot-Api-Secret-Token")!=expected: abort(403)
  payload=request.get_json(silent=True) or {}; msg=payload.get("message",{}); text=msg.get("text",""); chat=msg.get("chat",{}).get("id")
  match=re.fullmatch(r"/start mp_(\d+)_([A-Za-z0-9_-]+)",text.strip())
  if match and chat:
   row=db().execute("SELECT id,telegram_token FROM users WHERE id=?",(int(match.group(1)),)).fetchone()
   if row and secrets.compare_digest(row["telegram_token"],match.group(2)):
    db().execute("UPDATE users SET telegram_chat_id=? WHERE id=?",(str(chat),row["id"])); db().commit(); send_tg(str(chat),"Готово! Теперь Mops Parcel сможет присылать обновления.")
  return {"ok":True}
 @app.route("/dashboard")
 @login_required
 def dashboard():
  c=db(); orders=c.execute("SELECT * FROM orders WHERE user_id=? AND archived=0 ORDER BY id DESC",(g.user["id"],)).fetchall(); archived=c.execute("SELECT * FROM orders WHERE user_id=? AND archived=1 ORDER BY id DESC",(g.user["id"],)).fetchall(); reviews=c.execute("SELECT * FROM reviews WHERE user_id=? ORDER BY id DESC",(g.user["id"],)).fetchall()
  return render_template("dashboard.html",orders=orders,archived=archived,reviews=reviews)
 @app.route("/orders/new",methods=["GET","POST"])
 @login_required
 def new_order():
  settings={r["key"]:r["value"] for r in db().execute("SELECT * FROM settings")}
  if request.method=="POST":
   try:
    proof=upload("proof","proof"); photo=upload("item_photo","item"); item=request.form.get("item","").strip(); phone=request.form.get("phone","").strip(); delivery=request.form.get("delivery","").strip(); branch=request.form.get("branch","").strip(); tg=request.form.get("telegram","").strip().removeprefix("@")
    if not all((item,phone,delivery,tg)) or (delivery!="Домашняя доставка" and not branch): raise ValueError("Заполните все поля и укажите пункт выдачи.")
    oid=db().execute("INSERT INTO orders(user_id,item,phone,delivery,branch,telegram,proof,item_photo,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?)",(g.user["id"],item,phone,delivery,branch,tg,proof,photo,stamp(),stamp())).lastrowid; db().commit(); admin_msg(f"Новая заявка #{oid}: {item}, клиент {g.user['name']} (@{tg}). Проверьте, что статус покупки — Shipped."); flash("Заявка создана и ожидает проверки статуса Shipped.","success"); return redirect(url_for("dashboard"))
   except ValueError as e: flash(str(e),"error")
  return render_template("new_order.html",settings=settings)
 @app.post("/orders/<int:oid>/change")
 @login_required
 def change(oid):
  order=db().execute("SELECT * FROM orders WHERE id=? AND user_id=?",(oid,g.user["id"])).fetchone()
  if not order: abort(404)
  data={k:request.form.get(k,"").strip() for k in ("phone","delivery","branch","telegram") if request.form.get(k,"").strip()}
  if not data: flash("Укажите новые данные.","error")
  else:
   db().execute("INSERT INTO changes(order_id,user_id,payload,created) VALUES(?,?,?,?)",(oid,g.user["id"],"\n".join(f"{k}: {v}" for k,v in data.items()),stamp())); db().commit(); admin_msg(f"Изменение заявки #{oid}: "+", ".join(f"{k}={v}" for k,v in data.items())); flash("Запрос изменения отправлен администратору.","success")
  return redirect(url_for("dashboard"))
 @app.post("/orders/<int:oid>/payment-method")
 @login_required
 def other_payment(oid):
  if not db().execute("SELECT 1 FROM orders WHERE id=? AND user_id=?",(oid,g.user["id"])).fetchone(): abort(404)
  msg=request.form.get("message","Нужен другой способ оплаты").strip(); db().execute("INSERT INTO payment_requests(order_id,user_id,message,created) VALUES(?,?,?,?)",(oid,g.user["id"],msg,stamp())); db().commit(); admin_msg(f"Другой способ оплаты, заявка #{oid}, {g.user['email']}: {msg}"); flash("Запрос отправлен администратору.","success"); return redirect(url_for("dashboard"))
 @app.post("/reviews")
 @login_required
 def review():
  try:
   name=upload("review_image","review"); db().execute("INSERT INTO reviews(user_id,image,created) VALUES(?,?,?)",(g.user["id"],name,stamp())); db().commit(); admin_msg(f"Отзыв на проверку: {g.user['email']}"); flash("Скрин отзыва отправлен на проверку бонуса.","success")
  except ValueError as e: flash(str(e),"error")
  return redirect(url_for("dashboard"))
 @app.post("/orders/<int:oid>/photo-decision")
 @login_required
 def photo_decision(oid):
  order=db().execute("SELECT * FROM orders WHERE id=? AND user_id=?",(oid,g.user["id"])).fetchone()
  if not order: abort(404)
  if order["status"]!="Фотоотчёт готов": abort(409)
  if not order["deadline"] or datetime.fromisoformat(order["deadline"])<=datetime.now(timezone.utc): abort(410)
  choice=request.form.get("choice","")
  if choice not in ("accept","return","more_photos"): abort(400)
  labels={"accept":"Фотоотчёт принят","return":"Запрошен возврат","more_photos":"Запрошены дополнительные фото"}
  status="К отправке" if choice=="accept" else order["status"]
  db().execute("UPDATE orders SET status=?,photo_decision=?,updated=? WHERE id=?",(status,labels[choice],stamp(),oid)); db().commit()
  admin_msg(f"{labels[choice]} · заявка #{oid} · клиент {g.user['name']} (@{order['telegram']})")
  flash("Решение отправлено администратору.","success"); return redirect(url_for("dashboard"))
 @app.route("/admin")
 @admin_required
 def admin():
  c=db(); users=c.execute("SELECT * FROM users WHERE role='client' ORDER BY approved,id DESC").fetchall(); orders=c.execute("SELECT o.*,u.name AS client_name,u.email FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.id DESC").fetchall(); changes=c.execute("SELECT c.*,o.item,u.name AS client_name FROM changes c JOIN orders o ON o.id=c.order_id JOIN users u ON u.id=c.user_id WHERE c.state='Ожидает подтверждения'").fetchall(); payments=c.execute("SELECT p.*,u.name AS client_name FROM payment_requests p JOIN users u ON u.id=p.user_id WHERE p.state='Ожидает ответа'").fetchall(); reviews=c.execute("SELECT r.*,u.name AS client_name FROM reviews r JOIN users u ON u.id=r.user_id ORDER BY r.id DESC").fetchall(); settings={r["key"]:r["value"] for r in c.execute("SELECT * FROM settings")}; return render_template("admin.html",users=users,orders=orders,changes=changes,payments=payments,reviews=reviews,settings=settings)
 @app.post("/admin/users/<int:uid>/approve")
 @admin_required
 def approve(uid):
  u=db().execute("SELECT * FROM users WHERE id=? AND role='client'",(uid,)).fetchone()
  if not u: abort(404)
  db().execute("UPDATE users SET approved=1 WHERE id=?",(uid,)); db().commit(); client_msg(u["telegram"],"Mops Parcel: аккаунт подтверждён."); flash(f"Доступ подтверждён: {u['email']}","success"); return redirect(url_for("admin")+"#users")
 @app.post("/admin/orders/<int:oid>/update")
 @admin_required
 def update_order(oid):
  o=db().execute("SELECT o.*,u.telegram AS user_telegram FROM orders o JOIN users u ON u.id=o.user_id WHERE o.id=?",(oid,)).fetchone()
  if not o: abort(404)
  status=request.form.get("status",o["status"])
  if status not in STATUSES: abort(400)
  fee=request.form.get("fee","").strip(); tracking=request.form.get("tracking","").strip(); report=o["report"]
  if request.files.get("report") and request.files["report"].filename: report=upload("report","report"); status="Фотоотчёт готов"
  deadline=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat(timespec="seconds") if status=="Фотоотчёт готов" and (report!=o["report"] or o["status"]!="Фотоотчёт готов") else o["deadline"]; archived=int(status in ("Доставлено","Архив"))
  db().execute("UPDATE orders SET status=?,fee=?,tracking=?,report=?,deadline=?,updated=?,archived=? WHERE id=?",(status,fee,tracking,report,deadline,stamp(),archived,oid)); db().commit(); msg=f"Mops Parcel · заявка #{oid}: {status}."
  if fee:
   card=db().execute("SELECT value FROM settings WHERE key='payment_card'").fetchone()[0]; msg+=f" Счёт: {fee}. Реквизиты: {card or 'уточните у администратора'}."
  if tracking: msg+=f" Трек: {tracking}."
  if status=="Фотоотчёт готов": msg+=" В течение 2 дней можно запросить возврат или дополнительные фото."
  client_msg(o["user_telegram"],msg); flash(f"Заявка #{oid} обновлена.","success"); return redirect(url_for("admin")+"#orders")
 @app.post("/admin/settings")
 @admin_required
 def settings_save():
  for k in ("home_delivery","inpost","evri","royal_mail","other_delivery","payment_card"): db().execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(k,request.form.get(k,"").strip()))
  db().commit(); flash("Настройки адресов и оплаты сохранены.","success"); return redirect(url_for("admin")+"#settings")
 @app.post("/admin/changes/<int:cid>/<decision>")
 @admin_required
 def change_decision(cid,decision):
  if decision not in ("approve","reject"): abort(404)
  r=db().execute("SELECT c.*,u.telegram FROM changes c JOIN users u ON u.id=c.user_id WHERE c.id=?",(cid,)).fetchone()
  if not r or r["state"]!="Ожидает подтверждения": abort(404)
  state="Подтверждено" if decision=="approve" else "Отклонено"
  if decision=="approve":
   d=dict(line.split(": ",1) for line in r["payload"].splitlines() if ": " in line); d={k:d[k] for k in ("phone","delivery","branch","telegram") if k in d}
   if d: db().execute("UPDATE orders SET "+",".join(k+"=?" for k in d)+",updated=? WHERE id=? and user_id=? ",(*d.values(),stamp(),r["order_id"],r["user_id"]))
  db().execute("UPDATE changes SET state=? WHERE id=?",(state,cid)); db().commit(); client_msg(r["telegram"],f"Запрос изменения данных {state.lower()}."); flash(f"Запрос {state.lower()}.","success"); return redirect(url_for("admin")+"#requests")
 @app.post("/admin/payments/<int:pid>/respond")
 @admin_required
 def payment_respond(pid):
  r=db().execute("SELECT p.*,u.telegram FROM payment_requests p JOIN users u ON u.id=p.user_id WHERE p.id=?",(pid,)).fetchone()
  if not r: abort(404)
  msg=request.form.get("response","").strip(); db().execute("UPDATE payment_requests SET state='Ответ отправлен' WHERE id=?",(pid,)); db().commit(); client_msg(r["telegram"],msg or "Администратор ответит вам по оплате."); flash("Ответ отправлен.","success"); return redirect(url_for("admin")+"#requests")
 @app.post("/admin/reviews/<int:rid>/approve")
 @admin_required
 def review_approve(rid):
  r=db().execute("SELECT r.*,u.telegram FROM reviews r JOIN users u ON u.id=r.user_id WHERE r.id=?",(rid,)).fetchone()
  if not r: abort(404)
  db().execute("UPDATE reviews SET state='Бонус подтверждён' WHERE id=?",(rid,)); db().execute("UPDATE users SET bonus_balance=bonus_balance+1 WHERE id=?",(r['user_id'],)); db().commit(); client_msg(r["telegram"],"Отзыв проверен, бонус подтверждён. Спасибо!"); flash("Бонус за отзыв подтверждён.","success"); return redirect(url_for("admin")+"#reviews")
 @app.route("/uploads/<path:name>")
 @login_required
 def uploaded(name):
  name=secure_filename(name)
  if g.user["role"]!="admin":
   own=db().execute("SELECT 1 FROM orders WHERE user_id=? AND (proof=? OR item_photo=? OR report=?) UNION SELECT 1 FROM reviews WHERE user_id=? AND image=?",(g.user["id"],name,name,name,g.user["id"],name)).fetchone()
   if not own: abort(403)
  return send_from_directory(app.config["UPLOAD_FOLDER"],name)
 @app.errorhandler(413)
 def large(_e): flash("Файл слишком большой (лимит 12 МБ).","error"); return redirect(request.referrer or url_for("dashboard"))
 with app.app_context(): initialize()
 from enhancements import install_features
 install_features(app, db, stamp, login_required, admin_required)
 return app
app=create_app()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))





