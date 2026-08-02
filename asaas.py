import requests
from datetime import date, timedelta

from config import ASAAS_API_KEY


# =========================================================
# CONFIGURAÇÃO ASAAS
# =========================================================

ASAAS_BASE_URL = "https://api.asaas.com/v3"


# =========================================================
# HEADERS
# =========================================================

def headers():

    if not ASAAS_API_KEY:
        raise ValueError(
            "ASAAS_API_KEY não configurada."
        )

    return {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": ASAAS_API_KEY,
    }


# =========================================================
# VERIFICAR API
# =========================================================

def verificar_asaas():

    resposta = requests.get(
        f"{ASAAS_BASE_URL}/customers",
        headers=headers(),
        params={
            "limit": 1
        },
        timeout=30,
    )

    if resposta.status_code != 200:

        raise Exception(
            "Não foi possível conectar ao Asaas: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    return True


# =========================================================
# LIMPAR CPF / CNPJ
# =========================================================

def limpar_documento(documento):

    if not documento:
        return ""

    return "".join(
        caractere
        for caractere in documento
        if caractere.isdigit()
    )


# =========================================================
# VALIDAR CPF
# =========================================================

def validar_cpf(cpf):

    cpf = limpar_documento(cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    soma = 0

    for i in range(9):
        soma += int(cpf[i]) * (10 - i)

    resto = soma % 11

    digito1 = 0 if resto < 2 else 11 - resto

    if int(cpf[9]) != digito1:
        return False

    soma = 0

    for i in range(10):
        soma += int(cpf[i]) * (11 - i)

    resto = soma % 11

    digito2 = 0 if resto < 2 else 11 - resto

    if int(cpf[10]) != digito2:
        return False

    return True


# =========================================================
# VALIDAR CNPJ
# =========================================================

def validar_cnpj(cnpj):

    cnpj = limpar_documento(cnpj)

    if len(cnpj) != 14:
        return False

    if cnpj == cnpj[0] * 14:
        return False

    numeros = [int(x) for x in cnpj]

    pesos1 = [
        5, 4, 3, 2,
        9, 8, 7, 6,
        5, 4, 3, 2
    ]

    soma = sum(
        numeros[i] * pesos1[i]
        for i in range(12)
    )

    resto = soma % 11

    digito1 = 0 if resto < 2 else 11 - resto

    if numeros[12] != digito1:
        return False

    pesos2 = [
        6, 5, 4, 3, 2,
        9, 8, 7, 6,
        5, 4, 3, 2
    ]

    soma = sum(
        numeros[i] * pesos2[i]
        for i in range(13)
    )

    resto = soma % 11

    digito2 = 0 if resto < 2 else 11 - resto

    if numeros[13] != digito2:
        return False

    return True


# =========================================================
# VALIDAR DOCUMENTO
# =========================================================

def validar_documento(documento):

    documento = limpar_documento(documento)

    if len(documento) == 11:
        return validar_cpf(documento)

    if len(documento) == 14:
        return validar_cnpj(documento)

    return False


# =========================================================
# CRIAR CLIENTE
# =========================================================

def criar_cliente(
    nome,
    cpf_cnpj,
    email=None,
    telefone=None,
    external_reference=None,
):

    cpf_cnpj = limpar_documento(
        cpf_cnpj
    )

    if not validar_documento(cpf_cnpj):

        raise ValueError(
            "CPF ou CNPJ inválido."
        )

    url = (
        f"{ASAAS_BASE_URL}/customers"
    )

    dados = {
        "name": nome,
        "cpfCnpj": cpf_cnpj,
        "notificationDisabled": True,
    }

    if email:
        dados["email"] = email

    if telefone:
        dados["mobilePhone"] = telefone

    if external_reference:

        dados[
            "externalReference"
        ] = external_reference

    resposta = requests.post(
        url,
        headers=headers(),
        json=dados,
        timeout=30,
    )

    if resposta.status_code not in (
        200,
        201,
    ):

        raise Exception(
            "Erro ao criar cliente no Asaas: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    return resposta.json()


# =========================================================
# BUSCAR CLIENTE POR CPF / CNPJ
# =========================================================

def buscar_cliente_por_cpf(
    cpf_cnpj
):

    cpf_cnpj = limpar_documento(
        cpf_cnpj
    )

    url = (
        f"{ASAAS_BASE_URL}/customers"
    )

    resposta = requests.get(
        url,
        headers=headers(),
        params={
            "cpfCnpj": cpf_cnpj,
            "limit": 10,
        },
        timeout=30,
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
        [],
    )

    if clientes:
        return clientes[0]

    return None


# =========================================================
# BUSCAR CLIENTE POR EXTERNAL REFERENCE
# =========================================================

def buscar_cliente_por_external_reference(
    external_reference
):

    url = (
        f"{ASAAS_BASE_URL}/customers"
    )

    resposta = requests.get(
        url,
        headers=headers(),
        params={
            "externalReference": (
                external_reference
            ),
            "limit": 100,
        },
        timeout=30,
    )

    if resposta.status_code != 200:

        raise Exception(
            "Erro ao buscar cliente por "
            "externalReference: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    dados = resposta.json()

    clientes = dados.get(
        "data",
        [],
    )

    if clientes:
        return clientes[0]

    return None


# =========================================================
# OBTER OU CRIAR CLIENTE
# =========================================================

def obter_ou_criar_cliente(
    nome,
    cpf_cnpj,
    email=None,
    telefone=None,
    external_reference=None,
):

    cpf_cnpj = limpar_documento(
        cpf_cnpj
    )

    # -----------------------------------------------------
    # VALIDAR DOCUMENTO
    # -----------------------------------------------------

    if not validar_documento(cpf_cnpj):

        raise ValueError(
            "CPF ou CNPJ inválido."
        )

    # -----------------------------------------------------
    # PRIMEIRO: CPF / CNPJ
    # -----------------------------------------------------

    cliente = buscar_cliente_por_cpf(
        cpf_cnpj
    )

    if cliente:

        return cliente

    # -----------------------------------------------------
    # SEGUNDO: EXTERNAL REFERENCE
    # -----------------------------------------------------

    if external_reference:

        cliente = (
            buscar_cliente_por_external_reference(
                external_reference
            )
        )

        if cliente:

            # Se encontrou um cliente antigo
            # sem CPF/CNPJ, devolvemos o cliente.
            # A cobrança mostrará o erro do Asaas
            # caso a conta exija atualização.

            return cliente

    # -----------------------------------------------------
    # CRIAR CLIENTE
    # -----------------------------------------------------

    return criar_cliente(
        nome=nome,
        cpf_cnpj=cpf_cnpj,
        email=email,
        telefone=telefone,
        external_reference=(
            external_reference
        ),
    )


# =========================================================
# CRIAR COBRANÇA PIX
# =========================================================

def criar_cobranca_pix(
    valor,
    descricao,
    cliente_id,
    external_reference=None,
):

    url = (
        f"{ASAAS_BASE_URL}/payments"
    )

    # -----------------------------------------------------
    # VENCIMENTO
    # -----------------------------------------------------
    #
    # Usaremos amanhã como vencimento.
    #
    # A API do Asaas exige dueDate na criação
    # da cobrança.
    #

    vencimento = (
        date.today()
        + timedelta(days=1)
    )

    dados = {
        "customer": cliente_id,
        "billingType": "PIX",
        "value": round(
            float(valor),
            2,
        ),
        "dueDate": (
            vencimento.isoformat()
        ),
        "description": descricao,
    }

    if external_reference:

        dados[
            "externalReference"
        ] = external_reference

    print(
        "CRIANDO COBRANÇA ASAAS:"
    )

    print(
        dados
    )

    resposta = requests.post(
        url,
        headers=headers(),
        json=dados,
        timeout=30,
    )

    if resposta.status_code not in (
        200,
        201,
    ):

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
        timeout=30,
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
        timeout=30,
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
        timeout=30,
    )

    if resposta.status_code not in (
        200,
        204,
    ):

        raise Exception(
            "Erro ao cancelar cobrança: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    if resposta.text:

        return resposta.json()

    return True
