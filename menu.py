from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def menu_principal():
    teclado = [
        [
            InlineKeyboardButton("🛍️ Catálogo", callback_data="catalogo"),
            InlineKeyboardButton("🛒 Carrinho", callback_data="carrinho")
        ],
        [
            InlineKeyboardButton("💰 Adicionar Saldo", callback_data="saldo"),
            InlineKeyboardButton("👤 Perfil", callback_data="perfil")
        ],
        [
            InlineKeyboardButton("📦 Meus Pedidos", callback_data="pedidos"),
            InlineKeyboardButton("🔄 Renovar", callback_data="renovar")
        ],
        [
            InlineKeyboardButton("📞 Suporte", callback_data="suporte"),
            InlineKeyboardButton("👥 Grupo VIP", callback_data="grupo")
        ]
    ]

    return InlineKeyboardMarkup(teclado)
