import asyncio
import base64
import binascii
import io


from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
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
    GRUPO_CLIENTES,
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
    listar_pagamentos_pendentes,
    processar_pagamento_pago,
)


from menu import (
    menu_principal
)


from catalogo import (
    menu_catalogo,
    buscar_produto,
)


from pushinpay import (
    criar_pix,
    consultar_pix,
)


# =========================================================
# CONFIGURAÇÕES DO PAGAMENTO
# =========================================================

VALOR_MINIMO = 5.00

VALOR_MAXIMO = 499.00

INTERVALO_VERIFICACAO = 5


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
        "valor_saldo"
    ] = None

    context.user_data[
        "quantidade_produto"
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
# COMPRAR PRODUTO
# =========================================================

async def comprar_produto(
    query,
    produto_id,
    usuario_id,
    quantidade=1,
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

    preco = float(preco)
    estoque = int(estoque)

    quantidade = int(
        quantidade
    )

    if quantidade <= 0:

        await query.answer(
            "❌ Quantidade inválida.",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # VERIFICAR ESTOQUE
    # -----------------------------------------------------

    if estoque < quantidade:

        await query.answer(
            f"❌ Estoque insuficiente.\n\n"
            f"📦 Disponível: {estoque}\n"
            f"🛒 Solicitado: {quantidade}",
            show_alert=True,
        )

        return

    valor_total = (
        preco * quantidade
    )

    # -----------------------------------------------------
    # VERIFICAR SALDO
    # -----------------------------------------------------

    saldo = consultar_saldo(
        usuario_id
    )

    if saldo < valor_total:

        await query.answer(
            f"❌ Saldo insuficiente.\n\n"
            f"💰 Seu saldo: R$ {saldo:.2f}\n"
            f"🛒 Total: R$ {valor_total:.2f}\n\n"
            f"💵 Faltam: "
            f"R$ {valor_total - saldo:.2f}",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # RETIRAR SALDO
    # -----------------------------------------------------

    sucesso = retirar_saldo(
        usuario_id,
        valor_total,
    )

    if not sucesso:

        await query.answer(
            "❌ Não foi possível realizar a compra.",
            show_alert=True,
        )

        return

    conn = conectar()
    cursor = conn.cursor()

    try:

        # -------------------------------------------------
        # ATUALIZAR ESTOQUE
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE produtos
            SET estoque = estoque - ?
            WHERE id = ?
            AND estoque >= ?
            """,
            (
                quantidade,
                produto_id,
                quantidade,
            ),
        )

        estoque_atualizado = (
            cursor.rowcount > 0
        )

        if not estoque_atualizado:

            conn.rollback()
            conn.close()

            adicionar_saldo(
                usuario_id,
                valor_total,
            )

            await query.answer(
                "❌ O estoque mudou. "
                "Tente novamente.",
                show_alert=True,
            )

            return

        # -------------------------------------------------
        # REGISTRAR PEDIDO
        # -------------------------------------------------

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
            VALUES (?, ?, ?, ?, 'pago')
            """,
            (
                usuario_id,
                produto_id,
                quantidade,
                valor_total,
            ),
        )

        conn.commit()

    except Exception as erro:

        conn.rollback()

        conn.close()

        adicionar_saldo(
            usuario_id,
            valor_total,
        )

        print(
            "ERRO AO REGISTRAR COMPRA:"
        )

        print(
            repr(erro)
        )

        await query.answer(
            "❌ Erro ao finalizar a compra.",
            show_alert=True,
        )

        return

    conn.close()

    # -----------------------------------------------------
    # NOVO SALDO
    # -----------------------------------------------------

    novo_saldo = consultar_saldo(
        usuario_id
    )

    # -----------------------------------------------------
    # COMPRA
    # -----------------------------------------------------

    texto = (
        "✅ *COMPRA REALIZADA!*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛒 *Produto:* {nome}\n"
        f"📦 *Quantidade:* {quantidade}\n"
        f"💰 *Preço unitário:* R$ {preco:.2f}\n"
        f"💵 *Total:* R$ {valor_total:.2f}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 *Saldo restante:* "
        f"R$ {novo_saldo:.2f}\n\n"
        "📦 Seu pedido foi registrado."
    )

    botoes = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛒 Comprar novamente",
                    callback_data=(
                        f"produto_{produto_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "🛒 Ver catálogo",
                    callback_data="catalogo",
                )
            ],
            [
                InlineKeyboardButton(
                    "↩️ Voltar ao menu",
                    callback_data="voltar_menu",
                )
            ],
        ]
    )

    await query.edit_message_text(
        texto,
        reply_markup=botoes,
        parse_mode="Markdown",
    )


