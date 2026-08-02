import requests

from config import PUSHINPAY_TOKEN


# =========================================================
# CONFIGURAÇÕES
# =========================================================

BASE_URL = (
    "https://api.pushinpay.com.br"
)


# =========================================================
# HEADERS
# =========================================================

def headers():

    return {
        "Authorization": (
            f"Bearer {PUSHINPAY_TOKEN}"
        ),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


# =========================================================
# CRIAR PIX
# =========================================================

def criar_pix(
    valor,
    webhook_url=None,
):

    # PushinPay trabalha com centavos
    valor_centavos = int(
        round(valor * 100)
    )

    dados = {
        "value": valor_centavos,
        "split_rules": [],
    }

    if webhook_url:

        dados["webhook_url"] = (
            webhook_url
        )

    resposta = requests.post(
        f"{BASE_URL}/api/pix/cashIn",
        headers=headers(),
        json=dados,
        timeout=30,
    )

    print(
        "PUSHINPAY CREATE:",
        resposta.status_code,
        resposta.text,
    )

    resposta.raise_for_status()

    return resposta.json()


# =========================================================
# CONSULTAR TRANSAÇÃO
# =========================================================

def consultar_pix(
    transacao_id,
):

    resposta = requests.get(
        (
            f"{BASE_URL}"
            f"/api/transactions/"
            f"{transacao_id}"
        ),
        headers=headers(),
        timeout=30,
    )

    print(
        "PUSHINPAY STATUS:",
        resposta.status_code,
        resposta.text,
    )

    resposta.raise_for_status()

    return resposta.json()
