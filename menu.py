from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def menu_principal():
    teclado = [
        [
            InlineKeyboardButton(
                "🛒 LOGINS | CONTAS PREMIUM",
                callback_data="catalogo"
            )
        ],
        [
            InlineKeyboardButton("🛍️ CARRINHO", callback_data="carrinho"),
            InlineKeyboardButton("💵 ADICIONAR SALDO", callback_data="saldo")
        ],
        [
            InlineKeyboardButton("🔎 PESQUISAR SERVIÇO", callback_data="pesquisar"),
            InlineKeyboardButton("📦 ESTOQUE DE LOGINS", callback_data="estoque")
        ],
        [
            InlineKeyboardButton("🎮 ATIVAÇÃO DE MAC", callback_data="mac"),
            InlineKeyboardButton("⚽ JOGOS NA TV", callback_data="jogos")
        ],
        [
            InlineKeyboardButton("♻️ RENOVAR CONTA", callback_data="renovar")
        ],
        [
            InlineKeyboardButton("🆘 SUPORTE", callback_data="suporte"),
            InlineKeyboardButton("👤 PERFIL", callback_data="perfil")
        ],
        [
            InlineKeyboardButton("📜 TERMOS DE USO", callback_data="termos"),
            InlineKeyboardButton("🤖 OUTROS BOTS", callback_data="outros_bots")
        ],
        [
            InlineKeyboardButton(
                "👥 GRUPO DE CLIENTES",
                callback_data="grupo"
            )
        ],
        [
            InlineKeyboardButton(
                "📣 ALUGAR ESTE BOT",
                callback_data="alugar"
            )
        ]
    ]

    return InlineKeyboardMarkup(teclado)
