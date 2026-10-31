ROWS='''
svc.verify|Подтверждение почты|Підтвердження пошти|Verify your email
svc.verify_hint|Введите шестизначный код из письма. Он действует 10 минут.|Введіть шестизначний код із листа. Він діє 10 хвилин.|Enter the six-digit email code. It expires in 10 minutes.
svc.code|Код из письма|Код із листа|Email code
svc.confirm|Подтвердить|Підтвердити|Verify
svc.resend|Отправить код повторно|Надіслати код повторно|Resend code
svc.code_sent|Код отправлен. Проверьте также папку «Спам».|Код надіслано. Перевірте також папку «Спам».|Code sent. Please also check your spam folder.
svc.code_wrong|Неверный код. После 5 ошибок запросите новый.|Неправильний код. Після 5 помилок запитайте новий.|Incorrect code. Request a new one after 5 failed attempts.
svc.code_expired|Код истёк или исчерпаны попытки. Запросите новый.|Термін дії коду минув або вичерпано спроби. Запитайте новий.|Code expired or attempt limit reached. Request a new code.
svc.email_subject|Код подтверждения Mops Parcel|Код підтвердження Mops Parcel|Mops Parcel verification code
svc.email_body|Ваш код: {code}. Он действует 10 минут. Если вы не регистрировались, проигнорируйте письмо.|Ваш код: {code}. Він діє 10 хвилин. Якщо ви не реєструвалися, проігноруйте лист.|Your code: {code}. It expires in 10 minutes. If you did not register, ignore this email.
svc.invalid_registration|Проверьте имя, почту, Telegram и пароль (8–256 символов).|Перевірте ім’я, пошту, Telegram і пароль (8–256 символів).|Check your name, email, Telegram and password (8–256 characters).
svc.email_failed|Не удалось отправить код. Попробуйте позже или напишите в поддержку.|Не вдалося надіслати код. Спробуйте пізніше або напишіть у підтримку.|Could not send the code. Try later or contact support.
svc.rate_limit|Слишком много попыток. Подождите перед повторной отправкой.|Забагато спроб. Зачекайте перед повторним надсиланням.|Too many attempts. Please wait before trying again.
svc.email_exists|Эта почта уже зарегистрирована. Войдите в аккаунт.|Цю пошту вже зареєстровано. Увійдіть в акаунт.|This email is already registered. Sign in instead.
svc.verified_pending|Почта подтверждена. Заявка отправлена администратору.|Пошту підтверджено. Заявку надіслано адміністратору.|Email verified. Your account is awaiting administrator approval.
svc.email_locked|Для изменения почты обратитесь в поддержку.|Для зміни пошти зверніться в підтримку.|Contact support to change your email address.
svc.verified|Подтверждена|Підтверджена|Verified
svc.legacy|Существующий аккаунт|Наявний акаунт|Existing account
svc.unverified|Не подтверждена|Не підтверджена|Not verified
svc.support|Поддержка|Підтримка|Support
svc.support_intro|Напишите нам о посылке или работе сервиса.|Напишіть нам про посилку або роботу сервісу.|Ask us about your parcel or the service.
svc.inbox|Сообщения клиентов|Повідомлення клієнтів|Customer inbox
svc.choose_thread|Выберите диалог слева или откройте чат из списка пользователей.|Виберіть діалог ліворуч або відкрийте чат зі списку користувачів.|Select a conversation or open a chat from the user directory.
svc.message|Сообщение|Повідомлення|Message
svc.send|Отправить|Надіслати|Send
svc.sending|Отправка…|Надсилання…|Sending…
svc.connected|Сообщения обновляются автоматически|Повідомлення оновлюються автоматично|Messages refresh automatically
svc.chat_error|Нет связи. Текст сохранён в поле — попробуйте отправить снова.|Немає зв’язку. Текст збережено в полі — спробуйте надіслати ще раз.|Connection lost. Your draft is still in the field; try sending again.
svc.empty_chat|Сообщений пока нет. Начните разговор.|Повідомлень поки немає. Почніть розмову.|No messages yet. Start a conversation.
svc.bot_reply|Поддержка Mops Parcel ответила вам. Откройте раздел «Поддержка» в приложении.|Підтримка Mops Parcel відповіла вам. Відкрийте розділ «Підтримка» в застосунку.|Mops Parcel support replied. Open Support in the app.
svc.bot_support|Новое сообщение в поддержке от {name} (клиент #{id}). Откройте чат в панели администратора.|Нове повідомлення в підтримці від {name} (клієнт №{id}). Відкрийте чат у панелі адміністратора.|New support message from {name} (customer #{id}). Open the admin inbox.
svc.users|Все пользователи|Усі користувачі|All users
svc.search|Поиск по имени, почте или Telegram|Пошук за ім’ям, поштою або Telegram|Search name, email or Telegram
svc.role|Роль|Роль|Role
svc.admin|Администратор|Адміністратор|Administrator
svc.client|Клиент|Клієнт|Customer
svc.chat|Открыть чат|Відкрити чат|Open chat
svc.logs|Журнал действий|Журнал дій|Activity log
svc.storage_ok|Подключена постоянная PostgreSQL|Підключено постійну PostgreSQL|Persistent PostgreSQL connected
svc.storage_local|Локальная SQLite — только для запуска на компьютере|Локальна SQLite — лише для запуску на комп’ютері|Local SQLite — for running on your computer
svc.action|Действие|Дія|Action
svc.result|Результат|Результат|Result
svc.created|Дата|Дата|Date
svc.notifications|Очередь Telegram|Черга Telegram|Telegram queue
svc.retry|Повторить неудачные отправки|Повторити невдалі надсилання|Retry failed deliveries
svc.pending|Ожидает|Очікує|Pending
svc.sending_state|Отправляется|Надсилається|Sending
svc.failed|Не отправлено|Не надіслано|Failed
svc.link_telegram|Клиенту нужно подключить Telegram в профиле|Клієнту потрібно підключити Telegram у профілі|Customer needs to link Telegram in their profile
svc.configure_bot|Не настроен токен бота|Не налаштовано токен бота|Bot token is not configured
svc.telegram_delivery_failed|Telegram недоступен или бот заблокирован клиентом|Telegram недоступний або клієнт заблокував бота|Telegram is unavailable or the customer blocked the bot
svc.empty|Пока ничего нет|Поки нічого немає|Nothing here yet
svc.next|Далее|Далі|Next
svc.previous|Назад|Назад|Previous
svc.telegram_hint|Подключите Telegram, чтобы получать статусы посылок и ответы поддержки.|Підключіть Telegram, щоб отримувати статуси посилок і відповіді підтримки.|Link Telegram to receive parcel updates and support replies.
'''
STRINGS={}
for line in ROWS.strip().splitlines():
    key,ru,uk,en=line.split('|');STRINGS[key]={'ru':ru,'uk':uk,'en':en}
