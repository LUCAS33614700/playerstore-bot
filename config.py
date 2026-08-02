import os


# =========================
# CONFIGURAÇÕES DO BOT
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


# =========================
# BANCO DE DADOS
# =========================

DATABASE_NAME = "bot.db"


# =========================
# DADOS DA LOJA
# =========================

NOME_DA_LOJA = "PLAYER STORE"


# =========================
# PIX
# =========================

PIX_KEY = os.getenv("PIX_KEY", "")


# =========================
# ASAAS
# =========================

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")


# =========================
# SUPORTE
# =========================

SUPORTE_USERNAME = os.getenv("SUPORTE_USERNAME", "")


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
            "BOT_TOKEN não configurado"
        )

    if ADMIN_ID == 0:
        raise ValueError(
            "ADMIN_ID não configurado"
        )

    if not ASAAS_API_KEY:
        raise ValueError(
            "ASAAS_API_KEY não configurado"
        )

    return True
