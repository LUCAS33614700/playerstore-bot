import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DATABASE_NAME = "bot.db"

NOME_DA_LOJA = "PLAYER STORE"

PIX_KEY = os.getenv("PIX_KEY", "")

SUPORTE_USERNAME = os.getenv("SUPORTE_USERNAME", "")

GRUPO_CLIENTES = os.getenv("GRUPO_CLIENTES", "")

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")


def verificar_configuracao():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN não configurado")

    if ADMIN_ID == 0:
        raise ValueError("ADMIN_ID não configurado")

    if not ASAAS_API_KEY:
        raise ValueError("ASAAS_API_KEY não configurado")

    return True
