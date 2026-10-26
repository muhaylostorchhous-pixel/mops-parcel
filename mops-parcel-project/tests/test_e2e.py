import os, tempfile, uuid
from io import BytesIO
import sqlite3
from pathlib import Path
import pytest

_TEST_ROOT=Path(__file__).resolve().parents[1]/".test-runtime"/"bootstrap"
_TEST_ROOT.mkdir(parents=True,exist_ok=True)
os.environ.setdefault("DATABASE_PATH",str(Path(_TEST_ROOT)/"bootstrap.sqlite3"))
os.environ.setdefault("UPLOAD_FOLDER",str(Path(_TEST_ROOT)/"bootstrap-uploads"))
os.environ.setdefault("ADMIN_EMAIL","admin@mops.test")
os.environ.setdefault("ADMIN_PASSWORD","Mops-test-Admin-27!")
from app import create_app

@pytest.fixture
def ctx():
    runtime=Path(__file__).resolve().parents[1]/".test-runtime"/uuid.uuid4().hex
    runtime.mkdir(parents=True,exist_ok=True)
    app=create_app({"TESTING":True,"CSRF_ENABLED":False,"SECRET_KEY":"test-key","DATABASE":str(runtime/"test.sqlite3"),"UPLOAD_FOLDER":str(runtime/"uploads"),"TELEGRAM_BOT_TOKEN":"","TELEGRAM_ADMIN_CHAT_ID":""})
    client=app.test_client()
    admin=app.test_client()
    admin.post("/login",data={"email":"admin@mops.test","password":"Mops-test-Admin-27!"})
    return app,client,admin

def register_and_approve(ctx):
    app,client,admin=ctx
    client.post("/register",data={"name":"Test Client","email":"client@mops.test","password":"Client-pass-27!","telegram":"mops_client"})
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); uid=conn.execute("SELECT id FROM users WHERE email='client@mops.test'").fetchone()[0]; conn.close()
    admin.post(f"/admin/users/{uid}/approve")
    client.post("/login",data={"email":"client@mops.test","password":"Client-pass-27!"})
    return uid

def image(name="proof.png"):
    from PIL import Image
    stream=BytesIO(); Image.new("RGB",(12,12),(20,80,200)).save(stream,format="PNG");stream.seek(0)
    return (stream,name)

def create_order(client,**extra):
    data={"product_type":"outerwear","shipped":"1","ua_name":"Test Client","ua_phone":"+380501234567","ua_city":"Kyiv","ua_branch":"101","item":"Vintage jacket","phone":"+380501234567","delivery":"InPost locker","branch":"Kyiv locker 1001","telegram":"mops_client","proof":image("proof.png"),"item_photo":image("item.jpg")}
    data.update(extra)
    return client.post("/orders/new",data=data,content_type="multipart/form-data",follow_redirects=True)

def first_order_id(app):
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); row=conn.execute("SELECT id FROM orders ORDER BY id LIMIT 1").fetchone(); conn.close()
    return row[0]

def test_01_homepage_loads_with_brand_and_cta(ctx):
    _,client,_=ctx
    response=client.get("/")
    assert response.status_code==200 and b"MOPS" in response.data and b"register" in response.data

def test_02_registration_waits_for_admin_approval(ctx):
    _,client,_=ctx
    response=client.post("/register",data={"name":"New Client","email":"new@mops.test","password":"Client-pass-27!","telegram":"new_client"},follow_redirects=True)
    assert response.status_code==200 and "Заявка отправлена".encode() in response.data
    client.post("/login",data={"email":"new@mops.test","password":"Client-pass-27!"})
    assert client.get("/dashboard").status_code==403

def test_03_admin_is_recognized_by_explicit_role(ctx):
    _,_,admin=ctx
    assert admin.get("/admin").status_code==200

def test_04_admin_approval_opens_client_dashboard(ctx):
    _,client,_=ctx
    register_and_approve(ctx)
    assert client.get("/dashboard").status_code==200
    assert client.get("/orders/new").status_code==200

def test_05_order_form_requires_shipped_proof_and_item_photo(ctx):
    _,client,_=ctx; register_and_approve(ctx)
    response=client.post("/orders/new",data={"product_type":"outerwear","shipped":"1","ua_name":"Test Client","ua_phone":"+380501234567","ua_city":"Kyiv","ua_branch":"101","item":"Shoes","delivery":"InPost locker","telegram":"mops_client"},follow_redirects=True)
    assert response.status_code==200 and "Прикрепите обязательное фото".encode() in response.data

def test_06_valid_order_with_two_photos_enters_review_queue(ctx):
    app,client,admin=ctx; register_and_approve(ctx)
    response=create_order(client)
    assert response.status_code==200 and "ожидает проверки статуса Shipped".encode() in response.data
    oid=first_order_id(app)
    admin_page=admin.get("/admin")
    assert f"MP · {oid:04d}".encode() in admin_page.data
    assert f"/orders/{oid}/files/proof/send".encode() in admin_page.data

