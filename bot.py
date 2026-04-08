import json
import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКИ (токен уже внутри) ---
BOT_TOKEN = "8442204653:AAHwUFaMToLVyuaUIxoQn8vd64kyCUVZytg"
ADMIN_ID = 6706047006

# --- ИНИЦИАЛИЗАЦИЯ ---
app = Flask(__name__)

# Создаём приложение PTB v20+
application = Application.builder().token(BOT_TOKEN).build()
bot = application.bot

# Хранилище балансов (в памяти)
balances = {}

# --- ОБРАБОТЧИК ДАННЫХ ИЗ МИНИ-ПРИЛОЖЕНИЯ ---
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_message.web_app_data:
        return
    
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        
        if data.get('type') == 'admin_deposit':
            # Проверка на админа
            if update.effective_user.id != ADMIN_ID:
                await update.message.reply_text("⛔ Доступ запрещён")
                return
            
            user_id = str(data.get('targetId'))
            amount = int(data.get('amount', 0))
            
            balances[user_id] = balances.get(user_id, 0) + amount
            
            await update.message.reply_text(f"✅ Начислено {amount} ₽ пользователю {user_id}")
            
            try:
                await bot.send_message(chat_id=user_id, text=f"🎉 Ваш баланс пополнен на {amount} ₽!")
            except Exception as e:
                print(f"Не удалось уведомить {user_id}: {e}")
                
    except Exception as e:
        print(f"Ошибка WebAppData: {e}")

# Регистрируем обработчик
application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

# --- ВЕБХУК ДЛЯ TELEGRAM ---
@app.route('/webhook', methods=['POST'])
async def webhook():
    """Принимает обновления от Telegram"""
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        await application.process_update(update)
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Ошибка вебхука: {e}")
        return jsonify({"status": "error"}), 500

# --- API ДЛЯ МИНИ-ПРИЛОЖЕНИЯ ---
@app.route('/api/balance/<user_id>')
def get_balance(user_id):
    """Отдаёт баланс пользователя для фронта"""
    return jsonify({"balance": balances.get(str(user_id), 0)})

# --- ПРОВЕРКА РАБОТЫ ---
@app.route('/')
def home():
    return "✅ Bot is running (PTB v20.7)", 200

# --- НАСТРОЙКА ВЕБХУКА ПРИ ЗАПУСКЕ ---
async def setup_webhook():
    """Устанавливает URL вебхука при старте"""
    render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if render_host:
        webhook_url = f"https://{render_host}/webhook"
        await bot.set_webhook(webhook_url)
        print(f"✅ Webhook установлен: {webhook_url}")
    else:
        print("⚠️ RENDER_EXTERNAL_HOSTNAME не найден (локальный запуск)")

# --- ТОЧКА ВХОДА ---
if __name__ == '__main__':
    # Запускаем асинхронную настройку вебхука
    asyncio.run(setup_webhook())
    
    # Запускаем Flask
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
