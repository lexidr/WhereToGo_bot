import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import datetime

BOT_TOKEN = '6032759993:AAFbXq-hofzHYQQtRLAH9XosRZFRajlDKQc'


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

reply_keyboard = [['/show_events', '/films'],
                  ['/edit']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)


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
    context.user_data['locality'] = update.message.text
    await update.message.reply_text("Спасибо! Теперь я смогу подобрать для тебя подходящие мероприятия!)")
    return 3


async def show_events(update, context):
    await update.message.reply_text(f"Вот такие вот мероприятия для {context.user_data['age']} {context.user_data['locality']}")
    return ConversationHandler.END


async def edit(update, context):
    await update.message.reply_text(
        "Ты хочешь изменить информацию о себе.\n"
        "Вы можете прервать опрос, послав команду /stop.\n"
        "Сколько тебе лет?")
    return 1


async def stop(update, context):
    await update.message.reply_text("Надеюсь, я смог вам помочь!")
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_age)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_city)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_events)]
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

    application.add_handler(conv_handler)
    application.add_handler(conv_edit)

    application.add_handler(CommandHandler("show_events", show_events))
    application.add_handler(CommandHandler("help", help))

    application.run_polling()


if __name__ == '__main__':
    main()
