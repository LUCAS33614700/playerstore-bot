import os
import requests

from log import log_info


# =========================================================
# CONFIGURAÇÃO
# =========================================================

PUSHINPAY_TOKEN = os.getenv(
    "PUSHINPAY_TOKEN",
    "",
)

BASE_URL = (
    "https://api.pushinpay.com.br/api"
)


# =========================================================
# HEADERS
# =========================================================

def headers():

    if not PUSHINPAY_TOKEN:

        raise ValueError(
            "PUSHINPAY_TOKEN não configurado."
        )

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

    valor_centavos = int(
        round(
            float(valor) * 100
        )
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

        dados["webhook_url"] = (
            webhook_url
        )

    resposta = requests.post(
        f"{BASE_URL}/pix/cashIn",
        headers=headers(),
        json=dados,
        timeout=30,
    )

    log_info(
        "PUSHINPAY CRIAR PIX:",
        resposta.status_code,
    )

    resposta.raise_for_status()

    dados_resposta = (
        resposta.json()
    )

    if not isinstance(
        dados_resposta,
        dict,
    ):

        raise ValueError(
            "Resposta inválida da PushinPay."
        )

    log_info(
        "PUSHINPAY CRIAR PIX OK:",
        dados_resposta.get("id"),
        dados_resposta.get("status"),
    )

    return dados_resposta


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
        f"{BASE_URL}/transactions/"
        f"{transacao_id}",
        headers=headers(),
        timeout=30,
    )

    log_info(
        "PUSHINPAY CONSULTAR PIX:",
        resposta.status_code,
    )

    resposta.raise_for_status()

    dados = resposta.json()

    if not isinstance(
        dados,
        dict,
    ):

        raise ValueError(
            "Resposta inválida da PushinPay."
        )

    log_info(
        "PUSHINPAY CONSULTAR PIX OK:",
        dados.get("id"),
        dados.get("status"),
    )

    return dados


# =========================================================
# STATUS
# =========================================================

def status_pix(
    transacao_id,
):

    dados = consultar_pix(
        transacao_id
    )

    return str(
        dados.get(
            "status",
            "",
        )
    ).lower()


# =========================================================
# PIX PAGO
# =========================================================

def pix_pago(
    transacao_id,
):

    return (
        status_pix(
            transacao_id
        )
        == "paid"
    )
