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
            f"❌ Saldo insuficiente.\n\n"
            f"Seu saldo: R$ {saldo:.2f}\n"
            f"Preço: R$ {preco:.2f}",
            show_alert=True,
        )

        return

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