# =========================================================
# PEDIR QUANTIDADE
# =========================================================

async def pedir_quantidade_produto(
    query,
    context,
    produto_id,
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

    estoque = int(
        estoque
    )

    if estoque <= 0:

        await query.answer(
            "📦 Produto sem estoque.",
            show_alert=True,
        )

        return

    context.user_data[
        "aguardando_quantidade"
    ] = True

    context.user_data[
        "produto_quantidade_id"
    ] = produto_id

    await query.edit_message_text(
        "🛍️ *COMPRAR EM QUANTIDADE*\n\n"
        f"🛒 *Produto:* {nome}\n"
        f"💰 *Preço unitário:* R$ {float(preco):.2f}\n"
        f"📦 *Disponível:* {estoque}\n\n"
        "Digite a quantidade que deseja comprar.\n\n"
        "Exemplo:\n"
        "`1`\n"
        "`2`\n"
        "`5`",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Voltar",
                        callback_data=(
                            f"produto_{produto_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "↩️ Voltar ao menu",
                        callback_data=(
                            "voltar_menu"
                        ),
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# PROCESSAR QUANTIDADE
# =========================================================

async def processar_quantidade_produto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get(
        "aguardando_quantidade"
    ):

        return False

    if not update.message:

        return True

    produto_id = context.user_data.get(
        "produto_quantidade_id"
    )

    if not produto_id:

        context.user_data[
            "aguardando_quantidade"
        ] = False

        return True

    texto = (
        update.message.text
        .strip()
    )

    try:

        quantidade = int(
            texto
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Digite somente um número inteiro.\n\n"
            "Exemplo: `2`",
            parse_mode="Markdown",
        )

        return True

    if quantidade <= 0:

        await update.message.reply_text(
            "❌ A quantidade deve ser maior que zero."
        )

        return True

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        context.user_data[
            "aguardando_quantidade"
        ] = False

        await update.message.reply_text(
            "❌ Produto não encontrado."
        )

        return True

    (
        _,
        nome,
        descricao,
        preco,
        estoque,
    ) = produto

    preco = float(
        preco
    )

    estoque = int(
        estoque
    )

    if quantidade > estoque:

        await update.message.reply_text(
            f"❌ Quantidade indisponível.\n\n"
            f"📦 Estoque disponível: {estoque}\n"
            f"🛒 Você pediu: {quantidade}"
        )

        return True

    valor_total = (
        preco * quantidade
    )

    saldo = consultar_saldo(
        update.effective_user.id
    )

    if saldo < valor_total:

        await update.message.reply_text(
            f"❌ Saldo insuficiente.\n\n"
            f"💳 Seu saldo: R$ {saldo:.2f}\n"
            f"💰 Total: R$ {valor_total:.2f}\n\n"
            f"💵 Faltam: "
            f"R$ {valor_total - saldo:.2f}",
        )

        return True

    context.user_data[
        "aguardando_quantidade"
    ] = False

    context.user_data[
        "quantidade_produto"
    ] = quantidade

    # -----------------------------------------------------
    # CONFIRMAÇÃO
    # -----------------------------------------------------

    texto = (
        "🛒 *CONFIRMAR COMPRA*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ *Produto:* {nome}\n"
        f"📦 *Quantidade:* {quantidade}\n"
        f"💰 *Preço unitário:* R$ {preco:.2f}\n"
        f"💵 *Total:* R$ {valor_total:.2f}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 *Seu saldo:* R$ {saldo:.2f}\n"
        f"💳 *Saldo após compra:* "
        f"R$ {saldo - valor_total:.2f}\n\n"
        "⚡ *Entrega imediata*\n"
        "❌ Sem reembolso em Pix\n"
        "👩🏻‍💻 Suporte completo"
    )

    botoes = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ CONFIRMAR COMPRA",
                    callback_data=(
                        f"confirmar_compra_"
                        f"{produto_id}_"
                        f"{quantidade}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar ao produto",
                    callback_data=(
                        f"produto_{produto_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "↩️ Voltar ao menu",
                    callback_data=(
                        "voltar_menu"
                    ),
                )
            ],
        ]
    )

    await update.message.reply_text(
        texto,
        reply_markup=botoes,
        parse_mode="Markdown",
    )

    return True


# =========================================================
# PEDIR VALOR
# =========================================================

async def pedir_valor_saldo(
    query,
    context,
):

    context.user_data[
        "aguardando_valor"
    ] = True

    context.user_data[
        "valor_saldo"
    ] = None

    context.user_data[
        "aguardando_quantidade"
    ] = False

    await query.edit_message_text(
        "💵 *ADICIONAR SALDO*\n\n"
        "💠 PIX AUTOMÁTICO\n\n"
        "Digite o valor que deseja adicionar.\n\n"
        f"▫️ Mínimo: R$ {VALOR_MINIMO:.2f}\n"
        f"▫️ Máximo: R$ {VALOR_MAXIMO:.2f}\n\n"
        "Exemplo:\n"
        "`10`\n"
        "`25,50`\n"
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
# CONVERTER BASE64 DO QR CODE
# =========================================================

def converter_qr_code_base64(
    qr_code_base64,
):

    if not qr_code_base64:

        return None

    try:

        valor = str(
            qr_code_base64
        ).strip()

        if "," in valor:

            valor = valor.split(
                ",",
                1,
            )[1]

        dados = base64.b64decode(
            valor,
            validate=False,
        )

        if not dados:

            return None

        return io.BytesIO(
            dados
        )

    except (
        ValueError,
        TypeError,
        binascii.Error,
    ):

        print(
            "QR Code Base64 inválido."
        )

        return None


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

    texto = (
        update.message.text
        .strip()
    )

    try:

        valor = float(
            texto.replace(
                ",",
                ".",
            )
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Digite apenas um valor válido.\n\n"
            "Exemplo:\n"
            "`10`\n"
            "`25,50`\n"
            "`100`",
            parse_mode="Markdown",
        )

        return

    if valor < VALOR_MINIMO:

        await update.message.reply_text(
            f"❌ O valor mínimo é "
            f"R$ {VALOR_MINIMO:.2f}.",
        )

        return

    if valor > VALOR_MAXIMO:

        await update.message.reply_text(
            f"❌ O valor máximo é "
            f"R$ {VALOR_MAXIMO:.2f}.",
        )

        return

    valor = round(
        valor,
        2,
    )

    context.user_data[
        "valor_saldo"
    ] = valor

    context.user_data[
        "aguardando_valor"
    ] = False

    usuario = (
        update.effective_user
    )

    mensagem = (
        await update.message.reply_text(
            "⏳ *Gerando seu PIX...*",
            parse_mode="Markdown",
        )
    )

    try:

        pix = criar_pix(
            valor=valor
        )

        transacao_id = pix.get(
            "id"
        )

        qr_code = pix.get(
            "qr_code"
        )

        qr_code_base64 = pix.get(
            "qr_code_base64"
        )

        if not transacao_id:

            raise Exception(
                "PushinPay não retornou "
                "o ID da transação."
            )

        if not qr_code:

            raise Exception(
                "PushinPay não retornou "
                "o código PIX."
            )

        criar_pagamento(
            usuario.id,
            valor,
            transacao_id,
        )

        texto_pix = (
            "💎 *PIX AUTOMÁTICO*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"💰 *Valor:* R$ {valor:.2f}\n"
            f"🆔 *ID da compra:* `{transacao_id}`\n"
            "⏳ *Status:* Aguardando pagamento\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📋 *PIX COPIA E COLA*\n\n"
            f"`{qr_code}`\n\n"
            "⚡ Após o pagamento, "
            "a confirmação será feita "
            "automaticamente.\n\n"
            "💰 O saldo será liberado "
            "assim que o pagamento for "
            "confirmado."
        )

        botoes = [
            [
                InlineKeyboardButton(
                    "📋 COPIAR CÓDIGO",
                    copy_text=CopyTextButton(
                        text=str(qr_code)
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⏰ AGUARDANDO PAGAMENTO",
                    callback_data=(
                        "status_pagamento_"
                        f"{transacao_id}"
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

        markup = (
            InlineKeyboardMarkup(
                botoes
            )
        )

        imagem_qr = (
            converter_qr_code_base64(
                qr_code_base64
            )
        )

        if imagem_qr:

            await mensagem.delete()

            await update.message.reply_photo(
                photo=imagem_qr,
                caption=texto_pix,
                reply_markup=markup,
                parse_mode="Markdown",
            )

        else:

            await mensagem.edit_text(
                texto_pix,
                reply_markup=markup,
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
            "❌ *Não foi possível gerar o PIX.*\n\n"
            "Ocorreu um erro ao comunicar "
            "com a PushinPay.\n\n"
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

    if context.user_data.get(
        "aguardando_quantidade"
    ):

        await processar_quantidade_produto(
            update,
            context,
        )

        return

    if context.user_data.get(
        "aguardando_valor"
    ):

        await processar_valor_saldo(
            update,
            context,
        )

        return


# =========================================================
# VERIFICAR PAGAMENTO MANUAL
# =========================================================

async def verificar_pagamento(
    query,
    transacao_id,
):

    try:

        pagamento = (
            consultar_pagamento(
                transacao_id
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

        if status_banco == "pago":

            saldo = consultar_saldo(
                usuario_id
            )

            await query.answer(
                "✅ Pagamento já confirmado.",
                show_alert=True,
            )

            return

        transacao = await asyncio.to_thread(
            consultar_pix,
            transacao_id,
        )

        status = str(
            transacao.get(
                "status",
                "",
            )
        ).lower()

        print(
            f"Pagamento {transacao_id}: "
            f"{status}"
        )

        if status == "paid":

            resultado = (
                processar_pagamento_pago(
                    transacao_id
                )
            )

            if resultado:

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

            else:

                await query.answer(
                    "✅ Pagamento já processado.",
                    show_alert=True,
                )

            return

        if status in (
            "created",
            "pending",
        ):

            await query.answer(
                "⏳ O pagamento ainda está pendente.",
                show_alert=True,
            )

            return

        if status in (
            "canceled",
            "cancelled",
            "expired",
        ):

            atualizar_status_pagamento(
                transacao_id,
                "cancelado",
            )

            await query.edit_message_text(
                "❌ *PAGAMENTO ENCERRADO*\n\n"
                "A cobrança não foi aprovada.\n\n"
                "💰 Nenhum saldo foi adicionado.",
                reply_markup=menu_principal(),
                parse_mode="Markdown",
            )

            return

        await query.answer(
            f"Status atual: {status}",
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
# VERIFICAÇÃO AUTOMÁTICA
# =========================================================

async def verificar_pagamentos_automaticamente(
    context: ContextTypes.DEFAULT_TYPE,
):

    pagamentos = (
        listar_pagamentos_pendentes()
    )

    if not pagamentos:

        return

    print(
        f"🔎 Verificando "
        f"{len(pagamentos)} pagamento(s)..."
    )

    for pagamento in pagamentos:

        try:

            (
                pagamento_id,
                usuario_id,
                valor,
                transacao_id,
                status_banco,
                criado_em,
            ) = pagamento

            transacao = (
                await asyncio.to_thread(
                    consultar_pix,
                    transacao_id,
                )
            )

            status = str(
                transacao.get(
                    "status",
                    "",
                )
            ).lower()

            print(
                f"PIX {transacao_id}: "
                f"{status}"
            )

            if status == "paid":

                resultado = (
                    processar_pagamento_pago(
                        transacao_id
                    )
                )

                if not resultado:

                    continue

                novo_saldo = (
                    consultar_saldo(
                        usuario_id
                    )
                )

                try:

                    await context.bot.send_message(
                        chat_id=usuario_id,
                        text=(
                            "✅ *PAGAMENTO APROVADO!*\n\n"
                            "━━━━━━━━━━━━━━━━━━\n"
                            f"💰 Valor: "
                            f"R$ {float(valor):.2f}\n"
                            f"🆔 ID: `{transacao_id}`\n"
                            "━━━━━━━━━━━━━━━━━━\n\n"
                            f"💳 *Novo saldo:* "
                            f"R$ {novo_saldo:.2f}\n\n"
                            "🎉 Seu saldo foi liberado "
                            "automaticamente!"
                        ),
                        reply_markup=menu_principal(),
                        parse_mode="Markdown",
                    )

                except Exception as erro_envio:

                    print(
                        "ERRO AO ENVIAR "
                        "CONFIRMAÇÃO:"
                    )

                    print(
                        repr(erro_envio)
                    )

                continue

            if status in (
                "canceled",
                "cancelled",
                "expired",
            ):

                atualizado = (
                    atualizar_status_pagamento(
                        transacao_id,
                        "cancelado",
                    )
                )

                if atualizado:

                    try:

                        await context.bot.send_message(
                            chat_id=usuario_id,
                            text=(
                                "❌ *PAGAMENTO ENCERRADO*\n\n"
                                f"💰 Valor: "
                                f"R$ {float(valor):.2f}\n\n"
                                "A cobrança PIX foi "
                                "cancelada ou expirou.\n\n"
                                "💳 Nenhum saldo foi "
                                "adicionado."
                            ),
                            reply_markup=menu_principal(),
                            parse_mode="Markdown",
                        )

                    except Exception as erro_envio:

                        print(
                            "ERRO AO ENVIAR "
                            "CANCELAMENTO:"
                        )

                        print(
                            repr(erro_envio)
                        )

        except Exception as erro:

            print(
                "ERRO NA VERIFICAÇÃO "
                f"DO PIX {pagamento[3]}:"
            )

            print(
                repr(erro)
            )


# =========================================================
# STATUS DO PAGAMENTO
# =========================================================

async def mostrar_status_pagamento(
    query,
    transacao_id,
):

    pagamento = (
        consultar_pagamento(
            transacao_id
        )
    )

    if not pagamento:

        await query.answer(
            "❌ Pagamento não encontrado.",
            show_alert=True,
        )

        return

    status = pagamento[4]

    if status == "pago":

        saldo = consultar_saldo(
            pagamento[1]
        )

        await query.answer(
            f"✅ Pago!\n"
            f"Saldo: R$ {saldo:.2f}",
            show_alert=True,
        )

        return

    if status == "cancelado":

        await query.answer(
            "❌ Esta cobrança foi encerrada.",
            show_alert=True,
        )

        return

    await query.answer(
        "⏰ Ainda aguardando o pagamento.\n\n"
        "O bot verifica automaticamente.",
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

    usuario_id = (
        query.from_user.id
    )

    acao = query.data

    # =====================================================
    # STATUS PAGAMENTO
    # =====================================================

    if acao.startswith(
        "status_pagamento_"
    ):

        transacao_id = (
            acao.replace(
                "status_pagamento_",
                "",
                1,
            )
        )

        await mostrar_status_pagamento(
            query,
            transacao_id,
        )

        return

    # =====================================================
    # CONSULTAR PAGAMENTO
    # =====================================================

    if acao.startswith(
        "consultar_pagamento_"
    ):

        transacao_id = (
            acao.replace(
                "consultar_pagamento_",
                "",
                1,
            )
        )

        await verificar_pagamento(
            query,
            transacao_id,
        )

        return

    # =====================================================
    # CATÁLOGO
    # =====================================================

    if acao == "catalogo":

        context.user_data[
            "aguardando_quantidade"
        ] = False

        await query.edit_message_text(
            "🛒 *LOGINS | CONTAS PREMIUM*\n\n"
            "Escolha um produto:",
            reply_markup=menu_catalogo(),
            parse_mode="Markdown",
        )

        return

    # =====================================================
    # PRODUTO
    # =====================================================

    if acao.startswith(
        "produto_"
    ):

        try:

            produto_id = int(
                acao.split("_")[1]
            )

        except (
            ValueError,
            IndexError,
        ):

            await query.answer(
                "❌ Produto inválido.",
                show_alert=True,
            )

            return

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

        preco = float(
            preco
        )

        estoque = int(
            estoque
        )

        if estoque <= 0:

            await query.answer(
                "📦 Produto sem estoque.",
                show_alert=True,
            )

            return

        saldo = consultar_saldo(
            usuario_id
        )

        texto = (
            "🛒 *FINALIZAR COMPRA*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🛍️ *Serviço:* {nome}\n"
            f"💰 *Preço:* R$ {preco:.2f}\n"
            f"💳 *Seu saldo:* R$ {saldo:.2f}\n"
            f"📦 *Disponível:* {estoque}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📝 {descricao or 'Sem descrição'}\n\n"
            "⚡ *Entrega imediata*\n"
            "❌ *Sem reembolso em Pix*\n"
            "👩🏻‍💻 *Suporte completo*"
        )

        botoes_compra = [
            [
                InlineKeyboardButton(
                    "🛒 COMPRAR",
                    callback_data=(
                        f"comprar_{produto_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "🛍️ COMPRAR EM QUANTIDADE",
                    callback_data=(
                        f"quantidade_{produto_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "💵 ADICIONAR SALDO",
                    callback_data=(
                        "adicionar_saldo"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ VOLTAR À CATEGORIA",
                    callback_data="catalogo",
                )
            ],
            [
                InlineKeyboardButton(
                    "↩️ VOLTAR AO MENU",
                    callback_data="voltar_menu",
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

        return

    # =====================================================
    # COMPRAR EM QUANTIDADE
    # =====================================================

    if acao.startswith(
        "quantidade_"
    ):

        try:

            produto_id = int(
                acao.split("_")[1]
            )

        except (
            ValueError,
            IndexError,
        ):

            await query.answer(
                "❌ Produto inválido.",
                show_alert=True,
            )

            return

        await pedir_quantidade_produto(
            query,
            context,
            produto_id,
        )

        return

    # =====================================================
    # CONFIRMAR COMPRA EM QUANTIDADE
    # =====================================================

    if acao.startswith(
        "confirmar_compra_"
    ):

        partes = acao.split("_")

        try:

            produto_id = int(
                partes[2]
            )

            quantidade = int(
                partes[3]
            )

        except (
            ValueError,
            IndexError,
        ):

            await query.answer(
                "❌ Compra inválida.",
                show_alert=True,
            )

            return

        await comprar_produto(
            query,
            produto_id,
            usuario_id,
            quantidade,
        )

        context.user_data[
            "quantidade_produto"
        ] = None

        return

    # =====================================================
    # COMPRAR
    # =====================================================

    if acao.startswith(
        "comprar_"
    ):

        try:

            produto_id = int(
                acao.split("_")[1]
            )

        except (
            ValueError,
            IndexError,
        ):

            await query.answer(
                "❌ Produto inválido.",
                show_alert=True,
            )

            return

        await comprar_produto(
            query,
            produto_id,
            usuario_id,
            1,
        )

        return

    # =====================================================
    # SALDO
    # =====================================================

    if acao == "saldo":

        saldo = consultar_saldo(
            usuario_id
        )

        botoes_saldo = [
            [
                InlineKeyboardButton(
                    "💵 Adicionar saldo",
                    callback_data=(
                        "adicionar_saldo"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data=(
                        "voltar_menu"
                    ),
                )
            ],
        ]

        await query.edit_message_text(
            "💳 *MEU SALDO*\n\n"
            f"💰 Saldo atual: "
            f"R$ {saldo:.2f}\n\n"
            "Escolha uma opção:",
            reply_markup=InlineKeyboardMarkup(
                botoes_saldo
            ),
            parse_mode="Markdown",
        )

        return

    # =====================================================
    # ADICIONAR SALDO
    # =====================================================

    if acao == "adicionar_saldo":

        await pedir_valor_saldo(
            query,
            context,
        )

        return

    # =====================================================
    # VOLTAR
    # =====================================================

    if acao == "voltar_menu":

        context.user_data[
            "aguardando_valor"
        ] = False

        context.user_data[
            "valor_saldo"
        ] = None

        context.user_data[
            "aguardando_quantidade"
        ] = False

        context.user_data[
            "produto_quantidade_id"
        ] = None

        context.user_data[
            "quantidade_produto"
        ] = None

        await query.edit_message_text(
            "🛒 *PLAYER STORE*\n\n"
            "Escolha uma opção abaixo:",
            reply_markup=menu_principal(),
            parse_mode="Markdown",
        )

        return

    # =====================================================
    # GRUPO
    # =====================================================

    if acao == "grupo":

        botoes_grupo = (
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👥 Entrar no grupo",
                            url=GRUPO_CLIENTES,
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ Voltar",
                            callback_data=(
                                "voltar_menu"
                            ),
                        )
                    ],
                ]
            )
        )

        await query.edit_message_text(
            "👥 *GRUPO DE CLIENTES*\n\n"
            "Entre no nosso grupo para "
            "acompanhar novidades e referências.",
            reply_markup=botoes_grupo,
            parse_mode="Markdown",
        )

        return

    # =====================================================
    # PERFIL
    # =====================================================

    if acao == "perfil":

        usuario = consultar_usuario(
            usuario_id
        )

        saldo = consultar_saldo(
            usuario_id
        )

        nome = (
            query.from_user.full_name
            or query.from_user.first_name
            or "Usuário"
        )

        username = (
            query.from_user.username
        )

        texto_username = (
            f"@{username}"
            if username
            else "Não informado"
        )

        await query.edit_message_text(
            "👤 *MEU PERFIL*\n\n"
            f"🧑 Nome: {nome}\n"
            f"🔗 Username: {texto_username}\n"
            f"🆔 ID: `{usuario_id}`\n\n"
            f"💰 Saldo: R$ {saldo:.2f}",
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

        return

    # =====================================================
    # AJUDA
    # =====================================================

    if acao == "ajuda":

        await query.edit_message_text(
            "❓ *AJUDA*\n\n"
            "🛒 *Comprar produto*\n"
            "Escolha um produto no catálogo "
            "e clique em Comprar.\n\n"
            "🛍️ *Comprar em quantidade*\n"
            "Escolha a quantidade desejada "
            "e confirme a compra.\n\n"
            "💳 *Adicionar saldo*\n"
            "Escolha o valor e o bot irá "
            "gerar um PIX automaticamente.\n\n"
            "💰 *Saldo*\n"
            "Veja seu saldo disponível.\n\n"
            "⚡ *Pagamento automático*\n"
            "Depois de pagar o PIX, "
            "não é necessário enviar comprovante "
            "nem ficar consultando manualmente.\n\n"
            "🤖 O sistema verifica "
            "automaticamente a confirmação.",
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

        return

    # =====================================================
    # ESTOQUE VAZIO
    # =====================================================

    if acao == "sem_estoque":

        await query.answer(
            "📦 No momento não há produtos disponíveis.",
            show_alert=True,
        )

        return

    # =====================================================
    # DESCONHECIDO
    # =====================================================

    await query.answer(
        "❌ Opção não reconhecida.",
        show_alert=True,
    )


# =========================================================
# INICIALIZAÇÃO DA VERIFICAÇÃO AUTOMÁTICA
# =========================================================

async def iniciar_verificador(
    application,
):

    if application.job_queue is None:

        raise RuntimeError(
            "JobQueue não está disponível. "
            "Instale python-telegram-bot[job-queue]."
        )

    application.job_queue.run_repeating(
        verificar_pagamentos_automaticamente,
        interval=INTERVALO_VERIFICACAO,
        first=INTERVALO_VERIFICACAO,
        name="verificador_pagamentos",
    )

    print(
        "💳 Verificador automático de PIX iniciado."
    )


# =========================================================
# ERRO GLOBAL
# =========================================================

async def erro_global(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    print(
        "ERRO:"
    )

    print(
        repr(context.error)
    )


# =========================================================
# MAIN
# =========================================================

def main():

    verificar_configuracao()

    criar_tabelas()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(
            iniciar_verificador
        )
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            botoes
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            processar_mensagem_texto,
        )
    )

    application.add_error_handler(
        erro_global
    )

    print(
        "🤖 PLAYER STORE iniciado!"
    )

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":

    main()
