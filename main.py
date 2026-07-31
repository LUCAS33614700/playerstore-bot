from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from config import TOKEN, NOME_LOJA
from menu import menu_principal
from catalogo import CATALOGO, teclado_catalogo

WELCOME = f"""
🏪 *{NOME_LOJA}*

━━━━━━━━━━━━━━━━━━━━

🏆 Sua loja de Streaming, Games e Apps Premium.

⚡ Entrega rápida
🔒 Compra segura
🛠️ Suporte garantido

━━━━━━━━━━━━━━━━━━━━

Escolha uma opção abaixo.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        WELCOME,
        parse_mode="Markdown",
        reply_markup=menu_principal()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.data == "catalogo":

        await query.edit_message_text(
            text=CATALOGO,
            parse_mode="Markdown",
            reply_markup=teclado_catalogo()
        )

    elif query.data == "inicio":

        await query.edit_message_text(
            text=WELCOME,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )
elif query.data == "carrinho":

        await query.edit_message_text(
            "🛒 *Carrinho*\n\nSeu carrinho está vazio.",
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

    elif query.data == "perfil":

        usuario = query.from_user

        texto = f"""
👤 *Meu Perfil*

🆔 ID: `{usuario.id}`

👤 Nome: {usuario.first_name}

💰 Saldo: R$ 0,00

📦 Pedidos: 0
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

    elif query.data == "saldo":

        texto = """
💰 *Adicionar Saldo*

Forma de pagamento:

💳 Pix

Após realizar o pagamento, envie o comprovante ao suporte.
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

    elif query.data == "pedidos":

        await query.edit_message_text(
            "📦 *Meus Pedidos*\n\nVocê ainda não possui pedidos.",
            parse_mode="Markdown",
            reply_markup=menu_principal()
)    elif query.data == "renovar":

        texto = """
🔄 *Renovação*

Renove sua assinatura de forma rápida.

Escolha um canal abaixo para continuar.
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

    elif query.data == "pagamento":

        texto = """
💳 *Pagamento*

━━━━━━━━━━━━━━

💠 PIX

📧 Chave Pix

moraes3361@gmail.com

━━━━━━━━━━━━━━

Após o pagamento envie o comprovante ao suporte.
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

    elif query.data == "promocoes":

        texto = """
🎁 *Promoções*

🔥 Confira nossas promoções entrando em contato com o suporte.

As ofertas são atualizadas frequentemente.
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

    elif query.data == "suporte":

        texto = """
🛠️ *Suporte*

📲 WhatsApp
https://wa.me/559293592126

💬 Telegram
https://t.me/sr_PICKLES
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

    elif query.data == "grupo":

        texto = """
👥 *Grupo VIP*

Em breve você poderá entrar no grupo exclusivo da PLAYER STORE.
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )

    elif query.data == "faq":

        texto = """
❓ *Perguntas Frequentes*

• Como recebo meu acesso?
Após a confirmação do pagamento.

• Qual a forma de pagamento?
Pix.

• Tem suporte?
Sim, durante o período contratado.
"""

        await query.edit_message_text(
            texto,
            parse_mode="Markdown",
            reply_markup=menu_principal()
)# ==========================================
# INICIALIZAÇÃO DO BOT
# ==========================================

def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print(f"{NOME_LOJA} iniciado com sucesso!")

    app.run_polling()


if __name__ == "__main__":
    main()
