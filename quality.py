"""Parcel detail workspace and accessible interface additions."""
from datetime import datetime, timezone
from flask import g, render_template, request, url_for
from i18n import CATALOG, t
from quality_i18n import STRINGS

CATALOG.update(STRINGS)
CATALOG.update({row['ru']: row for row in STRINGS.values()})


def next_step(order):
    if order['status'] == 'Отклонено': return 'ux.next_rejected'
    if order['archived'] or order['status'] == 'Доставлено': return 'ux.next_done'
    if order['status'] == 'Отправлено': return 'ux.next_transit'
    if order['photo_decision'] == 'Запрошен возврат': return 'ux.next_return'
    if order['photo_decision'] == 'Запрошены дополнительные фото': return 'ux.next_photos'
    if order['payment_status'] == 'pending': return 'ux.next_review'
    if order['report'] and not order['photo_decision']: return 'ux.next_report' if photo_window_open(order) else 'ux.expired'
    if order['report'] and order['payment_status'] != 'paid': return 'ux.next_pay'
    if order['status'] == 'К отправке': return 'ux.next_ready'
    if order['status'] == 'Одержано': return 'ux.next_received'
    return 'ux.next_wait'


def photo_window_open(order):
    try:
        return order['status'] == 'Фотоотчёт готов' and datetime.fromisoformat(order['deadline']) > datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def install_quality(app, db, login_required):
    feature = app.extensions['mops_features']

    @app.template_filter('parcel_date')
    def parcel_date(value):
        try:
            return datetime.fromisoformat(value).strftime('%d.%m.%Y · %H:%M UTC')
        except (ValueError, TypeError):
            return value or '—'

    @app.context_processor
    def workspace_context():
        stats = None
        if g.get('user') and request.endpoint == 'dashboard':
            uid = g.user['id']
            stats = db().execute("""SELECT
                SUM(CASE WHEN archived=0 AND status<>'Отклонено' THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN archived=0 AND status<>'Отклонено' AND report<>'' AND fee<>'' AND payment_status='unpaid' THEN 1 ELSE 0 END) AS unpaid,
                SUM(CASE WHEN delivered_at<>'' THEN 1 ELSE 0 END) AS delivered
                FROM orders WHERE user_id=?""", (uid,)).fetchone()
        return {'workspace_stats': stats, 'next_step': next_step, 'photo_window_open': photo_window_open}

    @app.get('/orders/<int:oid>')
    @login_required
    def parcel_detail(oid):
        order = feature.owned_order(oid, admin=True)
        history = db().execute('SELECT action,created FROM order_audit WHERE order_id=? ORDER BY id', (oid,)).fetchall()
        changes = db().execute('SELECT state,created FROM changes WHERE order_id=? ORDER BY id DESC LIMIT 5', (oid,)).fetchall()
        return render_template('parcel_detail.html', order=order, history=history, parcel_changes=changes)

    # A support link may prefill a draft; it never sends a message automatically.
    @app.before_request
    def prepare_support_draft():
        if request.endpoint != 'support' or not g.get('user') or not request.args.get('parcel', type=int):
            return
        order = feature.owned_order(request.args.get('parcel', type=int), admin=True)
        if g.user['role'] == 'admin' and request.args.get('user', type=int) != order['user_id']:
            from flask import abort
            abort(403)
        g.parcel_support_draft = t('ux.support_draft', id=order['id'], item=order['item'])

    @app.context_processor
    def support_draft():
        return {'support_draft': g.get('parcel_support_draft', '')}
