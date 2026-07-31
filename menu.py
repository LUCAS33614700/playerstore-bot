from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def menu_principal():

    teclado = [

        [
            InlineKeyboardButton("🛍️ Catálogo", callback_data="catalogo"),
            InlineKeyboardButton("🛒 Carrinho", callback_data="carrinho")
        ],

        [
            InlineKeyboardButton("💰 Saldo", callback_data="saldo"),
            InlineKeyboardButton("👤 Perfil", callback_data="perfil")
        ],

        [
            InlineKeyboardButton("📦 Pedidos", callback_data="pedidos"),
            InlineKeyboardButton("🔄 Renovar", callback_data="renovar")
        ],

        [
            InlineKeyboardButton("💳 Pagamento", callback_data="pagamento"),
            InlineKeyboardButton("🎁 Promoções", callback_data="promocoes")
        ],

        [
            InlineKeyboardButton("📞 Suporte", callback_data="suporte"),
            InlineKeyboardButton("👥 Grupo VIP", callback_data="grupo")
        ],

        [
            InlineKeyboardButton("❓ FAQ", callback_data="faq")
        ]

    ]

    return InlineKeyboardMarkup(teclado)
