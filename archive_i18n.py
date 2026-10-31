"""Photo report retention and Telegram archive UI copy."""
ROWS=r'''
arc.title|Архив фотоотчётов|Архів фотозвітів|Photo report archive
arc.intro|После доставки фотоотчёт удаляется из базы только после подтверждённого сохранения клиенту и в закрытый канал Telegram.|Після доставки фотозвіт видаляється з бази лише після підтвердженого збереження клієнту та в закритий канал Telegram.|After delivery, a report is removed from the database only after confirmed delivery to the client and a private Telegram channel.
arc.setup|Укажи TELEGRAM_ARCHIVE_CHAT_ID в ENV и добавь бота администратором закрытого канала с правом публикации.|Укажи TELEGRAM_ARCHIVE_CHAT_ID в ENV і додай бота адміністратором закритого каналу з правом публікації.|Set TELEGRAM_ARCHIVE_CHAT_ID in ENV and add the bot as an administrator of a private channel with permission to post.
arc.ready|Архив настроен. Доступ к каналу проверяется перед сохранением.|Архів налаштовано. Доступ до каналу перевіряється перед збереженням.|Archive configured. Channel access is checked before each archive operation.
arc.retry|Повторить обработку|Повторити обробку|Retry processing
arc.queued|Обработка запрошена. Статус обновится после выполнения.|Обробку запитано. Статус оновиться після виконання.|Processing requested. The status will update when it completes.
arc.pending|Ожидает обработки|Очікує обробки|Awaiting processing
arc.sending|Сохраняется в Telegram|Зберігається в Telegram|Saving to Telegram
arc.confirmed|Сохранён в Telegram · ждёт доставки|Збережено в Telegram · очікує доставки|Saved to Telegram · awaiting delivery
arc.cleaned|Файл удалён из базы · доступен в Telegram|Файл видалено з бази · доступний в Telegram|File removed from database · available in Telegram
arc.failed|Нужна проверка администратора|Потрібна перевірка адміністратора|Administrator review needed
arc.disabled|Архив не настроен. Фото остаются в базе.|Архів не налаштовано. Фото залишаються в базі.|Archive is not configured. Photos remain in the database.
arc.channel_invalid|Нужен закрытый канал без публичного username и без автоудаления сообщений.|Потрібен закритий канал без публічного username та без автовидалення повідомлень.|Use a private channel without a public username or message auto-deletion.
arc.telegram_failed|Telegram не подтвердил сохранение. Файл остаётся в базе.|Telegram не підтвердив збереження. Файл залишається в базі.|Telegram did not confirm storage. The file remains in the database.
arc.link_telegram|Клиент ещё не подключил Telegram. Файл остаётся в базе.|Клієнт ще не підключив Telegram. Файл залишається в базі.|The client has not linked Telegram. The file remains in the database.
arc.client_failed|Не удалось отправить файл клиенту. Файл остаётся в базе.|Не вдалося надіслати файл клієнту. Файл залишається в базі.|Could not deliver the file to the client. The file remains in the database.
arc.file_unavailable|Telegram не подтвердил доступ к файлу. Очистка остановлена.|Telegram не підтвердив доступ до файлу. Очищення зупинено.|Telegram did not confirm file access. Cleanup was stopped.
arc.bot_changed|Изменился бот или канал. Нужна повторная проверка архива.|Змінився бот або канал. Потрібна повторна перевірка архіву.|The bot or channel changed. The archive needs to be checked again.
arc.shared_file|Файл используется другой записью и не будет удалён.|Файл використовується іншим записом і не буде видалений.|Another record uses this file. It will not be removed.
arc.saved|Фотоотчёт сохранён в Telegram. Его можно получить кнопкой ниже.|Фотозвіт збережено в Telegram. Його можна отримати кнопкою нижче.|Your photo report is stored in Telegram. Use the button below to receive it.
arc.saved_bytes|Удалено из базы|Видалено з бази|Removed from database
arc.open|Открыть архив|Відкрити архів|Open archive
arc.caption|Mops Parcel · фотоотчёт #{id}\nВещь: {item}\nТрек: {code}|Mops Parcel · фотозвіт #{id}\nРіч: {item}\nТрек: {code}|Mops Parcel · photo report #{id}\nItem: {item}\nTracking: {code}
arc.id_hint|ID канала можно получить в боте командой /archiveid после пересылки сообщения из этого канала.|ID каналу можна отримати в боті командою /archiveid після пересилання повідомлення з цього каналу.|The channel ID is available to admins via /archiveid after forwarding a message from that channel.
arc.id_instructions|Перешли сюда сообщение из своего закрытого канала. Я покажу его ID для TELEGRAM_ARCHIVE_CHAT_ID. Не отправляй токен бота.|Перешли сюди повідомлення зі свого закритого каналу. Я покажу його ID для TELEGRAM_ARCHIVE_CHAT_ID. Не надсилай токен бота.|Forward a message from your private channel here. I will show its ID for TELEGRAM_ARCHIVE_CHAT_ID. Do not send your bot token.
arc.id_value|ID канала для ENV:\nTELEGRAM_ARCHIVE_CHAT_ID={id}\nДобавь этого бота администратором канала с правом публикации. Канал должен быть закрытым.|ID каналу для ENV:\nTELEGRAM_ARCHIVE_CHAT_ID={id}\nДодай цього бота адміністратором каналу з правом публікації. Канал має бути закритим.|Channel ID for ENV:\nTELEGRAM_ARCHIVE_CHAT_ID={id}\nAdd this bot as a channel administrator with posting permission. The channel must be private.
'''
STRINGS={key:dict(zip(('ru','uk','en'),[v.replace('\\n','\n') for v in values])) for key,*values in (line.split('|') for line in ROWS.strip().splitlines())}
