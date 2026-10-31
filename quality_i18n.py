"""Interface copy for the parcel workspace, in all supported languages."""
ROWS = '''
ux.overview|Всё под контролем|Усе під контролем|Everything in view
ux.active|В работе|У роботі|In progress
ux.payment|Ждут оплаты|Очікують оплати|Awaiting payment
ux.delivered|Доставлено|Доставлено|Delivered
ux.rank|Твой ранг|Твій ранг|Your rank
ux.search|Название, номер или трек|Назва, номер або трек|Item name, number or tracking
ux.all|Все посылки|Усі посилки|All parcels
ux.transit|В пути|У дорозі|In transit
ux.warehouse|На складе|На складі|At the warehouse
ux.empty|Ничего не найдено|Нічого не знайдено|No parcels found
ux.reset|Сбросить фильтры|Скинути фільтри|Clear filters
ux.details|Открыть посылку|Відкрити посилку|View parcel
ux.history|История посылки|Історія посилки|Parcel history
ux.created|Заявка создана|Заявку створено|Request created
ux.destination|Получатель в Украине|Одержувач в Україні|Recipient in Ukraine
ux.warehouse_address|Адрес при оформлении в UK|Адреса в UK під час оформлення|UK address at registration
ux.next|Следующий шаг|Наступний крок|Next step
ux.next_wait|Мы проверим заявку и отметим прибытие вещи на склад.|Ми перевіримо заявку та позначимо прибуття речі на склад.|We will review your request and record its arrival at the warehouse.
ux.next_return|Запрос на возврат передан администратору. Дальнейшие действия согласуем в поддержке.|Запит на повернення передано адміністратору. Подальші дії узгодимо в підтримці.|Your return request has been sent to the administrator. Contact support to arrange the next steps.
ux.next_photos|Ты запросил дополнительные фото. Ждём обновлённый фотоотчёт.|Ти запросив додаткові фото. Очікуємо оновлений фотозвіт.|You requested more photos. We are waiting for the updated photo report.
ux.next_received|Вещь на складе. Готовим фотоотчёт для тебя.|Річ на складі. Готуємо для тебе фотозвіт.|Your item is at the warehouse. We are preparing your photo report.
ux.next_report|Проверь фотоотчёт в Telegram и сообщи своё решение в кабинете.|Переглянь фотозвіт у Telegram і повідом своє рішення в кабінеті.|Check your photo report in Telegram and submit your decision in your account.
ux.next_pay|Прикрепи скриншот перевода и квитанцию. Администратор проверит платёж.|Додай скриншот переказу та квитанцію. Адміністратор перевірить платіж.|Upload the transfer screenshot and receipt for the administrator to review.
ux.next_review|Платёж на проверке. Повторно переводить деньги не нужно.|Платіж на перевірці. Повторно переказувати гроші не потрібно.|Your payment is being reviewed. You do not need to pay again.
ux.next_ready|Готовим посылку к отправке. Трек появится после оформления отправления.|Готуємо посилку до відправлення. Трек з’явиться після оформлення відправлення.|We are preparing your parcel. Tracking will appear after dispatch is arranged.
ux.next_transit|Посылка в пути. Следующее обновление придёт в Telegram, если бот подключён.|Посилка в дорозі. Наступне оновлення надійде в Telegram, якщо бота підключено.|Your parcel is on its way. The next update will arrive in Telegram if your bot is connected.
ux.next_done|Доставка завершена. Спасибо, что выбрал Mops Parcel.|Доставку завершено. Дякуємо, що обрав Mops Parcel.|Delivery complete. Thank you for choosing Mops Parcel.
ux.next_rejected|Заявка отклонена. Уточни причину в поддержке перед повторной подачей.|Заявку відхилено. Уточни причину в підтримці перед повторним поданням.|Your request was declined. Contact support before submitting again.
ux.deadline|Решение по фотоотчёту до|Рішення щодо фотозвіту до|Photo report decision by
ux.expired|Срок ответа на фотоотчёт истёк. Напиши в поддержку, чтобы согласовать следующий шаг.|Строк відповіді на фотозвіт минув. Напиши в підтримку, щоб узгодити наступний крок.|The photo report response window has ended. Contact support to arrange the next step.
ux.help|Вопрос по этой посылке|Питання щодо цієї посилки|Ask about this parcel
ux.support_draft|Здравствуйте! У меня вопрос по посылке #{id}: {item}.|Вітаю! Маю питання щодо посилки #{id}: {item}.|Hello! I have a question about parcel #{id}: {item}.
ux.summary|Твоя доставка|Твоя доставка|Your delivery
ux.summary_hint|Выбери категорию — стоимость рассчитается автоматически.|Обери категорію — вартість розрахується автоматично.|Choose a category to see your delivery price.
ux.file_hint|JPG, PNG или WebP · до 12 МБ на файл|JPG, PNG або WebP · до 12 МБ на файл|JPG, PNG or WebP · up to 12 MB per file
ux.file_large|Файл больше 12 МБ. Выберите файл меньшего размера.|Файл більший за 12 МБ. Оберіть менший файл.|This file exceeds 12 MB. Choose a smaller file.
ux.sending|Отправляем…|Надсилаємо…|Sending…
ux.show|Показать пароль|Показати пароль|Show password
ux.hide|Скрыть пароль|Приховати пароль|Hide password
ux.skip|Перейти к содержимому|Перейти до вмісту|Skip to content
ux.navigation|Основная навигация|Основна навігація|Main navigation
ux.new|Добавить|Додати|Add parcel
ux.orders|Посылки|Посилки|Parcels
ux.back|К посылкам|До посилок|Back to parcels
ux.archive|Архив|Архів|Archive
ux.connected|Telegram подключён|Telegram підключено|Telegram connected
ux.connected_hint|Обновления приходят в твой бот.|Оновлення надходять у твій бот.|Updates are sent to your bot.
ux.saved|Сохранено|Збережено|Saved
ux.no_address|Адрес не сохранён. Напиши в поддержку.|Адресу не збережено. Напиши в підтримку.|No address saved. Contact support.
ux.faq|Перед первой отправкой|Перед першим відправленням|Before your first delivery
ux.faq.shipped|Когда создавать заявку?|Коли створювати заявку?|When should I register a parcel?
ux.faq.shipped_a|Только после статуса Shipped у продавца. Нужны скриншот со статусом и фото вещи.|Лише після статусу Shipped у продавця. Потрібні скриншот зі статусом і фото речі.|Only after the seller marks the order as Shipped. Include a screenshot showing the status and a photo of the item.
ux.faq.pay|Когда оплачивать доставку?|Коли оплачувати доставку?|When do I pay for delivery?
ux.faq.pay_a|После фотоотчёта в кабинете появится счёт. Для проверки платежа нужны скриншот перевода и квитанция.|Після фотозвіту в кабінеті з’явиться рахунок. Для перевірки платежу потрібні скриншот переказу та квитанція.|An invoice appears in your account after the photo report. Submit both a transfer screenshot and a receipt for payment verification.
ux.faq.bot|Как получать уведомления?|Як отримувати сповіщення?|How do I get notifications?
ux.faq.bot_a|Войди в аккаунт, нажми «Подключить Telegram» и запусти бота по персональной ссылке.|Увійди в акаунт, натисни «Підключити Telegram» і запусти бота за персональним посиланням.|Sign in, select Connect Telegram and start the bot using your personal link.
ux.faq.report|Где посмотреть фотографии?|Де переглянути фотографії?|Where can I see my photos?
ux.faq.report_a|Открой посылку и нажми кнопку фотоотчёта. Бот отправит фотографии файлами в твой Telegram.|Відкрий посилку та натисни кнопку фотозвіту. Бот надішле фотографії файлами у твій Telegram.|Open your parcel and select the photo report button. The bot will send the photos as files to your Telegram.
ux.duplicate|Эта заявка уже отправлена. Открываем твои посылки.|Цю заявку вже надіслано. Відкриваємо твої посилки.|This request has already been submitted. Opening your parcels.
ux.session|Обнови страницу и попробуй ещё раз.|Онови сторінку та спробуй ще раз.|Refresh the page and try again.
'''
STRINGS = {key: dict(zip(('ru', 'uk', 'en'), values)) for key, *values in (line.split('|') for line in ROWS.strip().splitlines())}
