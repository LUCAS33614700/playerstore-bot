from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CATALOGO = """
🛍️ *CATÁLOGO PLAYER STORE*

📺 STREAMING
• Netflix
• Prime Video
• Disney+
• Max
• Apple TV+
• Globoplay
• Globoplay + Canais
• Paramount+
• Crunchyroll
• Universal+
• Telecine
• MUBI
• Discovery+
• YouTube Premium

🎵 MÚSICA
• Spotify Premium
• Deezer Premium
• Tidal HiFi

🎮 GAMES
• Xbox Game Pass
• PlayStation Plus
• EA Play
• Ubisoft+

🤖 PRODUTIVIDADE
• ChatGPT Plus
• Canva Pro
• Microsoft 365
• Google One
• Dropbox Plus

👇 Escolha uma categoria abaixo.
"""

def teclado_catalogo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📺 Streaming", callback_data="streaming")],
        [InlineKeyboardButton("🎮 Games", callback_data="games")],
        [InlineKeyboardButton("🤖 Apps", callback_data="apps")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="voltar")]
    ])
