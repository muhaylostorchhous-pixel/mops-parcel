import re
import sqlite3
from html.parser import HTMLParser
from test_e2e import ctx, register_and_approve, create_order, first_order_id, image, confirm_payment

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if not self.skip:
            self.parts.extend(v for k, v in attrs if k in ("placeholder", "aria-label", "title") and v)
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def visible(response):
    parser = VisibleText()
    parser.feed(response.get_data(as_text=True))
    return " ".join(parser.parts)

def test_11_full_public_pages_in_three_languages(ctx):
    _, client, _ = ctx
    expected = {"ru": ("Войти", "Мы на связи в Telegram"), "uk": ("Увійти", "Ми на зв'язку в Telegram"), "en": ("Sign in", "Find us on Telegram")}
    for lang, labels in expected.items():
        for path in ("/", "/login", "/register"):
            response = client.get(path + "?lang=" + lang)
            assert response.status_code == 200
            assert f'<html lang="{lang}">' in response.get_data(as_text=True)
            for label in labels:
                assert label in visible(response)

def test_12_language_persists_across_navigation_login_and_logout(ctx):
    _, client, _ = ctx
    register_and_approve(ctx)
    client.get("/?lang=en")
    assert client.get("/orders/new").headers["Content-Language"] == "en"
    assert "Sign in" in visible(client.post("/logout", follow_redirects=True))
    response = client.post("/login", data={"email":"client@mops.test", "password":"Client-pass-27!"}, follow_redirects=True)
    assert response.headers["Content-Language"] == "en"
    assert not re.search(r"[А-Яа-яІіЇїЄє]", visible(response))

def test_13_invalid_language_keeps_saved_preference(ctx):
    _, client, _ = ctx
    client.get("/?lang=uk")
    assert client.get("/?lang=invalid").headers["Content-Language"] == "uk"
    client.set_cookie("mops_language", "invalid")
    assert client.get("/").headers["Content-Language"] == "ru"

def test_14_validation_and_flash_messages_are_localized(ctx):
    _, client, _ = ctx
    client.get("/?lang=en")
    response = client.post("/login", data={"email":"missing@mops.test", "password":"wrong"}, follow_redirects=True)
    assert "Incorrect email or password." in visible(response)
    client.get("/?lang=uk")
    response = client.post("/login", data={"email":"missing@mops.test", "password":"wrong"}, follow_redirects=True)
    assert "Неправильна пошта або пароль." in visible(response)
    client.get("/?lang=en")
    response = client.post("/register", data={"name":"Test", "email":"bad", "password":"short"})
    assert "Check your name, email and password" in visible(response)

def test_15_client_statuses_and_delivery_translate_without_mutating_data(ctx):
    app, client, _ = ctx
    register_and_approve(ctx)
    create_order(client, delivery="Домашняя доставка", branch="")
    from app import STATUSES
    from i18n import t
    oid = first_order_id(app)
    for status in STATUSES:
        with sqlite3.connect(app.config["DATABASE"]) as db:
            db.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
        response = client.get("/dashboard?lang=en")
        assert t(status, "en") in visible(response)
        assert "Home delivery" in visible(response)
        with sqlite3.connect(app.config["DATABASE"]) as db:
            assert db.execute("SELECT status,delivery FROM orders WHERE id=?", (oid,)).fetchone() == (status, "Домашняя доставка")

def test_16_english_admin_form_submits_canonical_status(ctx):
    app, client, admin = ctx
    register_and_approve(ctx)
    create_order(client)
    oid = first_order_id(app)
    response = admin.get("/admin?lang=en")
    assert '<option value="Отправлено"' in response.get_data(as_text=True)
    assert not re.search(r"[А-Яа-яІіЇїЄє]", visible(response))
    confirm_payment(ctx,oid)
    response = admin.post(f"/admin/orders/{oid}/update", data={"status":"Отправлено","tracking":"UK(251026)-1-UA"}, follow_redirects=True)
    assert f"Parcel #{oid} updated." in visible(response)
    with sqlite3.connect(app.config["DATABASE"]) as db:
        assert db.execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()[0] == "Отправлено"

def test_17_admin_change_labels_and_default_payment_request_are_localized(ctx):
    app, client, admin = ctx
    register_and_approve(ctx)
    create_order(client)
    oid = first_order_id(app)
    client.post(f"/orders/{oid}/change", data={"phone":"+380671112233", "delivery":"Домашняя доставка"})
    client.post(f"/orders/{oid}/payment-method")
    response = admin.get("/admin?lang=en")
    page = visible(response)
    assert "Phone: +380671112233\nDelivery method: Home delivery" in page
    assert "Another payment method requested" in page
    assert not re.search(r"[А-Яа-яІіЇїЄє]", page)

def test_18_error_and_pending_pages_are_localized(ctx):
    _, client, _ = ctx
    response = client.get("/missing-page?lang=en")
    assert response.status_code == 404 and "Page not found" in visible(response)
    client.post("/register", data={"name":"Pending", "email":"pending@mops.test", "password":"Client-pass-27!"})
    client.post("/login", data={"email":"pending@mops.test", "password":"Client-pass-27!"})
    response = client.get("/dashboard")
    assert response.status_code == 403
    assert not re.search(r"[А-Яа-яІіЇїЄє]", visible(response))
    client.post("/logout")
    register_and_approve(ctx)
    response = client.get("/admin")
    assert response.status_code == 403 and "Access denied" in visible(response)

def test_19_contact_links_and_manager_configuration(ctx, monkeypatch):
    _, client, _ = ctx
    monkeypatch.delenv("UKRAINE_MANAGER_USERNAME", raising=False)
    response = client.get("/?lang=en")
    assert 'href="https://t.me/amrbasota"' in response.get_data(as_text=True)
    assert 'href="https://t.me/wrong_cloo"' in response.get_data(as_text=True)
    assert 'href="https://t.me/barujka032"' in response.get_data(as_text=True)
    monkeypatch.setenv("UKRAINE_MANAGER_USERNAME", "@uk_manager")
    response = client.get("/")
    assert 'href="https://t.me/uk_manager"' in response.get_data(as_text=True)
    assert "Via the administrator" not in visible(response)

def test_20_reports_reviews_and_all_form_labels_in_english(ctx):
    app, client, admin = ctx
    register_and_approve(ctx)
    create_order(client)
    oid = first_order_id(app)
    admin.post(f"/admin/orders/{oid}/update", data={"status":"Одержано", "fee":"450", "report":image("report.png")}, content_type="multipart/form-data")
    client.post("/reviews", data={"review_image":image("review.png")}, content_type="multipart/form-data")
    for browser, path in ((client,"/dashboard"), (client,"/orders/new"), (admin,"/admin")):
        response = browser.get(path + "?lang=en")
        assert response.status_code == 200
        assert not re.search(r"[А-Яа-яІіЇїЄє]", visible(response)), visible(response)