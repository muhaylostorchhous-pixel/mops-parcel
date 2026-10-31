"""Regression scenarios for the parcel workspace on both configured databases."""
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from test_services import env, register, query, execute
from test_e2e import create_order, image
from test_i18n import visible


def key(client):
    page = client.get('/orders/new').get_data(as_text=True)
    return re.search(r'name="submission_key" value="([^"]+)"', page)[1]


def test_repeated_submission_creates_one_parcel_and_two_files(env):
    app, client, _, _ = env; register(env); token = key(client)
    create_order(client, submission_key=token, save_address='1')
    for _ in range(10):
        assert client.post('/orders/new', data={'submission_key': token}).status_code == 302
    assert query(app, 'SELECT COUNT(*) FROM orders')[0] == 1
    assert query(app, 'SELECT COUNT(*) FROM file_objects')[0] == 2
    assert query(app, 'SELECT COUNT(*) FROM addresses')[0] == 1


def test_concurrent_double_click_is_atomic(env, monkeypatch):
    app, client, _, _ = env; uid = register(env); token = key(client)
    barrier = Barrier(2); feature = app.extensions['mops_features']; original = feature.read_file
    def read_file(field, **kw):
        result = original(field, **kw)
        if field == 'item_photo': barrier.wait(timeout=15)
        return result
    monkeypatch.setattr(feature, 'read_file', read_file)
    def submit(_):
        c = app.test_client()
        with c.session_transaction() as s: s['uid'] = uid
        return create_order(c, submission_key=token).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(submit, range(2))) == [200, 200]
    assert query(app, 'SELECT COUNT(*) FROM orders')[0] == 1
    assert query(app, 'SELECT COUNT(*) FROM file_objects')[0] == 2


def test_failed_validation_can_retry_same_submission_key(env):
    app, client, _, _ = env; register(env); token = key(client)
    create_order(client, submission_key=token, shipped='0')
    assert not query(app, 'SELECT id FROM orders')
    create_order(client, submission_key=token)
    create_order(client, submission_key=key(client))
    assert query(app, 'SELECT COUNT(*) FROM orders')[0] == 2


def test_detail_page_is_private_and_admin_can_view(env):
    app, client, admin, _ = env; register(env); create_order(client)
    oid = query(app, 'SELECT id FROM orders')[0]
    outsider = app.test_client(); register(env, 'other@mops.test', outsider)
    assert outsider.get(f'/orders/{oid}').status_code == 403
    assert client.get(f'/orders/{oid}').status_code == 200
    assert admin.get(f'/orders/{oid}').status_code == 200
    assert client.get('/orders/999999').status_code == 404
    assert app.test_client().get(f'/orders/{oid}').status_code == 302


def test_detail_timeline_tracks_receipt_and_report(env):
    app, client, admin, _ = env; register(env); create_order(client)
    oid = query(app, 'SELECT id FROM orders')[0]
    admin.post(f'/admin/orders/{oid}/update', data={'status': 'Одержано'})
    admin.post(f'/admin/orders/{oid}/update', data={'report': image('report.png')})
    page = client.get(f'/orders/{oid}?lang=en')
    body = visible(page)
    assert 'Request created' in body and 'Photo report' in body
    assert body.count('UTC') >= 3
    assert '101' in body and 'Kyiv' in body
    assert len(query(app, 'SELECT parcel_code FROM orders')[0]) == 8


def test_support_link_prefills_only_owned_parcel_and_does_not_send(env):
    app, client, admin, _ = env; uid = register(env); create_order(client)
    oid = query(app, 'SELECT id FROM orders')[0]
    body = client.get(f'/support?parcel={oid}&lang=en').get_data(as_text=True)
    assert f'question about parcel #{oid}' in body
    assert not query(app, 'SELECT id FROM support_messages')
    outsider = app.test_client(); register(env, 'other@mops.test', outsider)
    assert outsider.get(f'/support?parcel={oid}').status_code == 403
    assert admin.get(f'/support?user={uid}&parcel={oid}').status_code == 200


