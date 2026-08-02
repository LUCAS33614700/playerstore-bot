import os
import requests


# =========================================================
# CONFIGURAÇÃO
# =========================================================

PUSHINPAY_TOKEN = os.getenv("PUSHINPAY_TOKEN", "")

BASE_URL = "https://api.pushinpay.com.br/api"


# =========================================================
# HEADERS
# =========================================================

def headers():

    if not PUSHINPAY_TOKEN:
        raise ValueError(
            "PUSHINPAY_TOKEN não configurado."
        )

    return {
        "Authorization": f"Bearer {PUSHINPAY_TOKEN}",
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
        round(float(valor) * 100)
    )

    if valor_centavos <= 0:
        raise ValueError(
            "Valor do PIX inválido."
        )

    dados = {
        "value": valor_centavos,
        "split_rules": [],
    }

    if webhook_url:
        dados["webhook_url"] = webhook_url

    resposta = requests.post(
        f"{BASE_URL}/pix/cashIn",
        headers=headers(),
        json=dados,
        timeout=30,
    )

    print(
        "PUSHINPAY CRIAR PIX:",
        resposta.status_code,
        resposta.text,
    )

    resposta.raise_for_status()

    return resposta.json()


# =========================================================
# CONSULTAR PIX
# =========================================================

def consultar_pix(
    transacao_id,
):

    if not transacao_id:
        raise ValueError(
            "ID da transação não informado."
        )

    resposta = requests.get(
        f"{BASE_URL}/transactions/{transacao_id}",
        headers=headers(),
        timeout=30,
    )

    print(
        "PUSHINPAY CONSULTAR PIX:",
        resposta.status_code,
        resposta.text,
    )

    resposta.raise_for_status()

    return resposta.json()


# =========================================================
# PEGAR STATUS
# =========================================================

def status_pix(
    transacao_id,
):

    dados = consultar_pix(
        transacao_id
    )

    return dados.get(
        "status",
        ""
    )


# =========================================================
# VERIFICAR SE ESTÁ PAGO
# =========================================================

def pix_pago(
    transacao_id,
):

    status = status_pix(
        transacao_id
    )

    return status.lower() == "paid"