def test_07_admin_only_routes_and_private_uploads(ctx):
    app,client,admin=ctx; register_and_approve(ctx); create_order(client); oid=first_order_id(app)
    assert client.get("/admin").status_code==403
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); fname=conn.execute("SELECT proof FROM orders WHERE id=?",(oid,)).fetchone()[0]; conn.close()
    assert client.get("/uploads/"+fname).status_code==200
    stranger=app.test_client()
    assert stranger.get("/uploads/"+fname).status_code in (302,403)

def test_08_admin_receipt_photo_report_and_two_day_window(ctx):
    app,client,admin=ctx; register_and_approve(ctx); create_order(client); oid=first_order_id(app)
    response=admin.post(f"/admin/orders/{oid}/update",data={"status":"Одержано","fee":"450","report":image("report.webp")},content_type="multipart/form-data",follow_redirects=True)
    assert response.status_code==200
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); row=conn.execute("SELECT status,report,deadline FROM orders WHERE id=?",(oid,)).fetchone(); conn.close()
    assert row[0]=="Фотоотчёт готов" and row[1].startswith("report_") and row[2]
    assert "2 дня".encode() in client.get("/dashboard").data
    assert client.post(f"/orders/{oid}/photo-decision",data={"choice":"accept"}).status_code==302
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); assert conn.execute("SELECT status,photo_decision FROM orders WHERE id=?",(oid,)).fetchone()==("К отправке","Фотоотчёт принят"); conn.close()

def test_09_change_and_alternative_payment_buttons_reach_admin(ctx):
    app,client,admin=ctx; register_and_approve(ctx); create_order(client); oid=first_order_id(app)
    client.post(f"/orders/{oid}/change",data={"phone":"+380671112233"},follow_redirects=True)
    page=admin.get("/admin")
    assert "Изменение".encode() in page.data
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); cid=conn.execute("SELECT id FROM changes LIMIT 1").fetchone()[0]; conn.close()
    admin.post(f"/admin/changes/{cid}/approve")
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); assert conn.execute("SELECT phone FROM orders WHERE id=?",(oid,)).fetchone()[0]=="+380671112233"; conn.close()
    client.post(f"/orders/{oid}/payment-method",data={"message":"Оплата переводом"},follow_redirects=True)
    assert "Оплата".encode() in admin.get("/admin").data
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); pid=conn.execute("SELECT id FROM payment_requests LIMIT 1").fetchone()[0]; conn.close()
    assert admin.post(f"/admin/payments/{pid}/respond",data={"response":"Напишем вам в Telegram"}).status_code==302

def test_10_tracking_delivery_archive_and_review_bonus(ctx):
    app,client,admin=ctx; uid=register_and_approve(ctx); create_order(client); oid=first_order_id(app)
    confirm_payment(ctx,oid)
    admin.post(f"/admin/orders/{oid}/update",data={"status":"Отправлено","tracking":"UK(251026)-1-UA","fee":"450"})
    assert "UK(251026)-1-UA".encode() in client.get("/dashboard").data
    admin.post(f"/admin/orders/{oid}/update",data={"status":"Доставлено"})
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); assert conn.execute("SELECT archived FROM orders WHERE id=?",(oid,)).fetchone()[0]==1; conn.close()
    client.post("/reviews",data={"review_image":image("review.png")},content_type="multipart/form-data")
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); rid=conn.execute("SELECT id FROM reviews LIMIT 1").fetchone()[0]; conn.close()
    admin.post(f"/admin/reviews/{rid}/approve")
    with app.app_context():
        conn=sqlite3.connect(app.config["DATABASE"]); assert conn.execute("SELECT bonus_balance FROM users WHERE id=?",(uid,)).fetchone()[0]==1; conn.close()
    assert b"1" in client.get("/dashboard").data







def confirm_payment(ctx,oid):
    app,client,admin=ctx
    admin.post(f"/admin/orders/{oid}/update",data={"status":"Одержано","report":image("report.png")},content_type="multipart/form-data")
    response=client.post(f"/orders/{oid}/pay",data={"screenshot":image("transfer.png"),"receipt":(BytesIO(b"%PDF-1.4\nTest bank receipt"),"receipt.pdf")},content_type="multipart/form-data")
    assert response.status_code==302
    with sqlite3.connect(app.config["DATABASE"]) as conn:pid=conn.execute("SELECT id FROM order_payments WHERE order_id=? ORDER BY id DESC",(oid,)).fetchone()[0]
    assert admin.post(f"/admin/payment-proofs/{pid}/approve").status_code==302
