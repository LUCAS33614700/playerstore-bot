from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CATALOGO = """
🛍️ *CATÁLOGO PLAYER STORE*

Escolha uma categoria abaixo.

━━━━━━━━━━━━━━━━━━━━━━

📺 Streaming

🎵 Música

🎮 Games

💻 Produtividade

━━━━━━━━━━━━━━━━━━━━━━

⚡ Entrega rápida
🔒 Contas Premium
🛠️ Suporte Garantido
"""


def teclado_catalogo():

    keyboard = [

        [InlineKeyboardButton("📺 Streaming", callback_data="streaming")],

        [InlineKeyboardButton("🎵 Música", callback_data="musica")],

        [InlineKeyboardButton("🎮 Games", callback_data="games")],

        [InlineKeyboardButton("💻 Produtividade", callback_data="apps")],

        [InlineKeyboardButton("🏠 Menu Principal", callback_data="inicio")]

    ]

    return InlineKeyboardMarkup(keyboard)


def teclado_streaming():

    keyboard = [

        [InlineKeyboardButton("📺 Netflix", callback_data="netflix")],

        [InlineKeyboardButton("📦 Prime Video", callback_data="prime")],

        [InlineKeyboardButton("🍿 Disney+", callback_data="disney")],

        [InlineKeyboardButton("🎥 Max", callback_data="max")],

        [InlineKeyboardButton("⬅️ Voltar", callback_data="catalogo")]

    ]

    return InlineKeyboardMarkup(keyboard)


def teclado_games():

    keyboard = [

        [InlineKeyboardButton("🎮 Xbox Game Pass", callback_data="xbox")],

        [InlineKeyboardButton("🎮 PlayStation Plus", callback_data="psplus")],

        [InlineKeyboardButton("⬅️ Voltar", callback_data="catalogo")]

    ]

    return InlineKeyboardMarkup(keyboard)


def teclado_apps():

    keyboard = [

        [InlineKeyboardButton("🤖 ChatGPT Plus", callback_data="chatgpt")],

        [InlineKeyboardButton("🎨 Canva Pro", callback_data="canva")],

        [InlineKeyboardButton("⬅️ Voltar", callback_data="catalogo")]

    ]

    return InlineKeyboardMarkup(keyboard)


def teclado_musica():

    keyboard = [

        [InlineKeyboardButton("🎧 Spotify Premium", callback_data="spotify")],

        [InlineKeyboardButton("🎼 Deezer", callback_data="deezer")],

        [InlineKeyboardButton("⬅️ Voltar", callback_data="catalogo")]

    ]

    return InlineKeyboardMarkup(keyboard)
