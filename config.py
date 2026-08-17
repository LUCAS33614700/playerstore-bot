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
# Em serviços como o Railway, o disco do container é
# apagado a cada novo deploy — só o que está em um Volume
# persistente sobrevive. Por isso o caminho do banco pode
# ser sobrescrito pela variável de ambiente DATABASE_PATH,
# apontando pra dentro do volume (ex: /data/bot.db).
# Sem essa variável, continua usando "bot.db" na pasta do
# projeto, como sempre foi.

DATABASE_NAME = os.getenv(
    "DATABASE_PATH",
    "bot.db",
)

_pasta_banco = os.path.dirname(DATABASE_NAME)

if _pasta_banco:
    os.makedirs(_pasta_banco, exist_ok=True)


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
    "https://t.me/PLAYERSTOREGRUPO"
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
