from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import BOT_TOKEN, verificar_configuracao
from database import criar_tabelas, criar_usuario, consultar_saldo
from menu import menu_principal
from catalogo import menu_catalogo, buscar_produto


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user

    criar_usuario(
        usuario.id,
        usuario.first_name or "",
        usuario.username or ""
    )

    texto = (
        f"👋 Olá, {usuario.first_name}!\n\n"
        "🛒 Bem-vindo à PLAYER STORE!\n\n"
        "Escolha uma opção abaixo:"
    )

    await update.message.reply_text(
        texto,
        reply_markup=menu_principal()
    )


async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    usuario_id = query.from_user.id
    acao = query.data

    if acao == "catalogo":
        await query.edit_message_text(
            "🛒 *LOGINS | CONTAS PREMIUM*\n\n"
            "Escolha um produto:",
            reply_markup=menu_catalogo(),
            parse_mode="Markdown"
        )

    elif acao == "saldo":
        saldo = consultar_saldo(usuario_id)

        await query.edit_message_text(
            f"💵 *Seu saldo*\n\n"
            f"Saldo atual: R$ {saldo:.2f}\n\n"
            "Em breve vamos adicionar o sistema de pagamento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "perfil":
        saldo = consultar_saldo(usuario_id)

        await query.edit_message_text(
            f"👤 *SEU PERFIL*\n\n"
            f"🆔 ID: `{usuario_id}`\n"
            f"💰 Saldo: R$ {saldo:.2f}",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "voltar_menu":
        await query.edit_message_text(
            "🏠 *MENU PRINCIPAL*\n\n"
            "Escolha uma opção:",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao.startswith("produto_"):
        produto_id = int(acao.split("_")[1])
        produto = buscar_produto(produto_id)

        if not produto:
            await query.answer(
                "❌ Produto não encontrado.",
                show_alert=True
            )
            return

        _, nome, descricao, preco, estoque = produto

        texto = (
            f"🛒 *{nome}*\n\n"
            f"📝 {descricao or 'Sem descrição'}\n\n"
            f"💰 Preço: R$ {preco:.2f}\n"
            f"📦 Estoque: {estoque}"
        )

        botoes = [
            [
                InlineKeyboardButton(
                    "🛒 Comprar",
                    callback_data=f"comprar_{produto_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="catalogo"
                )
            ]
        ]

        from telegram import InlineKeyboardMarkup

        await query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(botoes),
            parse_mode="Markdown"
        )

    elif acao == "carrinho":
        await query.edit_message_text(
            "🛍️ *CARRINHO*\n\n"
            "Seu carrinho está vazio.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "pesquisar":
        await query.edit_message_text(
            "🔎 *PESQUISAR SERVIÇO*\n\n"
            "Sistema de pesquisa em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "estoque":
        await query.edit_message_text(
            "📦 *ESTOQUE DE LOGINS*\n\n"
            "Consulte os produtos disponíveis através do catálogo.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "mac":
        await query.edit_message_text(
            "🎮 *ATIVAÇÃO DE MAC*\n\n"
            "Sistema de ativação em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "jogos":
        await query.edit_message_text(
            "⚽ *JOGOS NA TV*\n\n"
            "Informações sobre jogos serão adicionadas aqui.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "renovar":
        await query.edit_message_text(
            "♻️ *RENOVAR CONTA*\n\n"
            "Sistema de renovação em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "suporte":
        await query.edit_message_text(
            "🆘 *SUPORTE*\n\n"
            "Entre em contato com o suporte.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "termos":
        await query.edit_message_text(
            "📜 *TERMOS DE USO*\n\n"
            "Os termos de uso serão adicionados aqui.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "outros_bots":
        await query.edit_message_text(
            "🤖 *OUTROS BOTS*\n\n"
            "Em breve.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "grupo":
        await query.edit_message_text(
            "👥 *GRUPO DE CLIENTES*\n\n"
            "O link do grupo será configurado depois.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "alugar":
        await query.edit_message_text(
            "📣 *ALUGAR ESTE BOT*\n\n"
            "Em breve você poderá solicitar seu próprio bot.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    elif acao == "sem_estoque":
        await query.answer(
            "📦 O estoque está vazio.",
            show_alert=True
        )


def main():
    verificar_configuracao()
    criar_tabelas()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(botoes))

    print("🤖 Bot iniciado!")

    app.run_polling()


if __name__ == "__main__":
    main()
