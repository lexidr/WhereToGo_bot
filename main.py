import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import requests
import datetime
import sqlite3


con = sqlite3.connect("data/info_of_users.db")
cur = con.cursor()

BOT_TOKEN = '6032759993:AAFbXq-hofzHYQQtRLAH9XosRZFRajlDKQc'

# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
# )

cur.execute("""CREATE TABLE IF NOT EXISTS info(
   user_name INT PRIMARY KEY,
   age INT,
   city TEXT
   );
""")

# logger = logging.getLogger(__name__)

reply_keyboard = [['Концерт', 'Экскурсии'],
                  ['Кино', 'Театр']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)


places = {'Концерт': 'concert', 'Кино': 'cinema', 'Театр': 'theatre', 'Экскурсии': 'excursions'}


def translate_city(city):
    data = requests.get(
        "https://afisha.yandex.ru/api/cities?city=moscow").json()
    for i in data['data']:
        if i['name'].lower() == city.lower():
            return i['id']
    return None


def event(i):
    name = i['event']['title']
    place = i['scheduleInfo']['oneOfPlaces']['title']
    address = i['scheduleInfo']['oneOfPlaces']['address']
    date = i['scheduleInfo']['preview']['text']
    link = 'https://afisha.yandex.ru' + i['event']['url']
    text = name + '\n\n' + date + '\n\n' + place + ', ' + address + '\n\n' + link
    return text


async def start(update, context):
    await update.message.reply_text(
        "Привет. Это телеграмм бот WhereToGo!\n"
        "Я могу рассказать тебе всё о мероприятиях в твоём городе.\n"
        "Но сначала ответь на пару вопросов.\n"
        "Сколько тебе лет?")
    return 1


async def enter_age(update, context):
    a = update.message.text
    if a.isdigit() and int(a) > 0:
        context.user_data['age'] = a
        await update.message.reply_text("В каком городе ты живёшь?")
        return 2
    else:
        await update.message.reply_text("Неверный формат ввода. Попробуйте еще раз.")
        return 1


async def enter_city(update, context):
    city = translate_city(update.message.text)
    if city:
        context.user_data['locality'] = city
        res = cur.execute("""SELECT user_name FROM info
                       WHERE user_name = ?""", (update.effective_message.from_user['id'],)).fetchall()
        if not res:
            cur.execute("""INSERT INTO info(user_name,age,city) VALUES(?,?,?)""",
                        (update.effective_message.from_user['id'], context.user_data['age'], city))
            con.commit()
        else:
            cur.execute(f"""UPDATE info SET city = '{city}'
                       WHERE user_name = '{update.effective_message.from_user['id']}'""")
            con.commit()
        await update.message.reply_text(
            "Спасибо!\n"
            "Теперь я смогу подобрать для тебя подходящие мероприятия!\n"
            "Напиши команду /show_events, чтобы посмотреть мероприятия)"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Нет такого города.\n"
            "Попробуйте ещё раз.\n"
        )
        return 2


async def show_events(update, context):
    await update.message.reply_text(f"Какой тип мероприятия тебя интересует?", reply_markup=markup)
    return 1


async def enter_type(update, context):
    context.user_data['type'] = places[update.message.text]
    await update.message.reply_text("Теперь расскажи в какие даты ты ищешь мероприятия. Введи первую дату в формате 00.00.0000",
                                    reply_markup=ReplyKeyboardRemove())
    return 2


async def enter_data_start(update, context):
    date = update.message.text
    try:
        date = datetime.datetime.strptime(date, '%d.%m.%Y')
        context.user_data['date'] = date.strftime("%Y-%m-%d")
        await update.message.reply_text('Укажи количество дней, в которые мне искать мероприятия')
        return 3
    except Exception as e:
        await update.message.reply_text('Неверный формат, попробуйте ещё раз')
        return 2


async def enter_data_end(update, context):
    p = update.message.text
    if p.isdigit() and int(p) > 0:
        context.user_data['period'] = p
        await update.message.reply_text("Спасибо! Теперь я смогу подобрать для тебя подходящие мероприятия!)")

        res = cur.execute("""SELECT city FROM info
                       WHERE user_name = ?""", (update.effective_message.from_user['id'],)).fetchall()
        print(res)

        req = "https://afisha.yandex.ru/api/events/rubric/" + context.user_data['type'] + \
              "?city=" + res[0][0] + '&date=' + context.user_data['date'] \
              + '&period=' + context.user_data['period']
        data = requests.get(req).json()['data']
        if len(data) == 0:
            await update.message.reply_text(
                'Подходящих мероприятий не найдено. Чтобы попробовать ещё раз, напишите комнаду /show_events')
            return ConversationHandler.END
        else:
            context.user_data['i'] = 0
            r = event(data[context.user_data['i']])
            await update.message.reply_text(r)
            await update.message.reply_text(
                    'Напишите команду /next, чтобы посмотреть следующее мероприятие, и /stop - для окончания поиска')
    else:
        await update.message.reply_text('Неверный формат, попробуйте ещё раз')
        return 3


async def next_event(update, context):
    res = cur.execute("""SELECT city FROM info
                WHERE user_name = ?""", (update.effective_message.from_user['id'], )).fetchall()
    req = "https://afisha.yandex.ru/api/events/rubric/" + context.user_data['type'] + \
          "?city=" + res[0][0] + '&date=' + context.user_data['date'] \
          + '&period=' + context.user_data['period']
    data = requests.get(req).json()['data']
    context.user_data['i'] += 1
    if context.user_data['i'] == len(data) - 1:
        await update.message.reply_text('Это все мероприятия, которые я смог найти')
        return ConversationHandler.END
    else:
        r = event(data[context.user_data['i']])
        await update.message.reply_text(r)


async def edit(update, context):
    await update.message.reply_text(
        "Ты хочешь изменить информацию о себе.\n"
        "Вы можете прервать опрос, послав команду /stop.\n"
        "Сколько тебе лет?")
    return 1


async def stop(update, context):
    await update.message.reply_text("Надеюсь, я смог вам помочь!")
    return ConversationHandler.END


async def unknown(update, context):
    await update.message.reply_text("Простите, я не понимаю команду.    ")
      
      
async def help(update, context):
    await update.message.reply_text("/start - запуск бота\n/show_events - вывод всех мероприятий\n/help - информация о всех командах\n/edit - редактирование информации о себе")


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_age)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_city)],
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    conv_edit = ConversationHandler(
        entry_points=[CommandHandler('edit', edit)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_age)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_city)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    conv_show_events = ConversationHandler(
        entry_points=[CommandHandler('show_events', show_events)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_type)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_data_start)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_data_end)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, next_event)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    conv_next = ConversationHandler(
        entry_points=[CommandHandler('next', next_event)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, next_event)]
        },

        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)
    application.add_handler(conv_edit)
    application.add_handler(conv_show_events)
    application.add_handler(conv_next)

    application.add_handler(CommandHandler("show_events", show_events))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("next", next_event))

    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
