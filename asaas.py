import requests

from config import ASAAS_API_KEY


ASAAS_BASE_URL = "https://api.asaas.com/v3"


def headers():
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": ASAAS_API_KEY,
    }


def verificar_api():
    """
    Verifica se a chave do Asaas está configurada.
    """
    if not ASAAS_API_KEY:
        raise ValueError("ASAAS_API_KEY não configurada.")

    return True


def criar_cliente(
    nome,
    cpf_cnpj=None,
    email=None,
    telefone=None
):
    """
    Cria um cliente no Asaas.
    """

    verificar_api()

    url = f"{ASAAS_BASE_URL}/customers"

    dados = {
        "name": nome
    }

    if cpf_cnpj:
        dados["cpfCnpj"] = cpf_cnpj

    if email:
        dados["email"] = email

    if telefone:
        dados["phone"] = telefone

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


def buscar_cliente_por_email(email):
    """
    Procura um cliente existente no Asaas pelo e-mail.
    """

    verificar_api()

    if not email:
        return None

    url = f"{ASAAS_BASE_URL}/customers"

    resposta = requests.get(
        url,
        headers=headers(),
        params={
            "email": email
        },
        timeout=30
    )

    if resposta.status_code != 200:
        raise Exception(
            f"Erro ao consultar cliente no Asaas: "
            f"{resposta.status_code} - {resposta.text}"
        )

    dados = resposta.json()

    clientes = dados.get("data", [])

    if clientes:
        return clientes[0]

    return None


def obter_cliente(cliente_id):
    """
    Consulta um cliente pelo ID do Asaas.
    """

    verificar_api()

    url = f"{ASAAS_BASE_URL}/customers/{cliente_id}"

    resposta = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    if resposta.status_code != 200:
        raise Exception(
            f"Erro ao consultar cliente Asaas: "
            f"{resposta.status_code} - {resposta.text}"
        )

    return resposta.json()


def criar_cobranca_pix(
    valor,
    descricao,
    cliente_id
):
    """
    Cria uma cobrança PIX no Asaas.
    """

    verificar_api()

    url = f"{ASAAS_BASE_URL}/payments"

    dados = {
        "customer": cliente_id,
        "billingType": "PIX",
        "value": float(valor),
        "description": descricao
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
    """
    Obtém o QR Code PIX de uma cobrança.
    """

    verificar_api()

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
    """
    Consulta o status de uma cobrança.
    """

    verificar_api()

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
