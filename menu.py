from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def menu_principal():

    botoes = [

        # LOGINS
        [
            InlineKeyboardButton(
                "🛒 LOGINS | CONTAS PREMIUM",
                callback_data="catalogo"
            )
        ],

        # CARRINHO / SALDO
        [
            InlineKeyboardButton(
                "🛍️ CARRINHO",
                callback_data="carrinho"
            ),
            InlineKeyboardButton(
                "💵 ADICIONAR SALDO",
                callback_data="adicionar_saldo"
            )
        ],

        # PESQUISA / ESTOQUE
        [
            InlineKeyboardButton(
                "🔎 PESQUISAR SERVIÇO",
                switch_inline_query_current_chat=(
                    "buscar_loguin "
                ),
            ),
            InlineKeyboardButton(
                "📦 ESTOQUE DE LOGINS",
                callback_data="estoque_logins"
            )
        ],

        # SERVIÇOS
        [
            InlineKeyboardButton(
                "🎮 ATIVAÇÃO DE MAC",
                callback_data="ativacao_mac"
            ),
            InlineKeyboardButton(
                "⚽ JOGOS NA TV",
                callback_data="jogos_tv"
            )
        ],

        # RENOVAR
        [
            InlineKeyboardButton(
                "♻️ RENOVAR CONTA",
                callback_data="renovar_conta"
            )
        ],

        # SUPORTE / PERFIL
        [
            InlineKeyboardButton(
                "🆘 SUPORTE",
                callback_data="suporte"
            ),
            InlineKeyboardButton(
                "👤 PERFIL",
                callback_data="perfil"
            )
        ],

        # TERMOS / OUTROS BOTS
        [
            InlineKeyboardButton(
                "📜 TERMOS DE USO",
                callback_data="termos"
            ),
            InlineKeyboardButton(
                "🤖 OUTROS BOTS",
                callback_data="outros_bots"
            )
        ],

        # GRUPO
        [
            InlineKeyboardButton(
                "👥 GRUPO DE CLIENTES",
                callback_data="grupo"
            )
        ],

        # ALUGAR BOT
        [
            InlineKeyboardButton(
                "📣 ALUGAR ESTE BOT",
                callback_data="alugar_bot"
            )
        ],
    ]

    return InlineKeyboardMarkup(botoes)
