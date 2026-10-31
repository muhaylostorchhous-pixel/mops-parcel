"""Translations for profiles, billing, bot commands and guided onboarding."""
ROWS = '''
ua_name|ФИО получателя|ПІБ отримувача|Recipient name
ua_phone|Телефон получателя|Телефон отримувача|Recipient phone
ua_city|Город в Украине|Місто в Україні|City in Ukraine
ua_branch|Отделение Новой почты|Відділення Нової пошти|Nova Poshta branch
bot.change_request|Запрос изменения данных заявки #{id}. Проверьте его в панели администратора.|Запит зміни даних заявки №{id}. Перевірте його в панелі адміністратора.|Requested changes for parcel #{id}. Review them in the admin dashboard.
bot.change_result|Заявка #{id}: изменение данных — {status}.|Заявка №{id}: зміна даних — {status}.|Parcel #{id}: requested changes — {status}.
bot.payment_response|Оплата заявки #{id}: {message}|Оплата заявки №{id}: {message}|Payment for parcel #{id}: {message}

profile.title|Профиль|Профіль|Profile
profile.intro|Твои данные и адреса доставки в одном месте.|Твої дані та адреси доставки в одному місці.|Your details and delivery addresses in one place.
profile.personal|Личные данные|Особисті дані|Personal details
profile.fullname|ФИО получателя|ПІБ отримувача|Recipient's full name
profile.save|Сохранить профиль|Зберегти профіль|Save profile
profile.saved|Профиль сохранён.|Профіль збережено.|Profile saved.
profile.completed|Доставлено вещей|Доставлено речей|Items delivered
profile.rank|Ранг|Ранг|Rank
profile.bonus|Бонусы|Бонуси|Bonuses
profile.public|Показывать мой Telegram username в таблице лидеров|Показувати моє ім'я користувача Telegram у таблиці лідерів|Show my Telegram username on the leaderboard
profile.privacy|Без этой отметки в рейтинге будет только номер клиента.|Без цієї позначки в рейтингу буде лише номер клієнта.|Otherwise the leaderboard shows only your customer number.
profile.pending|Доступ к заявкам откроется после подтверждения администратором. Пока можно заполнить профиль и адрес.|Доступ до заявок відкриється після підтвердження адміністратором. Поки можна заповнити профіль та адресу.|Parcel registration opens after administrator approval. You can complete your profile and address now.
address.ua|Доставка по Украине|Доставка Україною|Delivery within Ukraine
address.add|Добавить адрес|Додати адресу|Add address
address.saved|Адрес доставки сохранён.|Адресу доставки збережено.|Delivery address saved.
address.none|Добавь первый адрес: ФИО, телефон, город и отделение Новой почты.|Додай першу адресу: ПІБ, телефон, місто та відділення Нової пошти.|Add your first address: full name, phone, city and Nova Poshta branch.
address.city|Город|Місто|City
address.branch|Отделение Новой почты|Відділення Нової пошти|Nova Poshta branch
address.branch_hint|Номер и адрес отделения|Номер та адреса відділення|Branch number and address
address.choose|Адрес получателя|Адреса отримувача|Recipient address
address.new|Указать новый адрес|Указати нову адресу|Enter a new address
address.save|Сохранить адрес в профиле|Зберегти адресу в профілі|Save address to profile
address.uk|Адреса для покупок в Великобритании|Адреси для покупок у Великій Британії|UK shopping addresses
address.uk_help|Используй адрес выбранной службы при покупке. Эти адреса заполняет администратор.|Використовуй адресу обраної служби під час покупки. Ці адреси заповнює адміністратор.|Use the selected service's address at checkout. These addresses are provided by the administrator.
address.copy|Копировать|Копіювати|Copy
address.copied|Скопировано|Скопійовано|Copied
address.copy_failed|Выдели адрес и скопируй вручную.|Виділи адресу та скопіюй вручну.|Select the address and copy it manually.
address.uk_method|Доставка по Великобритании|Доставка Великою Британією|UK delivery method
address.uk_branch|Пункт выдачи в Великобритании, если нужен|Пункт видачі у Великій Британії, якщо потрібен|UK pickup point, if needed
prices.title|Доставка в Украину|Доставка в Україну|Delivery to Ukraine
prices.kicker|ПОНЯТНЫЙ ПРАЙС|ЗРОЗУМІЛІ ЦІНИ|SIMPLE PRICING
prices.note|Цена за одну вещь. Выбери категорию при оформлении заявки.|Ціна за одну річ. Обери категорію під час оформлення заявки.|Price per item. Choose a category when registering a parcel.
product.type|Вид товара|Вид товару|Item category
product.shoes_no_box|Обувь без коробки|Взуття без коробки|Shoes without a box
product.shoes_box|Обувь с коробкой|Взуття з коробкою|Shoes with a box
product.outerwear|Кофта / куртка / штаны|Кофта / куртка / штани|Sweatshirt / jacket / trousers
product.small|Футболка / небольшой груз / шорты|Футболка / невеликий вантаж / шорти|T-shirt / small item / shorts
product.total|Стоимость доставки|Вартість доставки|Delivery price
payment.pay|Оплатить|Сплатити|Pay
payment.title|Оплата доставки|Оплата доставки|Delivery payment
payment.invoice|Счёт за доставку|Рахунок за доставку|Delivery invoice
payment.instruction|Переведи указанную сумму по реквизитам и прикрепи два подтверждения. Оплата засчитывается после проверки администратором.|Перекажи вказану суму за реквізитами та додай два підтвердження. Оплата зараховується після перевірки адміністратором.|Transfer the stated amount using the payment details and attach both documents. Payment is confirmed after administrator review.
payment.card|Реквизиты для перевода|Реквізити для переказу|Transfer details
payment.ask_admin|Уточните реквизиты у администратора.|Уточніть реквізити в адміністратора.|Ask the administrator for payment details.
payment.screenshot|Скриншот перевода|Скриншот переказу|Transfer screenshot
payment.receipt|Квитанция банка|Квитанція банку|Bank receipt
payment.receipt_hint|PDF, JPG, PNG или WEBP. До 12 МБ на файл.|PDF, JPG, PNG або WEBP. До 12 МБ на файл.|PDF, JPG, PNG or WEBP. Up to 12 MB per file.
payment.submit|Отправить платёж на проверку|Надіслати платіж на перевірку|Submit payment for review
payment.submitted|Подтверждения отправлены. Ожидайте проверки оплаты.|Підтвердження надіслано. Очікуйте перевірки оплати.|Evidence submitted. Your payment is awaiting review.
payment.pending|Оплата на проверке|Оплата на перевірці|Payment under review
payment.paid|Оплата подтверждена|Оплату підтверджено|Payment confirmed
payment.rejected|Платёж отклонён — отправьте новые подтверждения.|Платіж відхилено — надішліть нові підтвердження.|Payment rejected — submit new evidence.
payment.unpaid|Не оплачено|Не сплачено|Unpaid
payment.review|Проверка платежей|Перевірка платежів|Payment review
payment.approve|Подтвердить оплату|Підтвердити оплату|Confirm payment
payment.reject|Отклонить платёж|Відхилити платіж|Reject payment
payment.reason|Причина отклонения|Причина відхилення|Rejection reason
payment.history|История подтверждений|Історія підтверджень|Submission history
payment.evidence_caption|Подтверждение оплаты · заявка #{id}|Підтвердження оплати · заявка №{id}|Payment evidence · parcel #{id}
file.telegram|Получить в Telegram|Отримати в Telegram|Receive in Telegram
file.item|Фото вещи в Telegram|Фото речі в Telegram|Item photo in Telegram
file.proof|Скрин покупки в Telegram|Скриншот покупки в Telegram|Purchase screenshot in Telegram
file.report|Фотоотчёт в Telegram|Фотозвіт у Telegram|Photo report in Telegram
file.sent|Файл отправлен в ваш Telegram.|Файл надіслано у ваш Telegram.|The file has been sent to your Telegram.
file.failed|Файл пока не отправлен. Проверьте подключение бота и повторите попытку.|Файл поки не надіслано. Перевірте підключення бота та спробуйте ще раз.|The file was not sent. Check the bot connection and try again.
file.link_first|Сначала подключите Telegram в профиле и нажмите Start в боте.|Спочатку підключіть Telegram у профілі та натисніть Start у боті.|Connect Telegram in your profile first and press Start in the bot.
file.caption|Заявка #{id} · {item}|Заявка №{id} · {item}|Parcel #{id} · {item}
file.explanation|Нажми кнопку — бот пришлёт изображение отдельным файлом.|Натисни кнопку — бот надішле зображення окремим файлом.|Press the button and the bot will send the image as a document.
file.connection|Telegram подключён|Telegram підключено|Telegram connected
file.not_configured|Подключение бота пока настраивается. Обратитесь в поддержку.|Підключення бота поки налаштовується. Зверніться до підтримки.|Bot connection is being configured. Contact support.
tracking.code|Номер посылки|Номер посилки|Parcel number
tracking.recipient|Получатель в Украине|Отримувач в Україні|Recipient in Ukraine
tracking.legacy|Для старого заказа адрес нужно уточнить у клиента.|Для старої заявки адресу потрібно уточнити в клієнта.|Confirm the recipient address for this legacy order.
rank.new|Новичок|Новачок|Newcomer
rank.regular|Обычный пользователь|Звичайний користувач|Regular user
rank.lower|Реселлер нижнего класса|Реселер початкового рівня|Junior reseller
rank.middle|Реселлер среднего класса|Реселер середнього рівня|Intermediate reseller
rank.cool|Крутой реселлер|Крутий реселер|Top reseller
rank.boss|Босс ресейла|Бос ресейлу|Resale boss
bot.open|Открыть Mops Parcel|Відкрити Mops Parcel|Open Mops Parcel
bot.welcome|Добро пожаловать в Mops Parcel! Оформление посылок происходит в мини-приложении. Открой его, зарегистрируйся, заполни профиль и дождись подтверждения администратора. Затем подключи Telegram кнопкой в профиле. Создавай заявку только после статуса Shipped.|Вітаємо в Mops Parcel! Оформлення посилок відбувається в мінізастосунку. Відкрий його, зареєструйся, заповни профіль та дочекайся підтвердження адміністратора. Потім підключи Telegram кнопкою в профілі. Створюй заявку лише після статусу Shipped.|Welcome to Mops Parcel! Register parcels in the mini app. Open it, create an account, complete your profile and wait for administrator approval. Then connect Telegram using the button in your profile. Only register a parcel once its status is Shipped.
bot.account|{name}, ваш профиль Mops Parcel. Доставлено вещей: {completed}. Бонусы: {bonus}. Ранг: {rank}.|{name}, ваш профіль Mops Parcel. Доставлено речей: {completed}. Бонуси: {bonus}. Ранг: {rank}.|{name}, your Mops Parcel profile. Items delivered: {completed}. Bonuses: {bonus}. Rank: {rank}.
bot.pending|Аккаунт ожидает подтверждения администратора.|Акаунт очікує підтвердження адміністратора.|Your account is awaiting administrator approval.
bot.help|/start — профиль и мини-приложение; /orders — посылки; /leaders — лидеры; /language — язык. Файлы запрашивайте кнопками в кабинете.|/start — профіль та мінізастосунок; /orders — посилки; /leaders — лідери; /language — мова. Файли запитуйте кнопками в кабінеті.|/start — profile and mini app; /orders — parcels; /leaders — leaderboard; /language — language. Request files using the buttons in your account.
bot.leaders|Лидеры|Лідери|Leaderboard
bot.leaders_title|Лидеры Mops Parcel · доставленные вещи|Лідери Mops Parcel · доставлені речі|Mops Parcel leaders · delivered items
bot.member|Клиент #{id}|Клієнт №{id}|Customer #{id}
bot.no_leaders|Первые завершённые доставки появятся здесь.|Перші завершені доставки з'являться тут.|The first completed deliveries will appear here.
bot.choose_language|Выберите язык бота.|Оберіть мову бота.|Choose the bot language.
bot.bad_link|Ссылка подключения недействительна или Telegram уже связан с другим аккаунтом. Откройте профиль на сайте.|Посилання підключення недійсне або Telegram уже пов'язано з іншим акаунтом. Відкрийте профіль на сайті.|This connection link is invalid or Telegram is already linked to another account. Open your profile on the site.
bot.new_account|Заявка на доступ: {name}, {email}.|Заявка на доступ: {name}, {email}.|Account access request: {name}, {email}.
bot.new_order|Новая заявка #{id}: {item}. Проверьте статус Shipped в подтверждении покупки.|Нова заявка №{id}: {item}. Перевірте статус Shipped у підтвердженні покупки.|New parcel #{id}: {item}. Check the Shipped status in the purchase screenshot.
bot.status|Mops Parcel · заявка #{id}: {item}. Статус: {status}. Номер: {code}.|Mops Parcel · заявка №{id}: {item}. Статус: {status}. Номер: {code}.|Mops Parcel · parcel #{id}: {item}. Status: {status}. Number: {code}.
bot.invoice|К оплате: {amount} ₴. Реквизиты: {card} Подтверждения перевода отправьте через кабинет.|До сплати: {amount} ₴. Реквізити: {card} Підтвердження переказу надішліть через кабінет.|Amount due: {amount} ₴. Payment details: {card} Submit transfer evidence in your account.
bot.report_file|Фотоотчёт · #{id} · {item}. На возврат или запрос фото есть 2 дня.|Фотозвіт · №{id} · {item}. На повернення або запит фото є 2 дні.|Photo report · #{id} · {item}. You have 2 days to request a return or more photos.
bot.payment_review|Проверьте оплату заявки #{id}: {item}. Оба документа доступны в админ-панели.|Перевірте оплату заявки №{id}: {item}. Обидва документи доступні в панелі адміністратора.|Review payment for parcel #{id}: {item}. Both documents are available in the admin dashboard.
bot.payment_paid|Оплата заявки #{id} подтверждена.|Оплату заявки №{id} підтверджено.|Payment for parcel #{id} confirmed.
bot.payment_rejected|Оплата заявки #{id} отклонена. Причина: {reason}|Оплату заявки №{id} відхилено. Причина: {reason}|Payment for parcel #{id} rejected. Reason: {reason}
bot.approved|Доступ к Mops Parcel подтверждён. Можно оформить первую посылку.|Доступ до Mops Parcel підтверджено. Можна оформити першу посилку.|Your Mops Parcel account is approved. You can register your first parcel.
bot.bonus|Отзыв проверен, бонус начислен. Спасибо!|Відгук перевірено, бонус нараховано. Дякуємо!|Your review is approved and your bonus has been added. Thank you!
error.telegram|Укажите корректный Telegram username без пробелов.|Укажіть коректне ім'я користувача Telegram без пробілів.|Enter a valid Telegram username without spaces.
error.phone|Укажите корректный номер телефона.|Укажіть коректний номер телефону.|Enter a valid phone number.
error.profile|Проверьте ФИО и email.|Перевірте ПІБ та email.|Check your full name and email.
error.address|Заполните ФИО, телефон, город и отделение Новой почты.|Заповніть ПІБ, телефон, місто та відділення Нової пошти.|Enter the full name, phone, city and Nova Poshta branch.
error.product|Обязательно выберите вид товара.|Обов'язково оберіть вид товару.|You must select an item category.
error.required|Заполните обязательные поля.|Заповніть обов'язкові поля.|Complete the required fields.
error.shipped|Подтвердите, что заказ получил статус Shipped.|Підтвердьте, що замовлення отримало статус Shipped.|Confirm that your order is marked Shipped.
error.evidence|Прикрепите скриншот перевода и квитанцию банка.|Додайте скриншот переказу та квитанцію банку.|Attach both a transfer screenshot and a bank receipt.
error.same_evidence|Скрин перевода и квитанция должны быть разными документами.|Скриншот переказу та квитанція мають бути різними документами.|The transfer screenshot and receipt must be different documents.
error.filetype|Файл повреждён или имеет неподдерживаемый формат.|Файл пошкоджений або має непідтримуваний формат.|The file is damaged or has an unsupported format.
error.filesize|Лимит одного файла — 12 МБ.|Ліміт одного файлу — 12 МБ.|Each file must be no larger than 12 MB.
error.amount|Сумма должна быть положительным целым числом.|Сума має бути додатним цілим числом.|The amount must be a positive whole number.
error.locked_amount|Нельзя менять сумму платежа на проверке или после подтверждения.|Не можна змінювати суму платежу на перевірці або після підтвердження.|You cannot change a payment amount while under review or after approval.
error.unpaid|Сначала подтвердите оплату этой посылки.|Спочатку підтвердьте оплату цієї посилки.|Confirm this parcel's payment before dispatch.
error.report|Сначала прикрепите фотоотчёт.|Спочатку додайте фотозвіт.|Attach the photo report first.
error.reason|Укажите причину отклонения платежа.|Укажіть причину відхилення платежу.|Enter the reason for rejecting the payment.
tutorial.open|Обучение|Навчання|Tutorial
tutorial.title|Первый шаг — твой профиль|Перший крок — твій профіль|Start with your profile
tutorial.name|Укажи ФИО получателя. Эти данные понадобятся для доставки.|Укажи ПІБ отримувача. Ці дані знадобляться для доставки.|Enter the recipient's full name. It will be used for delivery.
tutorial.phone|Добавь телефон и Telegram username для связи.|Додай телефон та ім'я користувача Telegram для зв'язку.|Add a phone number and Telegram username so we can contact you.
tutorial.address|Сохрани ФИО, телефон, город и отделение Новой почты. Затем выбирай этот адрес в заявках.|Збережи ПІБ, телефон, місто та відділення Нової пошти. Потім обирай цю адресу в заявках.|Save your full name, phone, city and Nova Poshta branch, then select this address in future orders.
tutorial.uk|Здесь находятся британские адреса для покупок. Выбери нужную службу доставки.|Тут розміщені британські адреси для покупок. Обери потрібну службу доставки.|These are your UK shopping addresses. Choose the required delivery service.
tutorial.telegram|Подключи бота: он пришлёт уведомления и фотографии файлами.|Підключи бота: він надішле сповіщення та фотографії файлами.|Connect the bot to receive notifications and photos as documents.
tutorial.save|Сохрани профиль. После подтверждения аккаунта можно добавить посылку.|Збережи профіль. Після підтвердження акаунта можна додати посилку.|Save your profile. Once your account is approved, you can register a parcel.
tutorial.new|Эта кнопка открывает форму новой посылки.|Ця кнопка відкриває форму нової посилки.|This button opens a new parcel form.
tutorial.product|Выбери категорию. Стоимость доставки рассчитывается автоматически.|Обери категорію. Вартість доставки розраховується автоматично.|Choose a category. The delivery price is calculated automatically.
tutorial.proof|Добавь скрин со статусом Shipped и фото вещи.|Додай скриншот зі статусом Shipped та фото речі.|Add a screenshot showing Shipped and a photo of the item.
tutorial.payment|После фотоотчёта сверху появится счёт. Для проверки оплаты нужны скрин перевода и квитанция.|Після фотозвіту зверху з'явиться рахунок. Для перевірки оплати потрібні скриншот переказу та квитанція.|After the photo report, an invoice appears at the top. Submit a transfer screenshot and bank receipt for payment review.
tutorial.skip|Пропустить|Пропустити|Skip
tutorial.done|Понятно|Зрозуміло|Got it
'''
EXTRA={}
for row in ROWS.strip().splitlines():
    if not row.strip(): continue
    key,ru,uk,en=row.split('|')
    EXTRA[key]={'ru':ru,'uk':uk,'en':en}
