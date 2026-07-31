# ==========================================
# PLAYER STORE V2
# Desenvolvido para PLAYER STORE
# ==========================================

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

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
🎉 *Bem-vindo à {NOME_LOJA}!*

🏆 Sua loja de contas premium.

📺 Streaming
🎮 Games
🤖 Apps Premium

Escolha uma opção abaixo.
"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        WELCOME,
        parse_mode="Markdown",
        reply_markup=menu_principal()
    )# ==========================================
# MENU PRINCIPAL
# ==========================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    # ===== CATÁLOGO =====

    if query.data == "catalogo":

        await query.edit_message_text(
            text=CATALOGO,
            parse_mode="Markdown",
            reply_markup=teclado_catalogo()
        )

    # ===== CARRINHO =====

    elif query.data == "carrinho":

        keyboard = [
            [InlineKeyboardButton("⬅️ Voltar", callback_data="inicio")]
        ]

        await query.edit_message_text(
            "🛒 *Seu carrinho está vazio.*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== PERFIL =====

    elif query.data == "perfil":

        usuario = query.from_user

        keyboard = [
            [InlineKeyboardButton("⬅️ Voltar", callback_data="inicio")]
        ]

        await query.edit_message_text(
            f"""
👤 *Meu Perfil*

🆔 ID: `{usuario.id}`

👤 Nome: {usuario.first_name}

💰 Saldo: R$ 0,00
""",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== ADICIONAR SALDO =====

    elif query.data == "saldo":

        keyboard = [
            [InlineKeyboardButton("💳 Ver Pix", callback_data="pagamento")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="inicio")]
        ]

        await query.edit_message_text(
            "💰 *Adicionar saldo à sua conta.*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )    # ===== MEUS PEDIDOS =====

    elif query.data == "pedidos":

        keyboard = [
            [InlineKeyboardButton("⬅️ Voltar", callback_data="inicio")]
        ]

        await query.edit_message_text(
            """
📦 *MEUS PEDIDOS*

Você ainda não possui pedidos cadastrados.

Assim que realizar uma compra, ela aparecerá aqui.
""",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== RENOVAR =====

    elif query.data == "renovar":

        keyboard = [
            [InlineKeyboardButton("📲 WhatsApp", url="https://wa.me/559293592126?text=Olá! Quero renovar minha assinatura.")],
            [InlineKeyboardButton("💬 Telegram", url="https://t.me/sr_PICKLES")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="inicio")]
        ]

        await query.edit_message_text(
            """
🔄 *RENOVAÇÃO*

Renove sua assinatura de forma rápida.

Escolha um dos canais abaixo.
""",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== SUPORTE =====

    elif query.data == "suporte":

        keyboard = [
            [InlineKeyboardButton("📲 WhatsApp", url="https://wa.me/559293592126")],
            [InlineKeyboardButton("💬 Telegram", url="https://t.me/sr_PICKLES")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="inicio")]
        ]

        await query.edit_message_text(
            """
🛠️ *SUPORTE*

Estamos prontos para atender você.

📅 Atendimento diário.
""",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== GRUPO VIP =====

    elif query.data == "grupo":

        keyboard = [
            [InlineKeyboardButton("👥 Entrar no Grupo", url="https://t.me/sr_PICKLES")],
            [InlineKeyboardButton("⬅️ Voltar", callback_data="inicio")]
        ]

        await query.edit_message_text(
            """
👥 *GRUPO VIP*

Entre no nosso grupo para acompanhar novidades, promoções e lançamentos.
""",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== VOLTAR AO MENU =====

    elif query.data == "inicio":

        await query.edit_message_text(
            WELCOME,
            parse_mode="Markdown",
            reply_markup=menu_principal()
        )
