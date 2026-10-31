"""UI translations. Database status values remain stable across languages."""
import re
from flask import g, has_request_context

ROWS = """
Язык|Мова|Language
Войти|Увійти|Sign in
Выйти|Вийти|Sign out
Панель|Панель|Dashboard
Открыть аккаунт|Створити акаунт|Create account
Мои посылки|Мої посилки|My parcels
Войти — Mops Parcel|Вхід — Mops Parcel|Sign in — Mops Parcel
Создать аккаунт — Mops Parcel|Створення акаунта — Mops Parcel|Create account — Mops Parcel
Мои посылки — Mops Parcel|Мої посилки — Mops Parcel|My parcels — Mops Parcel
Новая посылка — Mops Parcel|Нова посилка — Mops Parcel|New parcel — Mops Parcel
Админ-панель — Mops Parcel|Панель адміністратора — Mops Parcel|Admin dashboard — Mops Parcel
Заявка на рассмотрении — Mops Parcel|Заявка на розгляді — Mops Parcel|Account pending — Mops Parcel
Mops Parcel — покупки из UK без хлопот|Mops Parcel — покупки з UK без клопоту|Mops Parcel — UK shopping, delivered
UK → UA · PERSONAL PARCEL SERVICE|UK → UA · ПЕРСОНАЛЬНА ДОСТАВКА|UK → UA · PERSONAL PARCEL SERVICE
Твоя покупка.|Твоя покупка.|Your purchase.
Наш маршрут.|Наш маршрут.|Our route.
Адрес для выкупа в Великобритании, фотоотчёт и доставка в Украину — каждый этап в одном удобном месте.|Адреса для покупок у Великій Британії, фотозвіт і доставка в Україну — кожен етап в одному зручному місці.|A UK shopping address, photo reports and delivery to Ukraine. Every step in one place.
Начать доставку|Почати доставку|Start shipping
Мини-тур|Мінітур|Quick tour
Всё прозрачно|Усе прозоро|Every step in view
от покупки до получения|від покупки до отримання|from checkout to your doorstep
ТВОЙ МАРШРУТ|ТВІЙ МАРШРУТ|YOUR ROUTE
Покупка|Покупка|Purchase
Твой адрес|Твоя адреса|Your address
СЕРВИС|СЕРВІС|SERVICE
Под твоим контролем|Під твоїм контролем|You're in control
Фото|Фото|Photos
адрес для заказа|адреса для замовлення|shopping address
перед отправкой|перед відправленням|before dispatch
статус в кабинете|статус у кабінеті|status in your account
Удобно с первого клика|Зручно з першого кліку|Easy from the first click
ПРОСТОЙ ПУТЬ · 4 ШАГА|ПРОСТИЙ ШЛЯХ · 4 КРОКИ|ONE ROUTE · FOUR STEPS
Путь посылки —|Шлях посилки —|Your parcel's journey —
без сюрпризов.|без сюрпризів.|without surprises.
Ты знаешь, что происходит, на каждом этапе.|Ти знаєш, що відбувається на кожному етапі.|Know what's happening at every step.
01 / ЗАКАЖИ|01 / ЗАМОВ|01 / SHOP
02 / ОФОРМИ|02 / ОФОРМИ|02 / REGISTER
03 / ПРОВЕРЬ|03 / ПЕРЕВІР|03 / REVIEW
04 / ПОЛУЧИ|04 / ОТРИМАЙ|04 / RECEIVE
Укажи наш адрес|Укажи нашу адресу|Use our address
Выбери удобный способ доставки по Великобритании и оформи покупку.|Обери зручний спосіб доставки у Великій Британії та оформи покупку.|Choose a UK delivery option and place your order.
Добавь посылку|Додай посилку|Add your parcel
Когда заказ получит статус Shipped, прикрепи скрин покупки и фото вещи.|Коли замовлення отримає статус Shipped, додай скриншот покупки та фото речі.|Once the order is Shipped, upload the purchase screenshot and an item photo.
Посмотри фотоотчёт|Переглянь фотозвіт|Review the photos
Мы примем вещь, сфотографируем её и дождёмся твоего решения.|Ми отримаємо річ, сфотографуємо її та дочекаємося твого рішення.|We'll receive your item, take photos and wait for your decision.
Следи за доставкой|Стеж за доставкою|Follow the delivery
Получай трек общей отправки и отслеживай путь до своего отделения.|Отримай трек спільного відправлення та відстежуй шлях до свого відділення.|Get your shipment's tracking number and follow it to your pickup point.
READY WHEN YOU ARE|ГОТОВІ, КОЛИ ГОТОВИЙ ТИ|READY WHEN YOU ARE
Следующая покупка|Наступна покупка|Your next find
уже ждёт|вже чекає|is waiting
в UK.|у UK.|in the UK.
Создать аккаунт|Створити акаунт|Create account
ТВОЙ КАБИНЕТ · MOPS PARCEL|ТВІЙ КАБІНЕТ · MOPS PARCEL|YOUR ACCOUNT · MOPS PARCEL
Снова|Знову|Welcome
на связи.|на зв'язку.|back.
Проверь статус, фотоотчёт и трек-номер своих посылок.|Перевір статус, фотозвіт і трек-номер своїх посилок.|Check your parcels' status, photos and tracking.
YOUR PARCEL, IN VIEW|ТВОЯ ПОСИЛКА ПІД КОНТРОЛЕМ|YOUR PARCEL, IN VIEW
РАДЫ ВИДЕТЬ|РАДІ БАЧИТИ|GOOD TO SEE YOU
Вход в аккаунт|Вхід в акаунт|Sign in to your account
Электронная почта|Електронна пошта|Email address
Пароль|Пароль|Password
Нет аккаунта?|Немає акаунта?|New here?
Подать заявку|Подати заявку|Request access
MOPS PARCEL · ДОСТАВКА ИЗ UK|MOPS PARCEL · ДОСТАВКА З UK|MOPS PARCEL · DELIVERY FROM THE UK
Свой маршрут|Твій маршрут|Your journey
начинается здесь.|починається тут.|starts here.
После регистрации администратор подтвердит доступ к личному кабинету.|Після реєстрації адміністратор підтвердить доступ до особистого кабінету.|An administrator will approve your account after registration.
НОВЫЙ АККАУНТ|НОВИЙ АКАУНТ|NEW ACCOUNT
Регистрация|Реєстрація|Register
Имя и фамилия|Ім'я та прізвище|Full name
Например, Анна Иванова|Наприклад, Анна Іванова|For example, Anna Smith
Не менее 8 символов|Щонайменше 8 символів|At least 8 characters
Telegram username|Ім'я користувача Telegram|Telegram username
Отправить заявку|Надіслати заявку|Submit request
Уже есть аккаунт?|Уже маєш акаунт?|Already have an account?
ДОСТУП НА ПРОВЕРКЕ|ДОСТУП НА ПЕРЕВІРЦІ|ACCESS UNDER REVIEW
Почти готово.|Майже готово.|Almost there.
Администратор проверит заявку на регистрацию. Как только доступ будет открыт, ты сможешь оформить посылку.|Адміністратор перевірить заявку на реєстрацію. Щойно доступ буде відкрито, ти зможеш оформити посилку.|An administrator will review your registration. Once approved, you can add a parcel.
Подключить Telegram ↗|Підключити Telegram ↗|Connect Telegram ↗
ЛИЧНЫЙ КАБИНЕТ · ДОБРО ПОЖАЛОВАТЬ,|ОСОБИСТИЙ КАБІНЕТ · ВІТАЄМО,|YOUR ACCOUNT · WELCOME,
Твои|Твої|Your
посылки.|посилки.|parcels.
Добавить посылку|Додати посилку|Add parcel
Получай уведомления о статусе прямо в Telegram|Отримуй сповіщення про статус прямо в Telegram|Get status updates in Telegram
БОНУСНЫЙ БАЛАНС|БОНУСНИЙ БАЛАНС|BONUS BALANCE
В процессе|У процесі|In progress
Отклонено|Відхилено|Rejected
Одержано|Отримано|Received
Фотоотчёт готов|Фотозвіт готовий|Photo report ready
К отправке|До відправлення|Ready to dispatch
Отправлено|Відправлено|Shipped
Доставлено|Доставлено|Delivered
Архив|Архів|Archive
На складе|На складі|At warehouse
В пути|У дорозі|In transit
СПОСОБ|СПОСІБ|DELIVERY
К ОПЛАТЕ|ДО СПЛАТИ|AMOUNT DUE
ТРЕК ОБЩЕЙ ПОСЫЛКИ|ТРЕК СПІЛЬНОЇ ПОСИЛКИ|SHIPMENT TRACKING
ФОТООТЧЁТ|ФОТОЗВІТ|PHOTO REPORT
Открыть фото ↗|Відкрити фото ↗|View photos ↗
У вас есть 2 дня, чтобы запросить возврат или дополнительные фото.|У вас є 2 дні, щоб запросити повернення або додаткові фото.|You have 2 days to request a return or additional photos.
Фотоотчёт принят|Фотозвіт прийнято|Photo report accepted
Запрошен возврат|Запитано повернення|Return requested
Запрошены дополнительные фото|Запитано додаткові фото|Additional photos requested
Согласиться · отправить|Погодитися · відправити|Approve · dispatch
Попросить фото|Запросити фото|Request photos
Запросить возврат|Запросити повернення|Request a return
Изменить данные|Змінити дані|Edit details
Новый телефон|Новий телефон|New phone number
Способ доставки|Спосіб доставки|Delivery method
Новое отделение|Нове відділення|New pickup point
Отправить запрос|Надіслати запит|Send request
Запросить другой способ оплаты ↗|Запросити інший спосіб оплати ↗|Request another payment method ↗
ТВОЙ ПУТЬ НАЧИНАЕТСЯ|ТВІЙ ШЛЯХ ПОЧИНАЄТЬСЯ|YOUR JOURNEY STARTS HERE
Здесь появится первая посылка.|Тут з'явиться перша посилка.|Your first parcel will appear here.
Добавь вещь после того, как продавец отправит её и заказ получит статус Shipped.|Додай річ після того, як продавець відправить її та замовлення отримає статус Shipped.|Add an item once the seller ships it and the order status is Shipped.
ОСТАВЬ ОТЗЫВ · ПОЛУЧИ БОНУС|ЗАЛИШ ВІДГУК · ОТРИМАЙ БОНУС|LEAVE A REVIEW · GET A BONUS
Твоё мнение —|Твоя думка —|Your feedback,
бонус тебе.|бонус тобі.|your reward.
Опубликуй отзыв в ветке сообщества, затем пришли скриншот публикации на проверку.|Опублікуй відгук у гілці спільноти, а потім надішли скриншот публікації на перевірку.|Post a review in the community thread, then upload a screenshot for approval.
Открыть ветку в Telegram ↗|Відкрити гілку в Telegram ↗|Open Telegram thread ↗
Прикрепить скриншот|Додати скриншот|Attach screenshot
Отправить на проверку ↗|Надіслати на перевірку ↗|Submit for review ↗
Ожидает проверки|Очікує перевірки|Awaiting review
Бонус подтверждён|Бонус підтверджено|Bonus approved
Архив ·|Архів ·|Archive ·
← Мои посылки|← Мої посилки|← My parcels
НОВАЯ ЗАЯВКА · UK → UA|НОВА ЗАЯВКА · UK → UA|NEW PARCEL · UK → UA
Добавь|Додай|Add
покупку.|покупку.|your purchase.
Создавай заявку только после того, как заказ получит статус|Створюй заявку лише після того, як замовлення отримає статус|Submit a parcel only after the order status changes to
. Заявки без подтверждения отправки администратор отклонит.|. Заявки без підтвердження відправлення адміністратор відхилить.|. Requests without proof of dispatch will be rejected.
Название вещи|Назва речі|Item name
Например, куртка vintage|Наприклад, вінтажна куртка|For example, a vintage jacket
Телефон|Телефон|Phone number
Выберите вариант|Оберіть варіант|Choose an option
Домашняя доставка|Доставка додому|Home delivery
InPost locker|Поштомат InPost|InPost locker
Evri пункт выдачи|Пункт видачі Evri|Evri pickup point
Royal Mail отделение|Відділення Royal Mail|Royal Mail branch
Другой|Інший|Other
Пункт выдачи / отделение|Пункт видачі / відділення|Pickup point / branch
Город, адрес или номер пункта|Місто, адреса або номер пункту|City, address or pickup point number
@username или chat ID|@username|@username
01 · СКРИН ПОКУПКИ|01 · СКРИНШОТ ПОКУПКИ|01 · PURCHASE SCREENSHOT
На изображении должен быть виден статус Shipped.|На зображенні має бути видно статус Shipped.|The Shipped status must be visible in the screenshot.
02 · ФОТО ВЕЩИ|02 · ФОТО РЕЧІ|02 · ITEM PHOTO
Фото товара, который выкуплен.|Фото придбаного товару.|A photo of the item you purchased.
Подтверждаю, что заказ отмечен как Shipped.|Підтверджую, що замовлення має статус Shipped.|I confirm that the order is marked Shipped.
Отправить заявку на проверку|Надіслати заявку на перевірку|Submit parcel for review
MOPS PARCEL · УПРАВЛЕНИЕ|MOPS PARCEL · КЕРУВАННЯ|MOPS PARCEL · MANAGEMENT
Админ-|Адмін-|Admin
панель.|панель.|dashboard.
● ADMIN ACCESS|● ДОСТУП АДМІНІСТРАТОРА|● ADMIN ACCESS
Доступы|Доступи|Access
Посылки|Посилки|Parcels
Запросы|Запити|Requests
Отзывы|Відгуки|Reviews
Настройки|Налаштування|Settings
01 · АККАУНТЫ|01 · АКАУНТИ|01 · ACCOUNTS
Заявки на доступ|Заявки на доступ|Access requests
Доступ открыт|Доступ відкрито|Access granted
Подтвердить доступ ↗|Підтвердити доступ ↗|Approve access ↗
Новых заявок нет.|Нових заявок немає.|No new requests.
02 · ЛОГИСТИКА|02 · ЛОГІСТИКА|02 · LOGISTICS
Все посылки|Усі посилки|All parcels
Решение клиента:|Рішення клієнта:|Client's decision:
Скрин покупки ↗|Скриншот покупки ↗|Purchase screenshot ↗
Фото вещи ↗|Фото речі ↗|Item photo ↗
Фотоотчёт ↗|Фотозвіт ↗|Photo report ↗
Статус|Статус|Status
Счёт, ₴|Рахунок, ₴|Invoice, ₴
Например, 450|Наприклад, 450|For example, 450
Трек-номер|Трек-номер|Tracking number
Фотоотчёт|Фотозвіт|Photo report
Сохранить ↗|Зберегти ↗|Save ↗
Заявок пока нет.|Заявок поки немає.|No parcels yet.
03 · ОБРАЩЕНИЯ|03 · ЗВЕРНЕННЯ|03 · REQUESTS
Запросы клиентов|Запити клієнтів|Client requests
Изменение · MP|Зміна · MP|Change · MP
Одобрить|Схвалити|Approve
Отклонить|Відхилити|Reject
Оплата · MP|Оплата · MP|Payment · MP
Ответ клиенту|Відповідь клієнту|Reply to client
Ответить|Відповісти|Reply
Ожидающих запросов нет.|Немає запитів, що очікують відповіді.|No pending requests.
04 · БОНУСЫ|04 · БОНУСИ|04 · BONUSES
Отзывы на проверку|Відгуки на перевірку|Reviews to approve
Скриншот отзыва ↗|Скриншот відгуку ↗|Review screenshot ↗
Подтвердить бонус|Підтвердити бонус|Approve bonus
Отзывов пока нет.|Відгуків поки немає.|No reviews yet.
05 · НАСТРОЙКА СЕРВИСА|05 · НАЛАШТУВАННЯ СЕРВІСУ|05 · SERVICE SETTINGS
Адреса и оплата|Адреси та оплата|Addresses and payment
Эти данные видны клиентам в форме подачи заявки.|Ці дані клієнти бачать у формі подання заявки.|Clients see these details when adding a parcel.
Home delivery|Доставка додому|Home delivery
Другие способы|Інші способи|Other methods
Карта для оплаты|Картка для оплати|Payment card
Укажите адрес / реквизиты|Укажіть адресу / реквізити|Enter an address / payment details
Сохранить настройки ↗|Зберегти налаштування ↗|Save settings ↗
MOPS PARCEL · МИНИ-ТУР|MOPS PARCEL · МІНІТУР|MOPS PARCEL · QUICK TOUR
Закрыть|Закрити|Close
Покупка отправлена|Покупку відправлено|Purchase shipped
Когда продавец отметит заказ как Shipped, создай заявку с подтверждением покупки и фото вещи.|Коли продавець позначить замовлення як Shipped, створи заявку зі скриншотом покупки та фото речі.|Once the seller marks your order Shipped, add a parcel with proof of purchase and an item photo.
Назад|Назад|Back
Далее ↗|Далі ↗|Next ↗
Готово ✓|Готово ✓|Done ✓
Из Великобритании — домой.|З Великої Британії — додому.|From the UK to your door.
Быстрая связь|Швидкий зв'язок|Get in touch
Мы на связи в Telegram|Ми на зв'язку в Telegram|Find us on Telegram
Отправки по Украине|Відправлення Україною|Deliveries within Ukraine
Менеджер по отправкам в Украине|Менеджер з відправлень Україною|Ukraine dispatch manager
Через администратора|Через адміністратора|Via the administrator
Администратор|Адміністратор|Administrator
Техническая поддержка|Технічна підтримка|Technical support
Открыть Telegram|Відкрити Telegram|Open Telegram
Твой дроп. Наш маршрут.|Твій дроп. Наш маршрут.|Your drop. Our route.
Лучшие находки · MOPS · Быстрая доставка · Выгодные цены · Быстрый ответ|Найкращі знахідки · MOPS · Швидка доставка · Вигідні ціни · Швидка відповідь|BEST DROP · MOPS · FAST DELIVERY · CHEAP PRICING · QUICK RESPONSE
Адрес для выкупа:|Адреса для покупок:|UK shopping address:
Адрес ещё не указан. Напишите администратору.|Адресу ще не вказано. Напишіть адміністратору.|This address hasn't been set. Contact the administrator.
Выбрать файл|Обрати файл|Choose file
Файл не выбран|Файл не обрано|No file selected
Заполните это поле.|Заповніть це поле.|Please fill in this field.
Введите корректный email.|Введіть коректний email.|Enter a valid email address.
Используйте не менее 8 символов.|Використовуйте щонайменше 8 символів.|Use at least 8 characters.
Подтвердите это условие.|Підтвердьте цю умову.|Please confirm this requirement.
Прикрепите обязательное фото.|Додайте обов'язкове фото.|Attach the required photo.
Формат: JPG, PNG или WEBP.|Формат: JPG, PNG або WEBP.|Accepted formats: JPG, PNG or WEBP.
Проверьте имя, почту и пароль (не менее 8 символов).|Перевірте ім'я, пошту та пароль (щонайменше 8 символів).|Check your name, email and password (at least 8 characters).
Заявка отправлена администратору.|Заявку надіслано адміністратору.|Your request has been sent to the administrator.
Пользователь с такой почтой уже есть.|Користувач із такою поштою вже існує.|An account with that email already exists.
Неверная почта или пароль.|Неправильна пошта або пароль.|Incorrect email or password.
Заполните все поля и укажите пункт выдачи.|Заповніть усі поля та вкажіть пункт видачі.|Complete all fields and specify a pickup point.
Заявка создана и ожидает проверки статуса Shipped.|Заявку створено. Вона очікує перевірки статусу Shipped.|Your parcel has been registered and is awaiting verification of its Shipped status.
Укажите новые данные.|Укажіть нові дані.|Enter the new details.
Запрос изменения отправлен администратору.|Запит на зміну надіслано адміністратору.|Your change request has been sent to the administrator.
Запрос отправлен администратору.|Запит надіслано адміністратору.|Your request has been sent to the administrator.
Скрин отзыва отправлен на проверку бонуса.|Скриншот відгуку надіслано на перевірку бонусу.|Your review screenshot has been submitted for bonus approval.
Решение отправлено администратору.|Рішення надіслано адміністратору.|Your decision has been sent to the administrator.
Настройки адресов и оплаты сохранены.|Налаштування адрес і оплати збережено.|Address and payment settings saved.
Ответ отправлен.|Відповідь надіслано.|Reply sent.
Бонус за отзыв подтверждён.|Бонус за відгук підтверджено.|Review bonus approved.
Файл слишком большой (лимит 12 МБ).|Файл завеликий (ліміт 12 МБ).|The file is too large (12 MB limit).
Запрос подтверждено.|Запит підтверджено.|Request approved.
Запрос отклонено.|Запит відхилено.|Request rejected.
Доступ подтверждён: {email}|Доступ підтверджено: {email}|Access approved: {email}
Заявка #{id} обновлена.|Заявку #{id} оновлено.|Parcel #{id} updated.
Ожидает подтверждения|Очікує підтвердження|Awaiting approval
Ожидает ответа|Очікує відповіді|Awaiting reply
Ответ отправлен|Відповідь надіслано|Reply sent
Подтверждено|Підтверджено|Approved
Нужен другой способ оплаты|Потрібен інший спосіб оплати|Another payment method requested
Страница не найдена|Сторінку не знайдено|Page not found
Недостаточно прав|Недостатньо прав|Access denied
Действие недоступно|Дія недоступна|Action unavailable
Срок ответа истёк|Термін відповіді минув|Response window expired
Обратитесь в поддержку или вернитесь в кабинет.|Зверніться до підтримки або поверніться до кабінету.|Contact support or return to your account.
Вернуться на главную|Повернутися на головну|Back to home
Не удалось выполнить запрос|Не вдалося виконати запит|The request could not be completed
Дополнительные фото|Додаткові фото|Additional photos
Посылка принята|Посилку отримано|Parcel received
Администратор отметит получение и приложит фотоотчёт к заявке.|Адміністратор позначить отримання та додасть фотозвіт до заявки.|The administrator will confirm receipt and attach a photo report.
Проверь фотоотчёт|Перевір фотозвіт|Review the photos
В течение двух дней можно запросить возврат или дополнительные фото.|Протягом двох днів можна запросити повернення або додаткові фото.|You have two days to request a return or more photos.
Доставлено!|Доставлено!|Delivered!
После отправки появится общий трек-номер. Следи за посылкой в личном кабинете.|Після відправлення з'явиться спільний трек-номер. Стеж за посилкою в особистому кабінеті.|After dispatch, your shipment tracking number will appear in your account.
Дождись статуса Shipped, затем добавь скрин покупки и фото вещи.|Дочекайся статусу Shipped, а потім додай скриншот покупки та фото речі.|Wait for the Shipped status, then upload the purchase screenshot and item photo.
phone|Телефон|Phone
delivery|Спосіб доставки|Delivery method
branch|Відділення|Pickup point
telegram|Telegram|Telegram
"""
CATALOG = {}
for line in ROWS.strip().splitlines():
    source, uk, en = line.split("|")
    CATALOG[source] = {"ru": source, "uk": uk, "en": en}
