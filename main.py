import base64
from io import BytesIO

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
    obter_cliente,
)


GRUPO_CLIENTES = (
    "https://t.me/PLAYERSTORYREFERENCIA"
)


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

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        await query.answer(
            "❌ Produto não encontrado.",
            show_alert=True
        )

        return

    (
        _,
        nome,
        descricao,
        preco,
        estoque
    ) = produto

    if estoque <= 0:

        await query.answer(
            "📦 Produto sem estoque.",
            show_alert=True
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
# PEDIR VALOR
# =========================================================

async def pedir_valor_saldo(
    query,
    context
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
# PROCESSAR VALOR DO SALDO
# =========================================================

async def processar_valor_saldo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.user_data.get(
        "aguardando_valor"
    ):
        return

    texto = (
        update.message.text
        .strip()
    )

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
        "⏳ *Gerando sua cobrança PIX...*",
        parse_mode="Markdown"
    )

    try:

        # =================================================
        # CADASTRAR / LOCALIZAR CLIENTE ASAAS
        # =================================================

        nome = (
            usuario.full_name
            or usuario.first_name
            or f"Cliente {usuario.id}"
        )

        # Criamos um e-mail único baseado no ID
        # do usuário do Telegram.
        email = (
            f"telegram{usuario.id}"
            "@playerstore.local"
        )

        cliente = obter_cliente(
            nome=nome,
            email=email
        )

        cliente_id = cliente.get(
            "id"
        )

        if not cliente_id:

            raise Exception(
                "O Asaas não retornou o ID do cliente."
            )

        # =================================================
        # CRIAR COBRANÇA PIX
        # =================================================

        cobranca = criar_cobranca_pix(
            valor=valor,
            descricao=(
                f"Adição de saldo - "
                f"Telegram {usuario.id}"
            ),
            cliente_id=cliente_id
        )

        cobranca_id = cobranca.get(
            "id"
        )

        if not cobranca_id:

            raise Exception(
                "O Asaas não retornou o ID da cobrança."
            )

        # =================================================
        # REGISTRAR PAGAMENTO NO BANCO
        # =================================================

        criar_pagamento(
            usuario_id=usuario.id,
            valor=valor,
            asaas_id=cobranca_id
        )

        # =================================================
        # OBTER QR CODE
        # =================================================

        pix = obter_qrcode_pix(
            cobranca_id
        )

        payload = pix.get(
            "payload",
            ""
        )

        encoded_image = pix.get(
            "encodedImage"
        )

        # =================================================
        # APAGAR MENSAGEM "GERANDO"
        # =================================================

        try:

            await mensagem.delete()

        except Exception:

            pass

        # =================================================
        # ENVIAR QR CODE
        # =================================================

        if encoded_image:

            try:

                imagem = base64.b64decode(
                    encoded_image
                )

                arquivo = BytesIO(
                    imagem
                )

                arquivo.name = "pix.png"

                await update.message.reply_photo(
                    photo=arquivo,
                    caption=(
                        "💳 *PAGAMENTO PIX*\n\n"
                        f"💰 Valor: R$ {valor:.2f}\n\n"
                        "📱 Escaneie o QR Code acima "
                        "para realizar o pagamento.\n\n"
                        "👇 Ou use o PIX Copia e Cola "
                        "abaixo."
                    ),
                    parse_mode="Markdown"
                )

            except Exception as erro:

                print(
                    "Erro ao enviar QR Code:",
                    erro
                )

        # =================================================
        # ENVIAR PIX COPIA E COLA
        # =================================================

        if payload:

            await update.message.reply_text(
                "📋 *PIX COPIA E COLA*\n\n"
                f"`{payload}`\n\n"
                "⚠️ Copie o código acima e "
                "pague no aplicativo do seu banco.\n\n"
                f"💰 Valor: R$ {valor:.2f}\n\n"
                "Após o pagamento, aguarde a "
                "confirmação.",
                parse_mode="Markdown"
            )

        else:

            await update.message.reply_text(
                "⚠️ A cobrança foi criada, "
                "mas o código PIX não foi retornado.\n\n"
                f"ID da cobrança: `{cobranca_id}`",
                parse_mode="Markdown"
            )

    except Exception as erro:

        print(
            "ERRO ASAAS:",
            repr(erro)
        )

        try:

            await mensagem.delete()

        except Exception:

            pass

        await update.message.reply_text(
            "❌ *Não foi possível gerar o PIX.*\n\n"
            "Ocorreu um erro ao criar a cobrança.\n\n"
            "Tente novamente em alguns instantes.",
            parse_mode="Markdown"
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

    # =====================================================
    # CATÁLOGO
    # =====================================================

    if acao == "catalogo":

        await query.edit_message_text(
            "🛒 *LOGINS | CONTAS PREMIUM*\n\n"
            "Escolha um produto:",
            reply_markup=menu_catalogo(),
            parse_mode="Markdown"
        )

    # =====================================================
    # PRODUTO
    # =====================================================

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

        (
            _,
            nome,
            descricao,
            preco,
            estoque
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
                    )
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

    # =====================================================
    # COMPRAR
    # =====================================================

    elif acao.startswith("comprar_"):

        produto_id = int(
            acao.split("_")[1]
        )

        await comprar_produto(
            query,
            produto_id,
            usuario_id
        )

    # =====================================================
    # SALDO
    # =====================================================

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

    # =====================================================
    # ADICIONAR SALDO
    # =====================================================

    elif acao == "adicionar_saldo":

        await pedir_valor_saldo(
            query,
            context
        )

    # =====================================================
    # PERFIL
    # =====================================================

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

    # =====================================================
    # VOLTAR
    # =====================================================

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

    # =====================================================
    # CARRINHO
    # =====================================================

    elif acao == "carrinho":

        await query.edit_message_text(
            "🛍️ *CARRINHO*\n\n"
            "Seu carrinho está vazio.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # PESQUISAR
    # =====================================================

    elif acao == "pesquisar":

        await query.edit_message_text(
            "🔎 *PESQUISAR SERVIÇO*\n\n"
            "Sistema de pesquisa em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # ESTOQUE
    # =====================================================

    elif acao == "estoque":

        await query.edit_message_text(
            "📦 *ESTOQUE DE LOGINS*\n\n"
            "Consulte os produtos disponíveis "
            "no catálogo.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # MAC
    # =====================================================

    elif acao == "mac":

        await query.edit_message_text(
            "🎮 *ATIVAÇÃO DE MAC*\n\n"
            "Sistema de ativação em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # JOGOS
    # =====================================================

    elif acao == "jogos":

        await query.edit_message_text(
            "⚽ *JOGOS NA TV*\n\n"
            "Informações sobre jogos serão "
            "adicionadas aqui.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # RENOVAR
    # =====================================================

    elif acao == "renovar":

        await query.edit_message_text(
            "♻️ *RENOVAR CONTA*\n\n"
            "Sistema de renovação em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # SUPORTE
    # =====================================================

    elif acao == "suporte":

        await query.edit_message_text(
            "🆘 *SUPORTE*\n\n"
            "Entre em contato com o suporte.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # TERMOS
    # =====================================================

    elif acao == "termos":

        await query.edit_message_text(
            "📜 *TERMOS DE USO*\n\n"
            "Os termos de uso serão adicionados aqui.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # OUTROS BOTS
    # =====================================================

    elif acao == "outros_bots":

        await query.edit_message_text(
            "🤖 *OUTROS BOTS*\n\n"
            "Em breve.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # GRUPO
    # =====================================================

    elif acao == "grupo":

        await query.edit_message_text(
            "👥 *GRUPO DE CLIENTES*\n\n"
            "Entre no nosso grupo de clientes "
            "pelo botão abaixo.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "👥 ENTRAR NO GRUPO",
                        url=GRUPO_CLIENTES
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Voltar",
                        callback_data="voltar_menu"
                    )
                ]
            ]),
            parse_mode="Markdown"
        )

    # =====================================================
    # ALUGAR
    # =====================================================

    elif acao == "alugar":

        await query.edit_message_text(
            "📣 *ALUGAR ESTE BOT*\n\n"
            "Em breve você poderá solicitar "
            "seu próprio bot.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # =====================================================
    # SEM ESTOQUE
    # =====================================================

    elif acao == "sem_estoque":

        await query.answer(
            "📦 O estoque está vazio.",
            show_alert=True
        )


# =========================================================
# MAIN
# =========================================================

def main():

    verificar_configuracao()

    criar_tabelas()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    app.add_handle
