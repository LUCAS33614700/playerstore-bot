from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    verificar_configuracao,
)

from database import (
    criar_tabelas,
    criar_usuario,
    consultar_usuario,
    consultar_saldo,
    conectar,
    retirar_saldo,
    criar_pagamento,
    consultar_pagamento,
    atualizar_status_pagamento,
)

from menu import menu_principal

from catalogo import (
    menu_catalogo,
    buscar_produto,
)

from asaas import (
    criar_cobranca_pix,
    obter_qrcode_pix,
    consultar_cobranca,
)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

GRUPO_CLIENTES = (
    "https://t.me/PLAYERSTORYREFERENCIA"
)


# =========================================================
# CLIENTE ASAAS
# =========================================================

def obter_ou_criar_cliente_asaas(usuario):
    """
    Procura o cliente no Asaas pelo externalReference.
    Se não encontrar, cria automaticamente.
    """

    import requests

    from config import ASAAS_API_KEY

    if not ASAAS_API_KEY:
        raise Exception(
            "ASAAS_API_KEY não configurada."
        )

    base_url = "https://api.asaas.com/v3"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": ASAAS_API_KEY,
    }

    external_reference = (
        f"telegram_{usuario.id}"
    )

    # -----------------------------------------------------
    # PROCURAR CLIENTE EXISTENTE
    # -----------------------------------------------------

    url_busca = (
        f"{base_url}/customers"
    )

    parametros = {
        "externalReference": external_reference,
        "limit": 100,
    }

    resposta = requests.get(
        url_busca,
        headers=headers,
        params=parametros,
        timeout=30,
    )

    if resposta.status_code != 200:
        raise Exception(
            "Erro ao consultar clientes Asaas: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    dados = resposta.json()

    clientes = dados.get(
        "data",
        []
    )

    if clientes:
        return clientes[0]["id"]

    # -----------------------------------------------------
    # CRIAR NOVO CLIENTE
    # -----------------------------------------------------

    nome = (
        usuario.full_name
        or usuario.first_name
        or f"Cliente {usuario.id}"
    )

    dados_cliente = {
        "name": nome,
        "externalReference": external_reference,
        "notificationDisabled": True,
    }

    if usuario.username:
        dados_cliente["name"] = (
            f"{nome} (@{usuario.username})"
        )

    resposta = requests.post(
        url_busca,
        headers=headers,
        json=dados_cliente,
        timeout=30,
    )

    if resposta.status_code not in (
        200,
        201,
    ):
        raise Exception(
            "Erro ao criar cliente Asaas: "
            f"{resposta.status_code} - "
            f"{resposta.text}"
        )

    cliente = resposta.json()

    cliente_id = cliente.get("id")

    if not cliente_id:
        raise Exception(
            "Asaas não retornou o ID do cliente."
        )

    return cliente_id


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    criar_usuario(
        usuario.id,
        usuario.first_name or "",
        usuario.username or "",
    )

    context.user_data[
        "aguardando_valor"
    ] = False

    texto = (
        f"👋 Olá, {usuario.first_name}!\n\n"
        "🛒 Bem-vindo à PLAYER STORE!\n\n"
        "Escolha uma opção abaixo:"
    )

    await update.message.reply_text(
        texto,
        reply_markup=menu_principal(),
    )


# =========================================================
# COMPRA DE PRODUTO
# =========================================================

async def comprar_produto(
    query,
    produto_id,
    usuario_id,
):

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        await query.answer(
            "❌ Produto não encontrado.",
            show_alert=True,
        )

        return

    (
        _,
        nome,
        descricao,
        preco,
        estoque,
    ) = produto

    if estoque <= 0:

        await query.answer(
            "📦 Produto sem estoque.",
            show_alert=True,
        )

        return

    saldo = consultar_saldo(
        usuario_id
    )

    if saldo < preco:

        await query.answer(
            f"❌ Saldo insuficiente.\n"
            f"Seu saldo: R$ {saldo:.2f}\n"
            f"Preço: R$ {preco:.2f}",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # RETIRAR SALDO
    # -----------------------------------------------------

    sucesso = retirar_saldo(
        usuario_id,
        preco,
    )

    if not sucesso:

        await query.answer(
            "❌ Não foi possível realizar a compra.",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # ATUALIZAR ESTOQUE E PEDIDO
    # -----------------------------------------------------

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE produtos
        SET estoque = estoque - 1
        WHERE id = ?
        AND estoque > 0
        """,
        (produto_id,),
    )

    estoque_atualizado = (
        cursor.rowcount > 0
    )

    if not estoque_atualizado:

        conn.rollback()
        conn.close()

        from database import adicionar_saldo

        adicionar_saldo(
            usuario_id,
            preco,
        )

        await query.answer(
            "❌ O produto ficou sem estoque.",
            show_alert=True,
        )

        return

    cursor.execute(
        """
        INSERT INTO pedidos
        (
            usuario_id,
            produto_id,
            quantidade,
            valor,
            status
        )
        VALUES (?, ?, 1, ?, 'pago')
        """,
        (
            usuario_id,
            produto_id,
            preco,
        ),
    )

    conn.commit()
    conn.close()

    novo_saldo = consultar_saldo(
        usuario_id
    )

    await query.edit_message_text(
        f"✅ *Compra realizada!*\n\n"
        f"🛒 Produto: {nome}\n"
        f"💰 Valor: R$ {preco:.2f}\n"
        f"💳 Saldo restante: "
        f"R$ {novo_saldo:.2f}\n\n"
        "📦 Seu pedido foi registrado.",
        reply_markup=menu_principal(),
        parse_mode="Markdown",
    )


# =========================================================
# PEDIR VALOR DO SALDO
# =========================================================

async def pedir_valor_saldo(
    query,
    context,
):

    context.user_data[
        "aguardando_valor"
    ] = True

    await query.edit_message_text(
        "💵 *ADICIONAR SALDO*\n\n"
        "Digite o valor que deseja adicionar.\n\n"
        "Exemplo:\n"
        "`10`\n"
        "`25.50`\n"
        "`100`",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Voltar",
                        callback_data="voltar_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# PROCESSAR VALOR DO SALDO
# =========================================================

async def processar_valor_saldo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get(
        "aguardando_valor"
    ):
        return

    if not update.message:
        return

    texto = update.message.text.strip()

    # -----------------------------------------------------
    # CONVERTER VALOR
    # -----------------------------------------------------

    try:

        valor = float(
            texto.replace(",", ".")
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Digite apenas um valor válido.\n\n"
            "Exemplo: `10` ou `25.50`",
            parse_mode="Markdown",
        )

        return

    # -----------------------------------------------------
    # VALIDAR VALOR
    # -----------------------------------------------------

    if valor < 1:

        await update.message.reply_text(
            "❌ O valor mínimo é R$ 1,00."
        )

        return

    if valor > 10000:

        await update.message.reply_text(
            "❌ O valor máximo é R$ 10.000,00."
        )

        return

    # -----------------------------------------------------
    # ARREDONDAR
    # -----------------------------------------------------

    valor = round(
        valor,
        2,
    )

    context.user_data[
        "aguardando_valor"
    ] = False

    usuario = update.effective_user

    # -----------------------------------------------------
    # MENSAGEM DE ESPERA
    # -----------------------------------------------------

    mensagem = await update.message.reply_text(
        "⏳ Gerando sua cobrança PIX..."
    )

    try:

        # -------------------------------------------------
        # CRIAR / LOCALIZAR CLIENTE ASAAS
        # -------------------------------------------------

        cliente_id = (
            obter_ou_criar_cliente_asaas(
                usuario
            )
        )

        # -------------------------------------------------
        # CRIAR COBRANÇA
        # -------------------------------------------------

        cobranca = criar_cobranca_pix(
            valor=valor,
            descricao=(
                f"Adição de saldo - "
                f"Telegram {usuario.id}"
            ),
            cliente_id=cliente_id,
        )

        cobranca_id = cobranca.get(
            "id"
        )

        if not cobranca_id:

            raise Exception(
                "Asaas não retornou o ID "
                "da cobrança."
            )

        # -------------------------------------------------
        # REGISTRAR PAGAMENTO
        # -------------------------------------------------

        criar_pagamento(
            usuario.id,
            valor,
            cobranca_id,
        )

        # -------------------------------------------------
        # OBTER QR CODE
        # -------------------------------------------------

        pix = obter_qrcode_pix(
            cobranca_id
        )

        payload = pix.get(
            "payload"
        )

        if not payload:

            raise Exception(
                "Asaas não retornou o "
                "Pix Copia e Cola."
            )

        expiration = pix.get(
            "expirationDate",
            "",
        )

        # -------------------------------------------------
        # MONTAR RESPOSTA
        # -------------------------------------------------

        texto_pix = (
            "💳 *PAGAMENTO PIX*\n\n"
            f"💰 Valor: *R$ {valor:.2f}*\n\n"
            "📋 *Pix Copia e Cola:*\n\n"
            f"`{payload}`\n\n"
            "👇 Copie o código acima e "
            "pague pelo seu banco.\n\n"
            "⏳ Após o pagamento, o saldo "
            "será liberado quando a cobrança "
            "for confirmada pelo Asaas."
        )

        if expiration:

            texto_pix += (
                f"\n\n⏰ Expiração: "
                f"{expiration}"
            )

        # -------------------------------------------------
        # BOTÕES
        # -------------------------------------------------

        botoes = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 Consultar pagamento",
                        callback_data=(
                            f"consultar_pagamento_"
                            f"{cobranca_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Voltar ao menu",
                        callback_data=(
                            "voltar_menu"
                        ),
                    )
                ],
            ]
        )

        await mensagem.edit_text(
            texto_pix,
            reply_markup=botoes,
            parse_mode="Markdown",
        )

    except Exception as erro:

        print(
            "ERRO AO GERAR PIX:"
        )

        print(
            repr(erro)
        )

        await mensagem.edit_text(
            "❌ *Não foi possível gerar "
            "a cobrança PIX.*\n\n"
            "Verifique a configuração da "
            "API do Asaas e tente novamente.",
            parse_mode="Markdown",
        )


# =========================================================
# CONSULTAR PAGAMENTO
# =========================================================

async def verificar_pagamento(
    query,
    cobranca_id,
):

    try:

        pagamento = (
            consultar_pagamento(
                cobranca_id
            )
        )

        if not pagamento:

            await query.answer(
                "❌ Pagamento não encontrado.",
                show_alert=True,
            )

            return

        usuario_id = pagamento[1]
        valor = pagamento[2]
        status_banco = pagamento[4]

        cobranca = (
            consultar_cobranca(
                cobranca_id
            )
        )

        status_asaas = (
            cobranca.get(
                "status",
                ""
            )
        )

        print(
            f"Pagamento {cobranca_id}: "
            f"{status_asaas}"
        )

        # -------------------------------------------------
        # PAGAMENTO RECEBIDO
        # -------------------------------------------------

        if status_asaas in (
            "RECEIVED",
            "CONFIRMED",
        ):

            if status_banco != "pago":

                atualizar_status_pagamento(
                    cobranca_id,
                    "pago",
                )

                from database import (
                    adicionar_saldo,
                )

                adicionar_saldo(
                    usuario_id,
                    valor,
                )

                saldo = consultar_saldo(
                    usuario_id
                )

                await query.edit_message_text(
                    "✅ *PAGAMENTO CONFIRMADO!*\n\n"
                    f"💰 Valor recebido: "
                    f"R$ {valor:.2f}\n\n"
                    f"💳 Novo saldo: "
                    f"R$ {saldo:.2f}\n\n"
                    "🎉 Seu saldo foi adicionado "
                    "com sucesso!",
                    reply_markup=menu_principal(),
                    parse_mode="Markdown",
                )

                return

            saldo = consultar_saldo(
                usuario_id
            )

            await query.edit_message_text(
                "✅ *PAGAMENTO JÁ CONFIRMADO*\n\n"
                f"💰 Valor: R$ {valor:.2f}\n"
                f"💳 Saldo atual: "
                f"R$ {saldo:.2f}",
                reply_markup=menu_principal(),
                parse_mode="Markdown",
            )

            return

        # -------------------------------------------------
        # PAGAMENTO PENDENTE
        # -------------------------------------------------

        if status_asaas in (
            "PENDING",
            "AWAITING_RISK_ANALYSIS",
        ):

            await query.answer(
                "⏳ O pagamento ainda está pendente.",
                show_alert=True,
            )

            return

        # -------------------------------------------------
        # PAGAMENTO CANCELADO
        # -------------------------------------------------

        if status_asaas in (
            "CANCELED",
            "REFUNDED",
            "REFUND_REQUESTED",
        ):

            atualizar_status_pagamento(
                cobranca_id,
                status_asaas.lower(),
            )

            await query.edit_message_text(
                "❌ *PAGAMENTO NÃO CONCLUÍDO*\n\n"
                f"Status: {status_asaas}\n\n"
                "Nenhum saldo foi adicionado.",
                reply_markup=menu_principal(),
                parse_mode="Markdown",
            )

            return

        # -------------------------------------------------
        # OUTRO STATUS
        # -------------------------------------------------

        await query.answer(
            f"Status atual: {status_asaas}",
            show_alert=True,
        )

    except Exception as erro:

        print(
            "ERRO AO CONSULTAR PAGAMENTO:"
        )

        print(
            repr(erro)
        )

        await query.answer(
            "❌ Erro ao consultar o pagamento.",
            show_alert=True,
        )


# =========================================================
# BOTÕES
# =========================================================

async def botoes(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    usuario_id = query.from_user.id

    acao = query.data

    # -----------------------------------------------------
    # CONSULTAR PAGAMENTO
    # -----------------------------------------------------

    if acao.startswith(
        "consultar_pagamento_"
    ):

        cobranca_id = (
            acao.replace(
                "consultar_pagamento_",
                "",
                1,
            )
        )

        await verificar_pagamento(
            query,
            cobranca_id,
        )

        return

    # -----------------------------------------------------
    # CATÁLOGO
    # -----------------------------------------------------

    if acao == "catalogo":

        await query.edit_message_text(
            "🛒 *LOGINS | CONTAS PREMIUM*\n\n"
            "Escolha um produto:",
            reply_markup=menu_catalogo(),
            parse_mode="Markdown",
        )

    # -----------------------------------------------------
    # PRODUTO
    # -----------------------------------------------------

    elif acao.startswith(
        "produto_"
    ):

        produto_id = int(
            acao.split("_")[1]
        )

        produto = buscar_produto(
            produto_id
        )

        if not produto:

            await query.answer(
                "❌ Produto não encontrado.",
                show_alert=True,
            )

            return

        (
            _,
            nome,
            descricao,
            preco,
            estoque,
        ) = produto

        texto = (
            f"🛒 *{nome}*\n\n"
            f"📝 {descricao or 'Sem descrição'}\n\n"
            f"💰 Preço: R$ {preco:.2f}\n"
            f"📦 Estoque: {estoque}"
        )

        botoes_compra = [
            [
                InlineKeyboardButton(
                    "🛒 Comprar",
                    callback_data=(
                        f"comprar_{produto_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="catalogo",
                )
            ],
        ]

        await query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(
                botoes_compra
            ),
            parse_mode="Markdown",
        )

    # -----------------------------------------------------
    # COMPRAR
     # -----------------------------------------------------
    # COMPRAR PRODUTO
    # -----------------------------------------------------

    elif acao.startswith("comprar_"):

        produto_id = int(
            acao.split("_")[1]
        )

        await comprar_produto(
            query,
            produto_id,
            usuario_id,
        )

    # -----------------------------------------------------
    # ADICIONAR SALDO
    # -----------------------------------------------------

    elif acao == "adicionar_saldo":

        await pedir_valor_saldo(
            query,
            context,
        )

    # -----------------------------------------------------
    # SALDO
    # -----------------------------------------------------

    elif acao == "saldo":

        saldo = consultar_saldo(
            usuario_id
        )

        await query.edit_message_text(
            "💳 *MEU SALDO*\n\n"
            f"💰 Saldo atual: R$ {saldo:.2f}\n\n"
            "Escolha uma opção:",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💵 Adicionar saldo",
                            callback_data="adicionar_saldo",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ Voltar",
                            callback_data="voltar_menu",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
)
