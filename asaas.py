import requests

from config import ASAAS_API_KEY


ASAAS_BASE_URL = "https://api.asaas.com/v3"


def headers():
    if not ASAAS_API_KEY:
        raise ValueError("ASAAS_API_KEY não configurada")

    return {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": ASAAS_API_KEY,
    }


def criar_cliente(nome, cpf_cnpj=None, email=None):
    url = f"{ASAAS_BASE_URL}/customers"

    dados = {
        "name": nome,
    }

    if cpf_cnpj:
        dados["cpfCnpj"] = cpf_cnpj

    if email:
        dados["email"] = email

    resposta = requests.post(
        url,
        headers=headers(),
        json=dados,
        timeout=30
    )

    if resposta.status_code not in (200, 201):
        raise Exception(
            f"Erro ao criar cliente no Asaas: "
            f"{resposta.status_code} - {resposta.text}"
        )

    return resposta.json()


def criar_cobranca_pix(valor, descricao, cliente_id):
    url = f"{ASAAS_BASE_URL}/payments"

    dados = {
        "customer": cliente_id,
        "billingType": "PIX",
        "value": float(valor),
        "description": descricao,
    }

    resposta = requests.post(
        url,
        headers=headers(),
        json=dados,
        timeout=30
    )

    if resposta.status_code not in (200, 201):
        raise Exception(
            f"Erro ao criar cobrança no Asaas: "
            f"{resposta.status_code} - {resposta.text}"
        )

    return resposta.json()


def obter_qrcode_pix(cobranca_id):
    url = (
        f"{ASAAS_BASE_URL}/payments/"
        f"{cobranca_id}/pixQrCode"
    )

    resposta = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    if resposta.status_code != 200:
        raise Exception(
            f"Erro ao obter PIX: "
            f"{resposta.status_code} - {resposta.text}"
        )

    return resposta.json()


def consultar_cobranca(cobranca_id):
    url = f"{ASAAS_BASE_URL}/payments/{cobranca_id}"

    resposta = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    if resposta.status_code != 200:
        raise Exception(
            f"Erro ao consultar cobrança: "
            f"{resposta.status_code} - {resposta.text}"
        )

    return resposta.json()