CATALOG["phone"]["ru"]="Телефон"
CATALOG["delivery"]["ru"]="Способ доставки"
CATALOG["branch"]["ru"]="Отделение"
CATALOG["telegram"]["ru"]="Telegram"
CATALOG["UK → UA · PERSONAL PARCEL SERVICE"]["ru"]="UK → UA · ПЕРСОНАЛЬНАЯ ДОСТАВКА"
CATALOG["READY WHEN YOU ARE"]["ru"]="ГОТОВЫ, КОГДА ГОТОВ ТЫ"
CATALOG["YOUR PARCEL, IN VIEW"]["ru"]="ТВОЯ ПОСЫЛКА ПОД КОНТРОЛЕМ"
CATALOG["● ADMIN ACCESS"]["ru"]="● ДОСТУП АДМИНИСТРАТОРА"
CATALOG["● LIVE"]={"ru":"● В РЕАЛЬНОМ ВРЕМЕНИ","uk":"● У РЕАЛЬНОМУ ЧАСІ","en":"● LIVE"}
CATALOG["Запрос подтверждено."]["ru"]="Запрос подтверждён."
CATALOG["Запрос отклонено."]["ru"]="Запрос отклонён."
CATALOG["@username или chat ID"]["ru"]="@username"

CATALOG["Home delivery"]["ru"]="Доставка на дом"
CATALOG["InPost locker"]["ru"]="Локер InPost"
CATALOG["Telegram username"]["ru"]="Имя пользователя Telegram"
CATALOG["Например, куртка vintage"]["ru"]="Например, винтажная куртка"
CATALOG["Одержано"]["ru"]="Получено"
CATALOG["Админ-"]["en"]="Admin "

def t(text, language=None, **values):
    if not isinstance(text, str):
        return text
    lang = language or (getattr(g, "lang", "ru") if has_request_context() else "ru")
    row=CATALOG.get(text)
    if row:
        translated=row.get(lang,row["ru"])
        return translated.format(**values) if values else translated
    for pattern, key in (
        (r"Доступ подтверждён: (.+)", "Доступ подтверждён: {email}"),
        (r"Заявка #(\d+) обновлена\.", "Заявка #{id} обновлена."),
    ):
        match=re.fullmatch(pattern,text)
        if match:
            field="email" if "{email}" in key else "id"
            return t(key,lang,**{field:match.group(1)})
    return text
