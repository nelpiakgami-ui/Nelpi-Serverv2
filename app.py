import os, threading
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nelpi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# GANTI BAGIAN INI
BOT_TOKEN = '9054849907:AAGh04X-TZnhN1aag29jb_cDkwpQVyurYpQ'
ADMIN_CHAT_ID = 8783941192 # ISI_ID_TELEGRAM_LO

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), unique=True)
    telegram_id = db.Column(db.String(50))
    tier = db.Column(db.String(20), default='free')
    quota_used = db.Column(db.Integer, default=0)
    def get_max_quota(self):
        return {'free': 50, 'vip_2k': 800, 'vip_5k': 2000, 'vip_10k': 999999}.get(self.tier, 50)

with app.app_context(): db.create_all()

@app.route('/')
def home(): return "Nelpi API is Running!"

@app.route('/api/register_device', methods=['POST'])
def register_device():
    data = request.json
    user = User.query.filter_by(device_id=data.get('device_id')).first()
    if not user:
        user = User(device_id=data.get('device_id'))
        db.session.add(user)
        db.session.commit()
    return jsonify({"tier": user.tier, "quota_used": user.quota_used, "max_quota": user.get_max_quota()})

@app.route('/api/consume_quota', methods=['POST'])
def consume_quota():
    data = request.json
    user = User.query.filter_by(device_id=data.get('device_id')).first()
    if not user: return jsonify({"error": "not found"}), 404
    if data.get('amount') > (user.get_max_quota() - user.quota_used): return jsonify({"error": "limit"}), 403
    user.quota_used += data.get('amount')
    db.session.commit()
    return jsonify({"status": "success"})

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif.")

async def daftar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    did = context.args[0]
    user = User.query.filter_by(device_id=did).first()
    if user:
        user.telegram_id = str(update.effective_user.id)
        db.session.commit()
        await update.message.reply_text("Berhasil ditautkan. Tunggu admin ACC.")
        keyboard = [[InlineKeyboardButton("✅ ACC VIP 2k", callback_data=f"acc_2k_{did}")],
                    [InlineKeyboardButton("✅ ACC VIP 5k", callback_data=f"acc_5k_{did}")],
                    [InlineKeyboardButton("✅ ACC VIP 10k", callback_data=f"acc_10k_{did}")]]
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Pendaftaran VIP: {did}", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Device ID tidak ditemukan.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_CHAT_ID: return
    await query.answer()
    data = query.data.split('_')
    user = User.query.filter_by(device_id=data[2]).first()
    if user:
        user.tier = f"vip_{data[1]}"
        user.quota_used = 0
        db.session.commit()
        await query.edit_message_text(text=f"VIP {data[1].upper()} Aktif untuk {data[2]}")
        if user.telegram_id:
            try: await context.bot.send_message(chat_id=user.telegram_id, text=f"Akun VIP {data[1]} Lo sudah aktif!")
            except: pass

def run_bot():
    bot = ApplicationBuilder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start_cmd))
    bot.add_handler(CommandHandler("daftar", daftar_cmd))
    bot.add_handler(CallbackQueryHandler(button_callback))
    bot.run_polling()

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
