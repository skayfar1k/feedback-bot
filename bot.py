import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI, Request
import uvicorn

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", "https://localhost")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
app = FastAPI()

user_messages = {} 

@dp.message(CommandStart())
async def start(msg: Message):
    await msg.answer("привет! напиши сюда свой отзыв или предложение — я передам его команде.")

@dp.message()
async def handle_feedback(msg: Message):
    if msg.chat.id == ADMIN_ID and msg.reply_to_message:
        reply_to_id = msg.reply_to_message.message_id
        if reply_to_id in user_messages:
            target_user = user_messages[reply_to_id]
            try:
                await bot.send_message(target_user, f"ответ от команды:\n\n{msg.text}")
                await msg.answer("отправлено пользователю.")
            except Exception as e:
                await msg.answer(f"ошибка: {e}")
        return

    if msg.from_user.id == ADMIN_ID:
        return

    user = msg.from_user
    header = f"<b>новое обращение</b>\nОт: {user.full_name} (@{user.username or 'нет'})\nID: <code>{user.id}</code>"
    
    sent_header = await bot.send_message(ADMIN_ID, header)
    forwarded = await msg.forward(ADMIN_ID)
    
    user_messages[forwarded.message_id] = user.id
    
    await msg.answer("спасибо! Твоё сообщение получено.")

@app.post("/webhook")
async def webhook(request: Request):
    update_data = await request.json()
    update = Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    print("Вебхук установлен!")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
