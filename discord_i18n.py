ROWS = """
feed.title|Парсер|Парсер|Finds
feed.subtitle|Объявления из подключённого Discord-канала.|Оголошення з підключеного Discord-каналу.|Listings from the connected Discord channel.
feed.refresh|Обновить|Оновити|Refresh
feed.note|Обновление раз в минуту, пока эта вкладка открыта.|Оновлення щохвилини, поки цю вкладку відкрито.|Refreshes every minute while this tab is open.
feed.empty|Объявлений пока нет.|Оголошень поки немає.|No listings yet.
feed.unconfigured|Лента пока не подключена.|Стрічку ще не підключено.|The feed is not connected yet.
feed.unavailable|Не удалось обновить ленту. Сохранённые объявления остаются доступны.|Не вдалося оновити стрічку. Збережені оголошення залишаються доступними.|Could not refresh the feed. Saved listings are still available.
feed.price_unknown|Цена не указана|Ціну не вказано|Price not listed
feed.listing|Объявление|Оголошення|Listing
feed.open|Открыть объявление|Відкрити оголошення|Open listing
feed.source|Сообщение в Discord|Повідомлення в Discord|Discord message
feed.search|Поиск по названию|Пошук за назвою|Search by title
feed.previous|Предыдущие|Попередні|Previous
feed.next|Следующие|Наступні|Next
feed.no_photo|Без фото|Без фото|No photo
feed.admin_setup|В ENV нужны DISCORD_BOT_TOKEN и DISCORD_CHANNEL_ID. Боту нужны доступ к каналу, история сообщений и Message Content Intent.|В ENV потрібні DISCORD_BOT_TOKEN і DISCORD_CHANNEL_ID. Боту потрібні доступ до каналу, історія повідомлень і Message Content Intent.|Set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID. The bot needs channel access, Read Message History and Message Content Intent.
feed.updated|Лента обновлена|Стрічку оновлено|Feed refreshed
feed.error_access|Discord отказал в доступе: проверьте токен, ID канала и права бота.|Discord відмовив у доступі: перевірте токен, ID каналу та права бота.|Discord denied access: check the token, channel ID and bot permissions.
feed.error_content|Discord возвращает сообщения без содержимого. Проверьте Message Content Intent.|Discord повертає повідомлення без вмісту. Перевірте Message Content Intent.|Discord returned messages without content. Check Message Content Intent.
feed.error_network|Discord временно недоступен. Повторим обновление позже.|Discord тимчасово недоступний. Повторимо оновлення пізніше.|Discord is temporarily unavailable. Refresh will retry later.
feed.error_limit|Discord ограничил запросы. Обновление возобновится автоматически.|Discord обмежив запити. Оновлення відновиться автоматично.|Discord rate limited requests. Refresh will resume automatically.
"""
STRINGS={}
for line in ROWS.strip().splitlines():
    key,ru,uk,en=line.split('|')
    STRINGS[key]=dict(ru=ru,uk=uk,en=en)
