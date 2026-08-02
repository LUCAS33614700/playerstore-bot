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

from config import BOT_TOKEN, verificar_configuracao

from database import (
    criar_tabelas,
    criar_usuario,
    consultar_saldo,
    conectar,
    retirar_saldo,
    adicionar_saldo,
    criar_pagamento,
    consultar_pagamento,
    atualizar_status_pagamento,
)

from menu import menu_principal
from catalogo import menu_catalogo, buscar_produto

from asaas import (
    criar_cliente,
    criar_cobranca_pix,
    obter_qrcode_pix,
    consultar_cobranca,
)


GRUPO_CLIENTES = "https://t.me/PLAYERSTORYREFERENCIA"


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    usuario = update.effective_user

    criar_usuario(
        usuario.id,
        usuario.first_name or "",
        usuario.username or ""
    )

    texto = (
        f"👋 Olá, {usuario.first_name}!\n\n"
        "🛒 Bem-vindo à PLAYER STORE!\n\n"
        "Escolha uma opção abaixo:"
    )

    await update.message.reply_text(
        texto,
        reply_markup=menu_principal()
    )


# =========================================================
# COMPRA DE PRODUTO
# =========================================================

async def comprar_produto(
    query,
    produto_id,
    usuario_id
):
    produto = buscar_produto(produto_id)

    if not produto:
        await query.answer(
            "❌ Produto não encontrado.",
            show_alert=True
        )
        return

    _, nome, descricao, preco, estoque = produto

    if estoque <= 0:
        await query.answer(
            "📦 Produto sem estoque.",
            show_alert=True
        )
        return

    saldo = consultar_saldo(usuario_id)

    if saldo < preco:
        await query.answer(
            f"❌ Saldo insuficiente.\n"
            f"Seu saldo: R$ {saldo:.2f}\n"
            f"Preço: R$ {preco:.2f}",
            show_alert=True
        )
        return

    sucesso = retirar_saldo(
        usuario_id,
        preco
    )

    if not sucesso:
        await query.answer(
            "❌ Não foi possível realizar a compra.",
            show_alert=True
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
        (produto_id,)
    )

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
            preco
        )
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
        parse_mode="Markdown"
    )


# =========================================================
# PEDIR VALOR DO SALDO
# =========================================================

async def pedir_valor_saldo(
    query,
    context
):
    context.user_data["aguardando_valor"] = True

    await query.edit_message_text(
        "💵 *ADICIONAR SALDO*\n\n"
        "Digite o valor que deseja adicionar.\n\n"
        "Exemplos:\n"
        "`10`\n"
        "`25.50`\n"
        "`100`",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="voltar_menu"
                )
            ]
        ]),
        parse_mode="Markdown"
    )


# =========================================================
# GERAR PAGAMENTO PIX
# =========================================================

