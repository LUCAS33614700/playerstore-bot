from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CATALOGO = """
🛍 *CATÁLOGO PLAYER STORE*

Escolha uma categoria:
"""

def teclado_catalogo():
    teclado = [
        [InlineKeyboardButton("📺 Streaming", callback_data="cat_streaming")],
        [InlineKeyboardButton("🎵 Música", callback_data="cat_musica")],
        [InlineKeyboardButton("🎮 Games", callback_data="cat_games")],
        [InlineKeyboardButton("🤖 IA e Apps", callback_data="cat_apps")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="inicio")]
    ]

    return InlineKeyboardMarkup(teclado)
