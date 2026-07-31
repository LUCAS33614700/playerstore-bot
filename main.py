# PLAYERSTORE Bot (modelo inicial)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os

TOKEN = os.getenv("BOT_TOKEN")

WELCOME = """🎉 *Bem-vindo à PLAYERSTORE!*

🏆 Sua loja de contas digitais.

📺 Streaming
🎮 Games
💻 Produtividade

Escolha uma opção abaixo.
"""

CATALOGO = """🛍️ *CATÁLOGO*

📺 Netflix
📺 Prime Video
🍿 Disney+
🎥 Max
🎞️ Paramount+
🥋 Crunchyroll
📺 Apple TV+
📺 Globoplay
📡 Globoplay + Canais
📺 Universal+
📺 Telecine
📺 MUBI
📺 Discovery+
▶️ YouTube Premium
🎵 Spotify Premium
🎵 Deezer Premium
🎵 Tidal HiFi

🎮 Xbox Game Pass
🎮 PlayStation Plus
🎮 EA Play
🎮 Ubisoft+

🤖 ChatGPT Plus
🎨 Canva Pro
💼 Microsoft 365
☁️ Google One
📂 Dropbox Plus
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🛍️ Catálogo", callback_data="catalogo")],
        [InlineKeyboardButton("💳 Pagamento", callback_data="pagamento")],
        [InlineKeyboardButton("🛠️ Suporte", callback_data="suporte")]
    ]
    await update.message.reply_text(
        WELCOME,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "catalogo":
        await q.edit_message_text(CATALOGO, parse_mode="Markdown")

    elif q.data == "pagamento":
        await q.edit_message_text(
            "💳 *Pagamento*\n\n"
            "Pix:\n"
            "`moraes3361@gmail.com`\n\n"
            "Após o pagamento envie o comprovante.\n\n"
            "WhatsApp:\nhttps://wa.me/559293592126\n\n"
            "Telegram:\nhttps://t.me/sr_PICKLES",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    elif q.data == "suporte":
        await q.edit_message_text(
            "🛠️ *Suporte*\n\n"
            "WhatsApp:\nhttps://wa.me/559293592126\n\n"
            "Telegram:\nhttps://t.me/sr_PICKLES",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

if __name__ == "__main__":
    app.run_polling()
    
