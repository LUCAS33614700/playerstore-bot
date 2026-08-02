import requests

from config import ASAAS_API_KEY


# =========================================================
# CONFIGURAÇÃO ASAAS
# =========================================================

ASAAS_BASE_URL = "https://api.asaas.com/v3"


# =========================================================
# HEADERS
# =========================================================

def headers():
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": ASAAS_API_KEY,
    }


# =========================================================
# VERIFICAR API
# =========================================================

def verificar_asaas():

    if not ASAAS_API_KEY:
        raise ValueError(
            "ASAAS_API_KEY não configurada."
        )

    resposta = requests.get(
        f"{ASAAS_BASE_URL}/customers",
        headers=headers(),
        params={
            "limit": 1
        },
        timeout=30
    )

    if resposta.status_code != 200:
        raise Exception(
            "Não foi possível conectar ao Asaas: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    return True


# =========================================================
# CRIAR CLIENTE
# =========================================================

def criar_cliente(
    nome,
    cpf_cnpj=None,
    email=None,
    telefone=None
):

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
            "Erro ao criar cliente no Asaas: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    return resposta.json()


# =========================================================
# BUSCAR CLIENTE POR CPF/CNPJ
# =========================================================

def buscar_cliente_por_cpf(cpf_cnpj):

    url = f"{ASAAS_BASE_URL}/customers"

    resposta = requests.get(
        url,
        headers=headers(),
        params={
            "cpfCnpj": cpf_cnpj,
            "limit": 10
        },
        timeout=30
    )

    if resposta.status_code != 200:

        raise Exception(
            "Erro ao buscar cliente no Asaas: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    dados = resposta.json()

    clientes = dados.get(
        "data",
        []
    )

    if clientes:
        return clientes[0]

    return None


# =========================================================
# BUSCAR CLIENTE POR E-MAIL
# =========================================================

def buscar_cliente_por_email(email):

    url = f"{ASAAS_BASE_URL}/customers"

    resposta = requests.get(
        url,
        headers=headers(),
        params={
            "email": email,
            "limit": 10
        },
        timeout=30
    )

    if resposta.status_code != 200:

        raise Exception(
            "Erro ao buscar cliente por e-mail: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    dados = resposta.json()

    clientes = dados.get(
        "data",
        []
    )

    if clientes:
        return clientes[0]

    return None


# =========================================================
# OBTER CLIENTE
# =========================================================

def obter_cliente(
    nome,
    email=None,
    cpf_cnpj=None
):

    # -----------------------------------------------------
    # Primeiro tenta encontrar por CPF/CNPJ
    # -----------------------------------------------------

    if cpf_cnpj:

        cliente = buscar_cliente_por_cpf(
            cpf_cnpj
        )

        if cliente:
            return cliente

    # -----------------------------------------------------
    # Depois tenta encontrar por e-mail
    # -----------------------------------------------------

    if email:

        cliente = buscar_cliente_por_email(
            email
        )

        if cliente:
            return cliente

    # -----------------------------------------------------
    # Se não encontrou, cria
    # -----------------------------------------------------

    return criar_cliente(
        nome=nome,
        cpf_cnpj=cpf_cnpj,
        email=email
    )


# =========================================================
# CRIAR COBRANÇA PIX
# =========================================================

def criar_cobranca_pix(
    valor,
    descricao,
    cliente_id
):

    url = f"{ASAAS_BASE_URL}/payments"

    dados = {
        "customer": cliente_id,
        "billingType": "PIX",
        "value": round(float(valor), 2),
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
            "Erro ao criar cobrança no Asaas: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    return resposta.json()


# =========================================================
# QR CODE PIX
# =========================================================

def obter_qrcode_pix(
    cobranca_id
):

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
            "Erro ao obter QR Code PIX: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    return resposta.json()


# =========================================================
# CONSULTAR COBRANÇA
# =========================================================

def consultar_cobranca(
    cobranca_id
):

    url = (
        f"{ASAAS_BASE_URL}/payments/"
        f"{cobranca_id}"
    )

    resposta = requests.get(
        url,
        headers=headers(),
        timeout=30
    )

    if resposta.status_code != 200:

        raise Exception(
            "Erro ao consultar cobrança: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    return resposta.json()


# =========================================================
# CANCELAR COBRANÇA
# =========================================================

def cancelar_cobranca(
    cobranca_id
):

    url = (
        f"{ASAAS_BASE_URL}/payments/"
        f"{cobranca_id}"
    )

    resposta = requests.delete(
        url,
        headers=headers(),
        timeout=30
    )

    if resposta.status_code not in (200, 204):

        raise Exception(
            "Erro ao cancelar cobrança: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    if resposta.text:
        return resposta.json()

    return True
