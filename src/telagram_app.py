import os
import random
import time

from telegram import __version__ as TG_VER
from dotenv import load_dotenv

# from ai_agent import dialog_router, english_to_russian
# from utils import load_json, get_file_path, dump_json
# from db import save_message, get_message_by_id, setup_database

load_dotenv(os.path.join(os.environ['CONFIG_DIR'], '.env'))

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from dialog_agent import dialog_router, request_api


TOKEN = os.environ['TG_BOT_TOKEN']
# quiz_file_path = get_file_path('quiz_db.json')
# quiz_db = load_json(quiz_file_path)
# keys = list(quiz_db.keys())
# print(f'Num keys {len(keys)}')
# message_history = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Use /help for help",
        reply_markup=ForceReply(selective=True),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    response = [
        "🌿 Hey there! I’m your AI budtender 🤖. Ask me anything about cannabis products — I’ve got you covered! 💬"
    ]
    for i in response:
        await update.message.reply_text(i)

async def bot_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_tg = update.effective_user
    user = {'user_id': user_tg.id, 'user_name': user_tg.username}
    print(user)
    bot_response = dialog_router(update.message.text, user)
    if bot_response['final_answer']:
        user_query = bot_response['answer']['user_query']
        print('Requesting search service')
        search_results = request_api(user_query)
        for i in search_results[:4]:
            await update.message.reply_html(
                f'<a href="{i[1]}">{i[0]}</a>',
                reply_markup=ForceReply(selective=True),
            )
    for line in bot_response['answer'].split('\n'):
        if len(line) > 0 :
            await update.message.reply_text(line)
            # await save_message(
            #     message_id=message.message_id,
            #     chat_id=message.chat_id,
            #     user_id=context.bot.id,
            #     message_text=line[2:]
            # )


def main() -> None:
    """Start the bot."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_dialog))
    
    application.run_polling(
        allowed_updates=["message", "edited_message", "channel_post",
                        "edited_channel_post", "message_reaction"],
    )

if __name__ == "__main__":
    main()
