import os


# =========================
# CONFIGURAÇÕES DO BOT
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "0"
    )
)


# =========================
# BANCO DE DADOS
# =========================

DATABASE_NAME = "bot.db"


# =========================
# DADOS DA LOJA
# =========================

NOME_DA_LOJA = "PLAYER STORE"


# =========================
# PUSHINPAY
# =========================

PUSHINPAY_TOKEN = os.getenv(
    "PUSHINPAY_TOKEN",
    ""
)


# =========================
# SUPORTE
# =========================

SUPORTE_USERNAME = os.getenv(
    "SUPORTE_USERNAME",
    ""
)


# =========================
# GRUPO DE CLIENTES
# =========================

GRUPO_CLIENTES = os.getenv(
    "GRUPO_CLIENTES",
    "https://t.me/PLAYERSTORYREFERENCIA"
)


# =========================
# VERIFICAÇÃO
# =========================

def verificar_configuracao():

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN não configurado."
        )

    if ADMIN_ID == 0:

        raise ValueError(
            "ADMIN_ID não configurado."
        )

    if not PUSHINPAY_TOKEN:

        raise ValueError(
            "PUSHINPAY_TOKEN não configurado."
        )

    return True
