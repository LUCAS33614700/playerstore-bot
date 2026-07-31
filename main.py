from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8678750605:AAGfbCBbNVm9FqOC7aR_hzR1p-8JB1URMJI"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """🎬 Bem-vindo à PLAYERSTORE!

Escolha um comando:

📺 /planos
💰 /precos
💳 /pagamento
🛠️ /suporte"""
    )

async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """📺 Planos disponíveis

• Netflix
• Disney+
• Prime Video
• Max
• HBO Max
• Spotify
• Xbox Game Pass
• ChatGPT Plus
• Canva Pro

Digite /precos para consultar os valores."""
    )

async def precos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """💰 Valores

Netflix - R$ 14,90
Disney+ - R$ 14,90
Prime Video - R$ 14,90
Max - R$ 14,90
Spotify - R$ 9,90
Xbox Game Pass - R$ 19,90
ChatGPT Plus - R$ 19,90
Canva Pro - R$ 9,90"""
    )

async def pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 Pagamento via Pix.\n\nEnvie o comprovante após o pagamento."
    )

async def suporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠️ Suporte\n\nFale com o administrador da PLAYERSTORE."
    )

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("planos", planos))
app.add_handler(CommandHandler("precos", precos))
app.add_handler(CommandHandler("pagamento", pagamento))
app.add_handler(CommandHandler("suporte", suporte))

print("Bot iniciado...")
app.run_polling()