def test_details_all_languages_and_escaped_item(env):
    app, client, _, _ = env; register(env)
    create_order(client, item='<img src=x onerror=alert(1)>')
    oid = query(app, 'SELECT id FROM orders')[0]
    for lang, label in [('ru', 'История посылки'), ('uk', 'Історія посилки'), ('en', 'Parcel history')]:
        page = client.get(f'/orders/{oid}?lang={lang}')
        assert label in visible(page)
        assert '<img src=x' not in page.get_data(as_text=True)
        assert 'ux.' not in visible(page)
    assert not re.search(r'[А-Яа-яІіЇїЄє]', visible(page))


def test_dashboard_counts_archive_and_filters(env):
    app, client, _, _ = env; register(env)
    create_order(client, item='Active')
    create_order(client, item='Arrived')
    execute(app, "UPDATE orders SET archived=1,status='Доставлено',delivered_at=updated WHERE item='Arrived'")
    body = client.get('/dashboard?lang=en').get_data(as_text=True)
    assert 'data-parcel-search' in body and 'data-parcel-filter="payment"' in body
    assert 'workspace-summary' in body and 'mobile-dock' in body
    oid = query(app, "SELECT id FROM orders WHERE item='Arrived'")[0]
    assert client.get(f'/orders/{oid}').status_code == 200
    assert 'Delivery complete.' in visible(client.get(f'/orders/{oid}'))


def test_invalid_submission_key_rejected_without_writes(env):
    app, client, _, _ = env; register(env)
    for token in ['bad key', 'x'*65, '<script>']:
        assert create_order(client, submission_key=token).status_code == 400
    assert not query(app, 'SELECT id FROM orders')
    assert not query(app, 'SELECT name FROM file_objects')


def test_migration_keeps_submission_and_history_on_restart(env):
    app, client, _, _ = env; register(env); token = key(client)
    create_order(client, submission_key=token)
    from app import create_app
    restarted = create_app(dict(app.config))
    assert query(restarted, 'SELECT submission_key FROM orders')[0] == token
    assert query(restarted, 'SELECT COUNT(*) FROM file_objects')[0] == 2


def test_expired_report_has_support_instead_of_dead_action(env):
    app, client, admin, _ = env; register(env); create_order(client)
    oid = query(app, 'SELECT id FROM orders')[0]
    admin.post(f'/admin/orders/{oid}/update', data={'report': image('report.png')})
    execute(app, "UPDATE orders SET deadline='2000-01-01T00:00:00+00:00' WHERE id=?", (oid,))
    for path in ['/dashboard', f'/orders/{oid}']:
        page = client.get(path+'?lang=en')
        assert 'response window has ended' in visible(page)
        assert 'value="accept"' not in page.get_data(as_text=True)
    assert client.post(f'/orders/{oid}/photo-decision', data={'choice':'accept'}).status_code == 410


@pytest.mark.parametrize('choice,expected', [('return', 'Your return request'), ('more_photos', 'You requested more photos')])
def test_photo_request_recorded_and_admin_notification_queued(env, choice, expected):
    app, client, admin, _ = env; register(env); create_order(client)
    oid = query(app, 'SELECT id FROM orders')[0]
    admin.post(f'/admin/orders/{oid}/update', data={'report': image('report.png')})
    app.config['TELEGRAM_ADMIN_CHAT_ID'] = '123456'
    client.post(f'/orders/{oid}/photo-decision', data={'choice':choice})
    assert expected in visible(client.get(f'/orders/{oid}?lang=en'))
    assert query(app, 'SELECT COUNT(*) FROM order_audit WHERE order_id=?', (oid,))[0] == 2
    assert query(app, "SELECT COUNT(*) FROM notification_outbox WHERE chat_id='123456' AND state='pending'")[0] == 1