async def processar_valor_saldo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.user_data.get(
        "aguardando_valor"
    ):
        return

    texto = update.message.text.strip()

    try:
        valor = float(
            texto.replace(",", ".")
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Digite apenas um valor válido.\n\n"
            "Exemplo: `10` ou `25.50`",
            parse_mode="Markdown"
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

    context.user_data[
        "aguardando_valor"
    ] = False

    usuario = update.effective_user

    mensagem = await update.message.reply_text(
        "⏳ Gerando sua cobrança PIX..."
    )

    try:
        # -------------------------------------------------
        # CRIAR CLIENTE ASAAS
        # -------------------------------------------------

        nome = usuario.first_name or "Cliente"

        username = usuario.username

        if username:
            email = (
                f"telegram_{usuario.id}_"
                f"{username}@playerstore.local"
            )
        else:
            email = (
                f"telegram_{usuario.id}"
                "@playerstore.local"
            )

        cliente = criar_cliente(
            nome=nome,
            email=email
        )

        cliente_id = cliente.get("id")

        if not cliente_id:
            raise Exception(
                "O Asaas não retornou o ID do cliente."
            )

        # -------------------------------------------------
        # CRIAR COBRANÇA
        # -------------------------------------------------

        cobranca = criar_cobranca_pix(
            valor=valor,
            descricao=(
                f"Adição de saldo - "
                f"PLAYER STORE - "
                f"Telegram {usuario.id}"
            ),
            cliente_id=cliente_id
        )

        cobranca_id = cobranca.get("id")

        if not cobranca_id:
            raise Exception(
                "O Asaas não retornou o ID da cobrança."
            )

        # -------------------------------------------------
        # REGISTRAR PAGAMENTO NO BANCO
        # -------------------------------------------------

        criar_pagamento(
            usuario_id=usuario.id,
            valor=valor,
            asaas_id=cobranca_id
        )

        # -------------------------------------------------
        # OBTER PIX
        # -------------------------------------------------

        pix = obter_qrcode_pix(
            cobranca_id
        )

        codigo_pix = (
            pix.get("payload")
            or pix.get("encodedImage")
            or ""
        )

        if not codigo_pix:
            codigo_pix = (
                "Não foi possível obter o "
                "código PIX automaticamente."
            )

        # -------------------------------------------------
        # MONTAR MENSAGEM
        # -------------------------------------------------

        texto_pix = (
            "💵 *PAGAMENTO PIX*\n\n"
            f"💰 Valor: *R$ {valor:.2f}*\n\n"
            "📱 Faça o pagamento usando o PIX.\n\n"
            "📋 *PIX copia e cola:*\n"
            f"`{codigo_pix}`\n\n"
            "Depois de realizar o pagamento, "
            "clique em *Verificar pagamento*.\n\n"
            "⚠️ O saldo somente será liberado "
            "após a confirmação do pagamento."
        )

        botoes = [
            [
                InlineKeyboardButton(
                    "🔄 Verificar pagamento",
                    callback_data=f"verificar_pagamento_{cobranca_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="voltar_menu"
                )
            ]
        ]

        await mensagem.edit_text(
            texto_pix,
            reply_markup=InlineKeyboardMarkup(botoes),
            parse_mode="Markdown"
        )

    except Exception as erro:
        print(
            f"Erro ao gerar cobrança PIX: {erro}"
        )

        await mensagem.edit_text(
            "❌ *Não foi possível gerar o PIX.*\n\n"
            "Verifique se a chave da API do Asaas "
            "está configurada corretamente no Railway.\n\n"
            "Tente novamente em alguns instantes.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )


# =========================================================
# VERIFICAR PAGAMENTO
# =========================================================

async def verificar_pagamento(
    query,
    cobranca_id
):
    try:
        pagamento = consultar_pagamento(
            cobranca_id
        )

        if not pagamento:
            await query.answer(
                "❌ Pagamento não encontrado.",
                show_alert=True
            )
            return

        pagamento_id = pagamento[0]
        usuario_id = pagamento[1]
        valor = pagamento[2]
        status_atual = pagamento[4]

        # -------------------------------------------------
        # CONSULTAR ASAAS
        # -------------------------------------------------

        cobranca = consultar_cobranca(
            cobranca_id
        )

        status_asaas = cobranca.get(
            "status",
            ""
        )

        # -------------------------------------------------
        # PAGAMENTO CONFIRMADO
        # -------------------------------------------------

        status_pagos = (
            "RECEIVED",
            "CONFIRMED"
        )

        if status_asaas in status_pagos:

            if status_atual == "pago":
                await query.answer(
                    "✅ Este pagamento já foi processado.",
                    show_alert=True
                )
                return

            atualizar_status_pagamento(
                cobranca_id,
                "pago"
            )

            adicionar_saldo(
                usuario_id,
                valor
            )

            novo_saldo = consultar_saldo(
                usuario_id
            )

            await query.edit_message_text(
                "✅ *PAGAMENTO CONFIRMADO!*\n\n"
                f"💰 Valor adicionado: "
                f"R$ {valor:.2f}\n\n"
                f"💳 Seu novo saldo: "
                f"R$ {novo_saldo:.2f}\n\n"
                "Obrigado pela compra! 🛒",
                reply_markup=menu_principal(),
                parse_mode="Markdown"
            )

            return

        # -------------------------------------------------
        # PAGAMENTO AINDA PENDENTE
        # -------------------------------------------------

        if status_asaas in (
            "PENDING",
            "AWAITING_RISK_ANALYSIS"
        ):
            await query.answer(
                "⏳ Pagamento ainda não confirmado.",
                show_alert=True
            )
            return

        # -------------------------------------------------
        # PAGAMENTO CANCELADO / VENCIDO
        # -------------------------------------------------

        if status_asaas in (
            "CANCELLED",
            "EXPIRED",
            "REFUNDED",
            "REFUND_REQUESTED"
        ):
            atualizar_status_pagamento(
                cobranca_id,
                status_asaas.lower()
            )

            await query.edit_message_text(
                "❌ *PAGAMENTO NÃO CONCLUÍDO*\n\n"
                f"Status: `{status_asaas}`\n\n"
                "A cobrança não foi confirmada.",
                reply_markup=menu_principal(),
                parse_mode="Markdown"
            )
            return

        await query.answer(
            f"⏳ Status atual: {status_asaas}",
            show_alert=True
        )

    except Exception as erro:
        print(
            f"Erro ao verificar pagamento: {erro}"
        )

        await query.answer(
            "❌ Não foi possível consultar o pagamento.",
            show_alert=True
        )


# =========================================================
# BOTÕES
# =========================================================

async def botoes(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query

    await query.answer()

    usuario_id = query.from_user.id
    acao = query.data

    # -----------------------------------------------------
    # CATÁLOGO
    # -----------------------------------------------------

    if acao == "catalogo":

        await query.edit_message_text(
            "🛒 *LOGINS | CONTAS PREMIUM*\n\n"
            "Escolha um produto:",
            reply_markup=menu_catalogo(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # PRODUTO
    # -----------------------------------------------------

    elif acao.startswith("produto_"):

        produto_id = int(
            acao.split("_")[1]
        )

        produto = buscar_produto(
            produto_id
        )

        if not produto:
            await query.answer(
                "❌ Produto não encontrado.",
                show_alert=True
            )
            return

        _, nome, descricao, preco, estoque = produto

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
                    callback_data=f"comprar_{produto_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="catalogo"
                )
            ]
        ]

        await query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(
                botoes_compra
            ),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # COMPRAR
    # -----------------------------------------------------

    elif acao.startswith("comprar_"):

        produto_id = int(
            acao.split("_")[1]
        )

        await comprar_produto(
            query,
            produto_id,
            usuario_id
        )

    # -----------------------------------------------------
    # SALDO
    # -----------------------------------------------------

    elif acao == "saldo":

        saldo = consultar_saldo(
            usuario_id
        )

        botoes_saldo = [
            [
                InlineKeyboardButton(
                    "💵 Adicionar saldo",
                    callback_data="adicionar_saldo"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="voltar_menu"
                )
            ]
        ]

        await query.edit_message_text(
            f"💵 *SEU SALDO*\n\n"
            f"💰 Saldo atual: "
            f"R$ {saldo:.2f}\n\n"
            "Escolha uma opção:",
            reply_markup=InlineKeyboardMarkup(
                botoes_saldo
            ),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # ADICIONAR SALDO
    # -----------------------------------------------------

    elif acao == "adicionar_saldo":

        await pedir_valor_saldo(
            query,
            context
        )

    # -----------------------------------------------------
    # VERIFICAR PAGAMENTO
    # -----------------------------------------------------

    elif acao.startswith(
        "verificar_pagamento_"
    ):

        cobranca_id = acao.replace(
            "verificar_pagamento_",
            "",
            1
        )

        await verificar_pagamento(
            query,
            cobranca_id
        )

    # -----------------------------------------------------
    # PERFIL
    # -----------------------------------------------------

    elif acao == "perfil":

        saldo = consultar_saldo(
            usuario_id
        )

        await query.edit_message_text(
            f"👤 *SEU PERFIL*\n\n"
            f"🆔 ID: `{usuario_id}`\n"
            f"💰 Saldo: R$ {saldo:.2f}",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # VOLTAR
    # -----------------------------------------------------

    elif acao == "voltar_menu":

        context.user_data[
            "aguardando_valor"
        ] = False

        await query.edit_message_text(
            "🏠 *MENU PRINCIPAL*\n\n"
            "Escolha uma opção:",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # CARRINHO
    # -----------------------------------------------------

    elif acao == "carrinho":

        await query.edit_message_text(
            "🛍️ *CARRINHO*\n\n"
            "Seu carrinho está vazio.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # PESQUISAR
    # -----------------------------------------------------

    elif acao == "pesquisar":

        await query.edit_message_text(
            "🔎 *PESQUISAR SERVIÇO*\n\n"
            "Sistema de pesquisa em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # ESTOQUE
    # -----------------------------------------------------

    elif acao == "estoque":

        await query.edit_message_text(
            "📦 *ESTOQUE DE LOGINS*\n\n"
            "Consulte os produtos disponíveis "
            "no catálogo.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # MAC
    # -----------------------------------------------------

    elif acao == "mac":

        await query.edit_message_text(
            "🎮 *ATIVAÇÃO DE MAC*\n\n"
            "Sistema de ativação em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # JOGOS
    # -----------------------------------------------------

    elif acao == "jogos":

        await query.edit_message_text(
            "⚽ *JOGOS NA TV*\n\n"
            "Informações sobre jogos serão "
            "adicionadas aqui.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # RENOVAR
    # -----------------------------------------------------

    elif acao == "renovar":

        await query.edit_message_text(
            "♻️ *RENOVAR CONTA*\n\n"
            "Sistema de renovação em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # -----------------------------------------------------
    # SUPORTE
    # -----------------------------------------------------

    elif acao == "suporte":

        await query.edit_message_text(
            "🆘 *SUPORTE*\n\n"
            "Entre em contato com o suporte.",
      
