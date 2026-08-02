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
    adicionar_saldo,
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
    obter_ou_criar_cliente,
    validar_documento,
)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

GRUPO_CLIENTES = (
    "https://t.me/PLAYERSTORYREFERENCIA"
)


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

    context.user_data[
        "aguardando_documento"
    ] = False

    context.user_data[
        "valor_saldo"
    ] = None

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

    # -----------------------------------------------------
    # VERIFICAR ESTOQUE
    # -----------------------------------------------------

    if estoque <= 0:

        await query.answer(
            "📦 Produto sem estoque.",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # VERIFICAR SALDO
    # -----------------------------------------------------

    saldo = consultar_saldo(
        usuario_id
    )

    if saldo < preco:

        await query.answer(
            f"❌ Saldo insuficiente.\n\n"
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
    # ATUALIZAR ESTOQUE
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
        (
            produto_id,
        ),
    )

    estoque_atualizado = (
        cursor.rowcount > 0
    )

    # -----------------------------------------------------
    # SE NÃO CONSEGUIU ATUALIZAR ESTOQUE
    # -----------------------------------------------------

    if not estoque_atualizado:

        conn.rollback()
        conn.close()

        adicionar_saldo(
            usuario_id,
            preco,
        )

        await query.answer(
            "❌ O produto ficou sem estoque.",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # REGISTRAR PEDIDO
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # NOVO SALDO
    # -----------------------------------------------------

    novo_saldo = consultar_saldo(
        usuario_id
    )

    # -----------------------------------------------------
    # FINALIZAR
    # -----------------------------------------------------

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

    context.user_data[
        "aguardando_documento"
    ] = False

    context.user_data[
        "valor_saldo"
    ] = None

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
                        callback_data=(
                            "voltar_menu"
                        ),
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# PROCESSAR VALOR
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
            "Exemplo:\n"
            "`10`\n"
            "`25.50`\n"
            "`100`",
            parse_mode="Markdown",
        )

        return

    # -----------------------------------------------------
    # VALIDAR MÍNIMO
    # -----------------------------------------------------

    if valor < 1:

        await update.message.reply_text(
            "❌ O valor mínimo é R$ 1,00."
        )

        return

    # -----------------------------------------------------
    # VALIDAR MÁXIMO
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # GUARDAR VALOR
    # -----------------------------------------------------

    context.user_data[
        "valor_saldo"
    ] = valor

    context.user_data[
        "aguardando_valor"
    ] = False

    # -----------------------------------------------------
    # AGUARDAR CPF/CNPJ
    # -----------------------------------------------------

    context.user_data[
        "aguardando_documento"
    ] = True

    await update.message.reply_text(
        "🧾 *IDENTIFICAÇÃO DO PAGAMENTO*\n\n"
        f"💰 Valor: *R$ {valor:.2f}*\n\n"
        "Para continuar, digite seu "
        "*CPF ou CNPJ*.\n\n"
        "Exemplo:\n"
        "`12345678909`\n\n"
        "Pode enviar com ou sem pontos e traços.",
        parse_mode="Markdown",
    )


# =========================================================
# PROCESSAR CPF / CNPJ
# =========================================================

async def processar_documento(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get(
        "aguardando_documento"
    ):

        return

    if not update.message:

        return

    documento = update.message.text.strip()

    # -----------------------------------------------------
    # LIMPAR DOCUMENTO
    # -----------------------------------------------------

    documento_limpo = "".join(
        caractere
        for caractere in documento
        if caractere.isdigit()
    )

    # -----------------------------------------------------
    # VALIDAR CPF / CNPJ
    # -----------------------------------------------------

    if not validar_documento(
        documento_limpo
    ):

        await update.message.reply_text(
            "❌ CPF ou CNPJ inválido.\n\n"
            "Digite novamente.\n\n"
            "Exemplo:\n"
            "`12345678909`",
            parse_mode="Markdown",
        )

        return

    # -----------------------------------------------------
    # PEGAR VALOR
    # -----------------------------------------------------

    valor = context.user_data.get(
        "valor_saldo"
    )

    if not valor:

        context.user_data[
            "aguardando_documento"
        ] = False

        await update.message.reply_text(
            "❌ Não encontrei o valor da cobrança.\n\n"
            "Volte ao menu e tente novamente.",
            reply_markup=menu_principal(),
        )

        return

    # -----------------------------------------------------
    # FINALIZAR ESTADO
    # -----------------------------------------------------

    context.user_data[
        "aguardando_documento"
    ] = False

    context.user_data[
        "valor_saldo"
    ] = None

    usuario = update.effective_user

    # -----------------------------------------------------
    # MENSAGEM DE ESPERA
    # -----------------------------------------------------

    mensagem = await update.message.reply_text(
        "⏳ Gerando sua cobrança PIX..."
    )

    try:

        # -------------------------------------------------
        # NOME DO CLIENTE
        # -------------------------------------------------

        nome = (
            usuario.full_name
            or usuario.first_name
            or f"Cliente {usuario.id}"
        )

        # -------------------------------------------------
        # REFERÊNCIA
        # -------------------------------------------------

        external_reference = (
            f"telegram_{usuario.id}"
        )

        # -------------------------------------------------
        # CRIAR / LOCALIZAR CLIENTE
        # -------------------------------------------------

        cliente = obter_ou_criar_cliente(
            nome=nome,
            cpf_cnpj=documento_limpo,
            external_reference=(
                external_reference
            ),
        )

        cliente_id = cliente.get(
            "id"
        )

        if not cliente_id:

            raise Exception(
                "Asaas não retornou o ID "
                "do cliente."
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
            external_reference=(
                f"saldo_{usuario.id}"
            ),
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
        # -----------------------------------------------------

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

        # -------------------------------------------------
        # EXPIRAÇÃO
        # -------------------------------------------------

        expiration = pix.get(
            "expirationDate",
            "",
        )

        # -------------------------------------------------
        # TEXTO PIX
        # -------------------------------------------------

        texto_pix = (
            "💳 *PAGAMENTO PIX*\n\n"
            f"💰 Valor: *R$ {valor:.2f}*\n\n"
            "📋 *Pix Copia e Cola:*\n\n"
            f"`{payload}`\n\n"
            "👇 Copie o código acima e "
            "pague pelo seu banco.\n\n"
            "⏳ Depois do pagamento, "
            "clique em *Consultar pagamento* "
            "para verificar a confirmação."
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

        # -------------------------------------------------
        # ENVIAR PIX
        # -------------------------------------------------

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

        # -------------------------------------------------
        # MOSTRAR ERRO
        # -------------------------------------------------

        await mensagem.edit_text(
            "❌ *Não foi possível gerar "
            "a cobrança PIX.*\n\n"
            "Ocorreu um erro ao comunicar "
            "com o Asaas.\n\n"
            "Tente novamente em alguns instantes.",
            parse_mode="Markdown",
        )


# =========================================================
# PROCESSAR TEXTO
# =========================================================

async def processar_mensagem_texto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    # -----------------------------------------------------
    # CPF / CNPJ
    # -----------------------------------------------------

    if context.user_data.get(
        "aguardando_documento"
    ):

        await processar_documento(
            update,
            context,
        )

        return

    # -----------------------------------------------------
    # VALOR
    # -----------------------------------------------------

    if context.user_data.get(
        "aguardando_valor"
    ):

        await processar_valor_saldo(
            update,
            context,
        )

        return


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

        # -------------------------------------------------
        # CONSULTAR ASAAS
        # -------------------------------------------------

        cobranca = (
            consultar_cobranca(
                cobranca_id
            )
        )

        status_asaas = (
            cobranca.get(
                "status",
                "",
            )
        )

        print(
            f"Pagamento {cobranca_id}: "
            f"{status_asaas}"
        )

        # -------------------------------------------------
        # PAGAMENTO CONFIRMADO
        # -------------------------------------------------

        if status_asaas in (
            "RECEIVED",
            "CONFIRMED",
        ):

            # -------------------------------------------------
            # EVITAR DUPLICIDADE
            # -------------------------------------------------

            if status_banco != "pago":

                atualizar_status_pagamento(
                    cobranca_id,
                    "pago",
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

            # -------------------------------------------------
            # JÁ PROCESSADO
            # -------------------------------------------------

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
        # PENDENTE
        # -------------------------------------------------

        if status_asaas in (
            "PENDING",
            "AWAITING_RISK_ANALYSIS",
       
