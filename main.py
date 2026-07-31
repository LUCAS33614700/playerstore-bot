from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TOKEN, NOME_LOJA
from menu import menu_principal
from catalogo import CATALOGO, teclado_catalogo

WELCOME=f"""🏪 *{NOME_LOJA}*

🏆 Sua loja de Streaming, Games e Apps Premium.

Escolha uma opção abaixo.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=menu_principal())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    if query.data=="catalogo":
        await query.edit_message_text(CATALOGO, parse_mode="Markdown", reply_markup=teclado_catalogo())
    elif query.data=="inicio":
        await query.edit_message_text(WELCOME, parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="carrinho":
        await query.edit_message_text("🛒 *Carrinho*\n\nSeu carrinho está vazio.", parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="perfil":
        u=query.from_user
        await query.edit_message_text(f"👤 *Meu Perfil*\n\n🆔 `{u.id}`\n👤 {u.first_name}\n💰 Saldo: R$ 0,00\n📦 Pedidos: 0", parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="saldo":
        await query.edit_message_text("💰 Pix: moraes3361@gmail.com", parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="pedidos":
        await query.edit_message_text("📦 Nenhum pedido.", parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="renovar":
        await query.edit_message_text("🔄 Renovação.", parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="pagamento":
        await query.edit_message_text("💳 Pix: moraes3361@gmail.com", parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="promocoes":
            elif query.data == "cat_streaming":

        texto = """
📺 *STREAMING*

• Netflix
• Prime Video
• Disney+
• Max
• Apple TV+
• Globoplay
• Paramount+
• Crunchyroll
• Discovery+
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=teclado_catalogo()
        )

    elif query.data == "cat_musica":

        texto = """
🎵 *MÚSICA*

• Spotify Premium
• Deezer Premium
• YouTube Premium
• Tidal HiFi
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=teclado_catalogo()
        )

    elif query.data == "cat_games":

        texto = """
🎮 *GAMES*

• Xbox Game Pass
• PlayStation Plus
• EA Play
• Ubisoft+
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=teclado_catalogo()
        )

    elif query.data == "cat_apps":

        texto = """
🤖 *IA E APPS*

• ChatGPT Plus
• Canva Pro
• Microsoft 365
• Google One
• Dropbox Plus
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=teclado_catalogo()
)
        await query.edit_message_text("🎁 Promoções.", parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="suporte":
        await query.edit_message_text("🛠️ WhatsApp: https://wa.me/559293592126", parse_mode="Markdown", disable_web_page_preview=True, reply_markup=menu_principal())
    elif query.data=="grupo":
        await query.edit_message_text("👥 Grupo VIP em breve.", parse_mode="Markdown", reply_markup=menu_principal())
    elif query.data=="faq":
        await query.edit_message_text("❓ FAQ.", parse_mode="Markdown", reply_markup=menu_principal())

def main():
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()

if __name__=="__main__":
    main()
        
