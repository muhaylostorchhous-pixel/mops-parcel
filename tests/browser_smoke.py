"""Optional real-browser smoke test. Requires playwright and installed Chrome."""
import os,re,threading,tempfile,uuid
from pathlib import Path
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
run=ROOT/'.test-runtime'/('browser-'+uuid.uuid4().hex);run.mkdir(parents=True)
os.environ['DATABASE_PATH']=str(run/'bootstrap.db');os.environ['UPLOAD_FOLDER']=str(run/'bootstrap-files')
os.environ['ADMIN_EMAIL']='admin@mops.test';os.environ['ADMIN_PASSWORD']='Mops-test-Admin-27!';os.environ['NOTIFICATION_WORKER']='false'
from app import create_app
app=create_app({'TESTING':True,'DATABASE_URL':'','DATABASE':str(run/'browser.db'),'UPLOAD_FOLDER':str(run/'files'),'SECRET_KEY':'browser-secret-test-32-characters','TELEGRAM_BOT_TOKEN':'','TELEGRAM_ADMIN_CHAT_ID':''})
server=make_server('127.0.0.1',0,app,threaded=True);threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_port);errors=[];checks=[]
def check(label):checks.append(label);print('PASS',label,flush=True)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(channel='chrome',headless=True)
  client=browser.new_context(viewport={'width':390,'height':844});page=client.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(url+'/?lang=en');expect(page.locator('h1')).to_be_visible();check('Mobile home and English language')
  page.goto(url+'/register');page.locator('input[name=name]').fill('Browser Client');page.locator('input[name=email]').fill('browser@mops.test');page.locator('input[name=password]').fill('Browser-pass-27!');page.locator('input[name=telegram]').fill('browser_client');page.locator('form[method=post]').first.locator('button:not([type=button])').click();page.wait_for_url('**/profile');page.locator('#onboardingClose').click();expect(page.locator('#onboarding')).to_be_hidden();check('Registration creates profile without email confirmation')
  adminctx=browser.new_context();admin=adminctx.new_page();admin.on('pageerror',lambda e:errors.append(str(e)))
  admin.goto(url+'/login?lang=en');admin.locator('input[name=email]').fill('admin@mops.test');admin.locator('input[name=password]').fill('Mops-test-Admin-27!');admin.locator('form[method=post]').first.locator('button:not([type=button])').click();admin.wait_for_url('**/admin');admin.goto(url+'/admin/users');card=admin.locator('.member-card').filter(has_text='browser@mops.test');card.locator('form button').click();check('Admin login, directory and approval')
  page.goto(url+'/start-delivery');page.wait_for_url('**/orders/new');check('Existing account goes to parcel form')
  page.goto(url+'/support');page.locator('#chatBody').fill('Where is my parcel?');page.locator('#sendMessage').click();expect(page.locator('.chat-bubble')).to_have_count(1);check('Client sends chat message through JavaScript')
  admin.goto(url+'/support');admin.locator('.conversation').filter(has_text='Browser Client').click();expect(admin.locator('.chat-bubble')).to_have_count(1);admin.locator('#chatBody').fill('Your parcel is on its way.');admin.locator('#sendMessage').click();expect(page.locator('.chat-bubble')).to_have_count(2,timeout=12000);check('Admin reply arrives without page reload')
  for lang in ['ru','uk','en']:
   page.goto(url+'/support?lang='+lang);expect(page.locator('html')).to_have_attribute('lang',lang)
   assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
  check('Chat languages and mobile overflow')
  admin.goto(url+'/admin/logs?lang=en');expect(admin.locator('table')).to_be_visible();r=page.goto(url+'/admin/users');assert r.status==403;assert not errors,errors;check('Audit page, role protection and no JavaScript errors')
  # Additional UI journeys: real forms, uploads, filters, payment and archive.
  picture=run/'purchase.png';Image.new('RGB',(40,40),(40,100,210)).save(picture)
  receipt=run/'receipt.pdf';receipt.write_bytes(b'%PDF-1.4\nMops test transfer receipt')
  page.goto(url+'/orders/new?lang=en')
  page.locator('[name=item]').fill('Nike Air Max 95')
  page.locator('#productType').select_option('shoes_box')
  expect(page.locator('#summaryPrice')).to_have_text('700 ₴')
  expect(page.locator('#summaryItem')).to_have_text('Nike Air Max 95')
  check('Live delivery cost and item summary')
  for field,value in [('ua_name','Browser Client'),('ua_phone','+380501234567'),('ua_city','Kyiv'),('ua_branch','101')]:
   page.locator(f'[name={field}]').fill(value)
  page.locator('#delivery').select_option('InPost locker')
  page.locator('[name=proof]').set_input_files(str(picture));page.locator('[name=item_photo]').set_input_files(str(picture))
  page.locator('[name=shipped]').check();page.locator('#submitParcel').click();page.wait_for_url('**/dashboard')
  expect(page.locator('[data-parcel-card]')).to_have_count(1);check('Parcel submission with two files and saved address')
  page.locator('[data-parcel-search]').fill('missing item');expect(page.locator('[data-filter-empty]')).to_be_visible()
  page.locator('[data-filter-reset]').click();expect(page.locator('[data-parcel-card]')).to_be_visible()
  page.locator('[data-parcel-filter=transit]').click();expect(page.locator('[data-filter-empty]')).to_be_visible()
  page.locator('[data-parcel-filter=all]').click();check('Search, empty state, status filters and reset')
  page.screenshot(path=str(run/'dashboard-mobile.png'),full_page=True)
  page.locator('.parcel-open').click();page.wait_for_url(re.compile(r'/orders/\d+$'))
  oid=page.url.rsplit('/',1)[-1];expect(page.locator('.parcel-timeline li')).to_have_count(1)
  page.locator('.detail-support').first.click();expect(page.locator('#chatBody')).to_have_value(re.compile('Nike Air Max 95'))
  check('Private parcel history and support draft')
  page.goto(url+'/dashboard?lang=en');page.locator('.mobile-dock a[href="/profile"]').click();page.wait_for_url('**/profile')
  page.locator('.mobile-dock a[href="/dashboard"]').click();page.wait_for_url('**/dashboard');check('Mobile dock navigation')
  admin.goto(url+'/admin?lang=en');order=admin.locator('.admin-order').filter(has_text='Nike Air Max 95')
  order.locator('[name=status]').select_option('Одержано');order.locator('[name=report]').set_input_files(str(picture));order.locator('.admin-order-form button').click()
  page.reload();expect(page.locator('.invoice-banner')).to_be_visible();check('Admin photo report and client invoice')
  page.goto(url+f'/orders/{oid}/pay');page.locator('[name=screenshot]').set_input_files(str(picture));page.locator('[name=receipt]').set_input_files(str(receipt));page.locator('form[enctype] button').click();page.wait_for_url('**/dashboard')
  check('Payment with transfer screenshot and PDF receipt')
  admin.goto(url+'/admin');admin.locator('form[action$="/approve"]').filter(has=admin.locator('input[name=csrf_token]')).all()
  approval=admin.locator('form[action^="/admin/payment-proofs/"][action$="/approve"]');expect(approval).to_have_count(1);approval.locator('button').click()
  page.reload();expect(page.locator('.invoice-banner')).to_have_count(0);check('Admin payment approval removes invoice')
  page.goto(url+f'/orders/{oid}');page.locator('form:has(input[value=accept]) button').click();page.wait_for_url('**/dashboard')
  admin.goto(url+'/admin');order=admin.locator('.admin-order').filter(has_text='Nike Air Max 95')
  order.locator('[name=status]').select_option('Отправлено');order.locator('[name=tracking]').fill('UK(281026)-1-UA');order.locator('.admin-order-form button').click()
  page.goto(url+f'/orders/{oid}?lang=en');expect(page.locator('#shipmentTrack')).to_have_text('UK(281026)-1-UA')
  expect(page.locator('.parcel-timeline li')).to_have_count(5);check('Dispatch tracking and event timeline')
  admin.goto(url+'/admin');order=admin.locator('.admin-order').filter(has_text='Nike Air Max 95');order.locator('[name=status]').select_option('Доставлено');order.locator('.admin-order-form button').click()
  page.goto(url+'/dashboard');page.locator('.archive summary').click();page.locator('.archive a').click();expect(page.locator('.art-delivered')).to_be_visible();check('Delivered parcel remains accessible in archive')
  for lang in ['ru','uk','en']:
   for width in [360,390,768,1440]:
    page.set_viewport_size({'width':width,'height':900});page.goto(url+f'/orders/{oid}?lang='+lang)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(lang,width)
  check('Three languages and four responsive widths')
  page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path=str(run/'parcel-desktop.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(run/'parcel-mobile.png'),full_page=True)
  guest=client.new_page();guest.goto(url+'/login?lang=en')
  # Sign-in page redirects for existing users; use a separate guest context for password controls.
  guestctx=browser.new_context(viewport={'width':390,'height':844});guest=guestctx.new_page();guest.on('pageerror',lambda e:errors.append(str(e)))
  guest.goto(url+'/login?lang=en');guest.locator('[name=password]').fill('Example-password');guest.locator('.password-toggle').click();expect(guest.locator('[name=password]')).to_have_attribute('type','text');guest.locator('.password-toggle').click();expect(guest.locator('[name=password]')).to_have_attribute('type','password')
  guest.goto(url+'/?lang=en');guest.locator('.faq-grid summary').first.click();expect(guest.locator('.faq-grid details').first).to_have_attribute('open','')
  guest.emulate_media(reduced_motion='reduce');assert guest.evaluate('matchMedia("(prefers-reduced-motion: reduce)").matches')
  assert not errors,errors;check('Password toggle, FAQ and no JavaScript errors')
  # Archive API is mocked; the browser still exercises the real admin/client routes.
  archive_calls=[];archive_channel='-1001234567890';archive_client='123456789'
  def archive_api(method,payload,files=None):
   archive_calls.append((method,dict(payload),bool(files)))
   if method=='getChat':return {'id':int(archive_channel),'type':'channel'}
   if method=='getFile':return {'file_id':payload['file_id'],'file_path':'documents/report.png'}
   if method=='sendDocument':return {'message_id':len(archive_calls),'chat':{'id':int(payload['chat_id'])},'document':{'file_id':'browser-archive-document'}}
   return {'message_id':len(archive_calls)}
  app.config.update(TELEGRAM_BOT_TOKEN='123456:browser-test',TELEGRAM_ARCHIVE_CHAT_ID=archive_channel)
  app.extensions['mops_features'].telegram.call=archive_api
  with app.app_context():
   c=app.extensions['services'].db();c.execute("UPDATE users SET telegram_chat_id=? WHERE email='browser@mops.test'",(archive_client,));c.commit()
  admin.goto(url+'/admin/report-archive?lang=en');expect(admin.locator('h1')).to_have_text('Photo report archive')
  admin.locator('form[action="/admin/report-archive/retry"] button').click();expect(admin.locator('.alert.success')).to_be_visible();check('Admin archive page and retry button')
  with app.app_context():app.extensions['report_archive'].drain()
  admin.reload();expect(admin.locator('.archive-job .status-pill')).to_contain_text('File removed from database')
  page.goto(url+f'/orders/{oid}?lang=en');expect(page.locator('.notice')).to_contain_text('stored in Telegram');check('Confirmed archive cleanup visible to admin and client')
  archive_calls.clear();page.locator(f'form[action="/orders/{oid}/files/report/send"] button').click();page.wait_for_url('**/dashboard')
  assert any(method=='sendDocument' and payload.get('document')=='browser-archive-document' and not upload for method,payload,upload in archive_calls)
  assert page.goto(url+'/admin/report-archive').status==403
  assert page.goto(url+'/healthz').json()=={'status':'ok'}
  assert not errors,errors;check('Report retrieval by Telegram file ID and private archive access')
  page.goto(url+'/support?lang=en');page.screenshot(path=str(run/'support-mobile.png'),full_page=True)
  browser.close()
finally:server.shutdown()
print('Browser checks:',len(checks),'Screenshot:',run/'support-mobile.png')
