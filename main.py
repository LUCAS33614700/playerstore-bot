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
    retirar_login_disponivel,
    listar_todos_produtos,
    consultar_estoque_logins,
    buscar_categoria,
)

from menu import menu_principal
from catalogo import (
    menu_catalogo,
    menu_categorias,
    menu_produtos_categoria,
    buscar_produto,
)
from pushinpay import criar_pix, consultar_pix

from admin import (
    comando_admin,
    botoes_admin,
    processar_admin_texto,
)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

VALOR_MINIMO = 5.00
VALOR_MAXIMO = 499.00
INTERVALO_VERIFICACAO = 5

VERIFICADOR_TASK = "verificador_pagamentos_task"


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    usuario = update.effective_user

    if not usuario:
        return

    criar_usuario(
        usuario.id,
        usuario.first_name or "",
        usuario.username or "",
    )

    context.user_data.clear()

    texto = (
        f"👋 Olá, {usuario.first_name or 'cliente'}!\n\n"
        "🛒 Bem-vindo à PLAYER STORE!\n\n"
        "Escolha uma opção abaixo:"
    )

    if update.message:
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
    produto = buscar_produto(produto_id)

    if not produto:
        await query.answer(
            "❌ Produto não encontrado.",
            show_alert=True,
        )
        return

    _, nome, descricao, preco, estoque = produto

    preco = float(preco)
    estoque = int(estoque)
    quantidade = int(quantidade)

    if quantidade <= 0:
        await query.answer(
            "❌ Quantidade inválida.",
            show_alert=True,
        )
        return

    # O estoque real de contas é a tabela logins.
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM logins
            WHERE produto_id = ?
              AND status = 'disponivel'
            """,
            (produto_id,),
        )
        estoque_logins = int(cursor.fetchone()[0])
    except Exception as erro:
        conn.close()
        print("ERRO AO CONSULTAR ESTOQUE DE LOGINS:", repr(erro))
        await query.answer(
            "❌ Não foi possível consultar o estoque.",
            show_alert=True,
        )
        return
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if estoque_logins < quantidade:
        await query.answer(
            f"❌ Estoque insuficiente.\n\n"
            f"📦 Disponível: {estoque_logins}\n"
            f"🛒 Solicitado: {quantidade}",
            show_alert=True,
        )
        return

    valor_total = preco * quantidade

    saldo = float(consultar_saldo(usuario_id) or 0)

    if saldo < valor_total:
        await query.edit_message_text(
            "❌ *SALDO INSUFICIENTE*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🛒 *Produto:* {nome}\n"
            f"💰 *Total:* R$ {valor_total:.2f}\n"
            f"💳 *Seu saldo:* R$ {saldo:.2f}\n"
            f"💵 *Faltam:* R$ {valor_total - saldo:.2f}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Adicione saldo para concluir a compra.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💵 ADICIONAR SALDO",
                            callback_data="adicionar_saldo",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ Voltar ao produto",
                            callback_data=f"produto_{produto_id}",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
        )
        return

    # Retira o saldo antes da criação do pedido.
    sucesso = retirar_saldo(usuario_id, valor_total)

    if not sucesso:
        await query.answer(
            "❌ Não foi possível realizar a compra.",
            show_alert=True,
        )
        return

    pedido_id = None

    try:
        conn = conectar()
        cursor = conn.cursor()

        # Confere novamente o estoque imediatamente antes do pedido.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM logins
            WHERE produto_id = ?
              AND status = 'disponivel'
            """,
            (produto_id,),
        )
        estoque_atual = int(cursor.fetchone()[0])

        if estoque_atual < quantidade:
            conn.close()
            adicionar_saldo(usuario_id, valor_total)

            await query.answer(
                "❌ O estoque mudou. Tente novamente.",
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
            VALUES (?, ?, ?, ?, 'pago')
            """,
            (
                usuario_id,
                produto_id,
                quantidade,
                valor_total,
            ),
        )

        pedido_id = cursor.lastrowid
        conn.commit()
        conn.close()

    except Exception as erro:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass

        adicionar_saldo(usuario_id, valor_total)

        print("ERRO AO REGISTRAR COMPRA:", repr(erro))

        await query.answer(
            "❌ Erro ao finalizar a compra.",
            show_alert=True,
        )
        return

    # Entrega das contas.
    contas_entregues = []

    try:
        for _ in range(quantidade):
            login = retirar_login_disponivel(
                produto_id,
                usuario_id,
                pedido_id,
            )

            if not login:
                raise RuntimeError(
                    "Não existe login disponível para entrega."
                )

            contas_entregues.append(login["dados"])

    except Exception as erro:
        print("ERRO NA ENTREGA:", repr(erro))

        adicionar_saldo(usuario_id, valor_total)

        try:
            conn = conectar()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE pedidos
                SET status = 'cancelado'
                WHERE id = ?
                """,
                (pedido_id,),
            )
            conn.commit()
            conn.close()
        except Exception as erro_db:
            print("ERRO AO CANCELAR PEDIDO:", repr(erro_db))

        await query.edit_message_text(
            "❌ *COMPRA NÃO CONCLUÍDA*\n\n"
            "O estoque de contas acabou antes da entrega.\n\n"
            "💰 O valor foi devolvido ao seu saldo.",
            reply_markup=InlineKeyboardMarkup(
                [
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
            ),
            parse_mode="Markdown",
        )
        return

    novo_saldo = float(consultar_saldo(usuario_id) or 0)

    texto_contas = ""

    for indice, dados in enumerate(contas_entregues, start=1):
        texto_contas += (
            f"\n🔐 *CONTA {indice}*\n"
            f"```\n{dados}\n```\n"
        )

    texto = (
        "✅ *COMPRA REALIZADA!*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛒 *Produto:* {nome}\n"
        f"📦 *Quantidade:* {quantidade}\n"
        f"💰 *Preço unitário:* R$ {preco:.2f}\n"
        f"💵 *Total:* R$ {valor_total:.2f}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🎁 *SEUS DADOS DE ACESSO*\n"
        f"{texto_contas}"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 *Saldo restante:* R$ {novo_saldo:.2f}\n\n"
        "⚡ Entrega realizada automaticamente."
    )

    botoes = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🛒 Comprar novamente",
                    callback_data=f"produto_{produto_id}",
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
    produto = buscar_produto(produto_id)

    if not produto:
        await query.answer(
            "❌ Produto não encontrado.",
            show_alert=True,
        )
        return

    _, nome, descricao, preco, estoque = produto

    preco = float(preco)
    estoque = int(estoque)

    # Estoque real.
    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM logins
            WHERE produto_id = ?
              AND status = 'disponivel'
            """,
            (produto_id,),
        )
        estoque_real = int(cursor.fetchone()[0])
    except Exception as erro:
        print("ERRO AO CONSULTAR ESTOQUE:", repr(erro))
        estoque_real = estoque
    finally:
        conn.close()

    if estoque_real <= 0:
        await query.answer(
            "📦 Produto sem estoque.",
            show_alert=True,
        )
        return

    context.user_data["aguardando_quantidade"] = True
    context.user_data["produto_quantidade_id"] = produto_id
    context.user_data["aguardando_valor"] = False

    await query.edit_message_text(
        "🛍️ *COMPRAR EM QUANTIDADE*\n\n"
        f"🛒 *Produto:* {nome}\n"
        f"💰 *Preço unitário:* R$ {preco:.2f}\n"
        f"📦 *Disponível:* {estoque_real}\n\n"
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
                        callback_data=f"produto_{produto_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "↩️ Voltar ao menu",
                        callback_data="voltar_menu",
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
    if not context.user_data.get("aguardando_quantidade"):
        return False

    if not update.message:
        return True

    produto_id = context.user_data.get("produto_quantidade_id")

    if not produto_id:
        context.user_data["aguardando_quantidade"] = False
        return True

    texto = (update.message.text or "").strip()

    try:
        quantidade = int(texto)
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

    produto = buscar_produto(produto_id)

    if not produto:
        context.user_data["aguardando_quantidade"] = False
        await update.message.reply_text(
            "❌ Produto não encontrado."
        )
        return True

    _, nome, descricao, preco, estoque = produto

    preco = float(preco)

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM logins
            WHERE produto_id = ?
              AND status = 'disponivel'
            """,
            (produto_id,),
        )
        estoque_logins = int(cursor.fetchone()[0])
    except Exception as erro:
        print("ERRO AO CONSULTAR ESTOQUE:", repr(erro))
        estoque_logins = 0
    finally:
        conn.close()

    if quantidade > estoque_logins:
        await update.message.reply_text(
            f"❌ Quantidade indisponível.\n\n"
            f"📦 Contas disponíveis: {estoque_logins}\n"
            f"🛒 Você pediu: {quantidade}"
        )
        return True

    valor_total = preco * quantidade
    saldo = float(
        consultar_saldo(update.effective_user.id) or 0
    )

    if saldo < valor_total:
        await update.message.reply_text(
            f"❌ Saldo insuficiente.\n\n"
            f"💳 Seu saldo: R$ {saldo:.2f}\n"
            f"💰 Total: R$ {valor_total:.2f}\n\n"
            f"💵 Faltam: R$ {valor_total - saldo:.2f}"
        )
        return True

    context.user_data["aguardando_quantidade"] = False
    context.user_data["quantidade_produto"] = quantidade

    texto = (
        "🛒 *CONFIRMAR COMPRA*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ *Produto:* {nome}\n"
        f"📦 *Quantidade:* {quantidade}\n"
        f"💰 *Preço unitário:* R$ {preco:.2f}\n"
        f"💵 *Total:* R$ {valor_total:.2f}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 *Seu saldo:* R$ {saldo:.2f}\n"
        f"💳 *Saldo após compra:* R$ {saldo - valor_total:.2f}\n\n"
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
                        f"confirmar_compra_{produto_id}_{quantidade}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar ao produto",
                    callback_data=f"produto_{produto_id}",
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
    context.user_data["aguardando_valor"] = True
    context.user_data["valor_saldo"] = None
    context.user_data["aguardando_quantidade"] = False
    context.user_data["produto_quantidade_id"] = None

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
                        callback_data="voltar_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# QR CODE BASE64
# =========================================================

def converter_qr_code_base64(qr_code_base64):
    if not qr_code_base64:
        return None

    try:
        valor = str(qr_code_base64).strip()

        if "," in valor:
            valor = valor.split(",", 1)[1]

        dados = base64.b64decode(
            valor,
            validate=False,
        )

        if not dados:
            return None

        arquivo = io.BytesIO(dados)
        arquivo.seek(0)
        return arquivo

    except (
        ValueError,
        TypeError,
        binascii.Error,
    ):
        print("QR Code Base64 inválido.")
        return None


# =========================================================
# PROCESSAR VALOR
# =========================================================

async def processar_valor_saldo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.user_data.get("aguardando_valor"):
        return

    if not update.message:
        return

    texto = (update.message.text or "").strip()

    try:
        valor = float(
            texto.replace(",", ".")
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
            f"❌ O valor mínimo é R$ {VALOR_MINIMO:.2f}."
        )
        return

    if valor > VALOR_MAXIMO:
        await update.message.reply_text(
            f"❌ O valor máximo é R$ {VALOR_MAXIMO:.2f}."
        )
        return

    valor = round(valor, 2)

    context.user_data["valor_saldo"] = valor
    context.user_data["aguardando_valor"] = False

    usuario = update.effective_user

    mensagem = await update.message.reply_text(
        "⏳ *Gerando seu PIX...*",
        parse_mode="Markdown",
    )

    try:
        pix = await asyncio.to_thread(
            criar_pix,
            valor,
        )

        if not isinstance(pix, dict):
            raise RuntimeError(
                "Resposta inválida da PushinPay."
            )

        transacao_id = pix.get("id")
        qr_code = pix.get("qr_code")
        qr_code_base64 = pix.get("qr_code_base64")

        if not transacao_id:
            raise RuntimeError(
                "PushinPay não retornou o ID da transação."
            )

        if not qr_code:
            raise RuntimeError(
                "PushinPay não retornou o código PIX."
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
            "⚡ Após o pagamento, a confirmação será feita "
            "automaticamente.\n\n"
            "💰 O saldo será liberado assim que o pagamento "
            "for confirmado."
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
                    callback_data=f"status_pagamento_{transacao_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar ao menu",
                    callback_data="voltar_menu",
                )
            ],
        ]

        markup = InlineKeyboardMarkup(botoes)

        imagem_qr = converter_qr_code_base64(
            qr_code_base64
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
        print("ERRO AO GERAR PIX:", repr(erro))

        try:
            await mensagem.edit_text(
                "❌ *Não foi possível gerar o PIX.*\n\n"
                "Ocorreu um erro ao comunicar com a PushinPay.\n\n"
                "Tente novamente em alguns instantes.",
                parse_mode="Markdown",
            )
        except Exception:
            pass


# =========================================================
# PROCESSAR TEXTO
# =========================================================

async def processar_mensagem_texto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        if await processar_admin_texto(
            update,
            context,
        ):
            return
    except Exception as erro:
        print("ERRO NO PROCESSAMENTO ADMIN:", repr(erro))

    if context.user_data.get("aguardando_quantidade"):
        await processar_quantidade_produto(
            update,
            context,
        )
        return

    if context.user_data.get("aguardando_valor"):
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
        pagamento = consultar_pagamento(transacao_id)

        if not pagamento:
            await query.answer(
                "❌ Pagamento não encontrado.",
                show_alert=True,
            )
            return

        usuario_id = pagamento[1]
        valor = float(pagamento[2])
        status_banco = pagamento[4]

        if status_banco == "pago":
            saldo = consultar_saldo(usuario_id)

            await query.answer(
                f"✅ Pagamento já confirmado.\n"
                f"Saldo: R$ {float(saldo):.2f}",
                show_alert=True,
            )
            return

        transacao = await asyncio.to_thread(
            consultar_pix,
            transacao_id,
        )

        status = str(
            transacao.get("status", "")
        ).lower()

        print(
            f"Pagamento {transacao_id}: {status}"
        )

        if status == "paid":
            resultado = processar_pagamento_pago(
                transacao_id
            )

            if resultado:
                saldo = consultar_saldo(usuario_id)

                await query.edit_message_text(
                    "✅ *PAGAMENTO CONFIRMADO!*\n\n"
                    f"💰 Valor recebido: R$ {valor:.2f}\n\n"
                    f"💳 Novo saldo: R$ {float(saldo):.2f}\n\n"
                    "🎉 Seu saldo foi adicionado com sucesso!",
                    reply_markup=menu_principal(),
                    parse_mode="Markdown",
                )
            else:
                await query.answer(
                    "✅ Pagamento já processado.",
                    show_alert=True,
                )

            return

        if status in ("created", "pending"):
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
            f"Status atual: {status or 'desconhecido'}",
            show_alert=True,
        )

    except Exception as erro:
        print(
            "ERRO AO CONSULTAR PAGAMENTO:",
            repr(erro),
        )

        await query.answer(
            "❌ Erro ao consultar o pagamento.",
            show_alert=True,
        )


# =========================================================
# VERIFICAÇÃO AUTOMÁTICA
# =========================================================
# IMPORTANTE:
# Não usamos JobQueue.
# Isso evita crash quando o pacote job-queue não está instalado
# no Railway. O verificador roda em uma task asyncio própria.

async def verificar_pagamentos_automaticamente(
    context: ContextTypes.DEFAULT_TYPE,
):
    pagamentos = listar_pagamentos_pendentes()

    if not pagamentos:
        return

    print(
        f"🔎 Verificando {len(pagamentos)} pagamento(s)..."
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

            transacao = await asyncio.to_thread(
                consultar_pix,
                transacao_id,
            )

            status = str(
                transacao.get("status", "")
            ).lower()

            print(
                f"PIX {transacao_id}: {status}"
            )

            if status == "paid":
                resultado = processar_pagamento_pago(
                    transacao_id
                )

                if not resultado:
                    continue

                novo_saldo = consultar_saldo(
                    usuario_id
                )

                try:
                    await context.bot.send_message(
                        chat_id=usuario_id,
                        text=(
                            "✅ *PAGAMENTO APROVADO!*\n\n"
                            "━━━━━━━━━━━━━━━━━━\n"
                            f"💰 Valor: R$ {float(valor):.2f}\n"
                            f"🆔 ID: `{transacao_id}`\n"
                            "━━━━━━━━━━━━━━━━━━\n\n"
                            f"💳 *Novo saldo:* R$ {float(novo_saldo):.2f}\n\n"
                            "🎉 Seu saldo foi liberado automaticamente!"
                        ),
                        reply_markup=menu_principal(),
                        parse_mode="Markdown",
                    )
                except Exception as erro_envio:
                    print(
                        "ERRO AO ENVIAR CONFIRMAÇÃO:",
                        repr(erro_envio),
                    )

                continue

            if status in (
                "canceled",
                "cancelled",
                "expired",
            ):
                atualizado = atualizar_status_pagamento(
                    transacao_id,
                    "cancelado",
                )

                if atualizado:
                    try:
                        await context.bot.send_message(
                            chat_id=usuario_id,
                            text=(
                                "❌ *PAGAMENTO ENCERRADO*\n\n"
                                f"💰 Valor: R$ {float(valor):.2f}\n\n"
                                "A cobrança PIX foi cancelada ou expirou.\n\n"
                                "💳 Nenhum saldo foi adicionado."
                            ),
                            reply_markup=menu_principal(),
                            parse_mode="Markdown",
                        )
                    except Exception as erro_envio:
                        print(
                            "ERRO AO ENVIAR CANCELAMENTO:",
                            repr(erro_envio),
                        )

        except Exception as erro:
            try:
                pix_id = pagamento[3]
            except Exception:
                pix_id = "desconhecido"

            print(
                f"ERRO NA VERIFICAÇÃO DO PIX {pix_id}:",
                repr(erro),
            )


async def loop_verificador_pagamentos(
    application: Application,
):
    print("💳 Verificador automático de PIX iniciado.")

    while True:
        try:
            context = ContextTypes.DEFAULT_TYPE

            # Cria um objeto de contexto simples através da própria
            # aplicação para manter acesso ao bot.
            class VerificadorContext:
                bot = application.bot

            await verificar_pagamentos_automaticamente(
                VerificadorContext()
            )

        except asyncio.CancelledError:
            print("💳 Verificador automático encerrado.")
            raise

        except Exception as erro:
            print(
                "ERRO NO LOOP DO VERIFICADOR:",
                repr(erro),
            )

        await asyncio.sleep(
            INTERVALO_VERIFICACAO
        )


async def iniciar_verificador(
    application: Application,
):
    task = asyncio.create_task(
        loop_verificador_pagamentos(application),
        name=VERIFICADOR_TASK,
    )

    application.bot_data[
        VERIFICADOR_TASK
    ] = task


async def parar_verificador(
    application: Application,
):
    task = application.bot_data.get(
        VERIFICADOR_TASK
    )

    if task:
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass


# =========================================================
# ESTOQUE PÚBLICO DE LOGINS
# =========================================================

async def mostrar_estoque_logins(
    query,
):
    produtos = listar_todos_produtos()

    if not produtos:
        texto = (
            "📦 *ESTOQUE DE LOGINS*\n\n"
            "❌ Nenhum produto cadastrado no momento."
        )

    else:
        texto = (
            "📦 *ESTOQUE DE LOGINS*\n\n"
            "Quantidade de contas disponíveis "
            "por produto:\n\n"
        )

        for produto in produtos:

            produto_id = produto[0]
            nome = produto[1]

            quantidade = consultar_estoque_logins(
                produto_id
            )

            if quantidade > 0:
                status_emoji = "✅"
            else:
                status_emoji = "❌"

            texto += (
                f"{status_emoji} *{nome}*\n"
                f"📊 Disponível: {quantidade}\n\n"
            )

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 ATUALIZAR",
                        callback_data="estoque_logins",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🛒 VER CATÁLOGO",
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
        ),
        parse_mode="Markdown",
    )


# =========================================================
# STATUS DO PAGAMENTO
# =========================================================

async def mostrar_status_pagamento(
    query,
    transacao_id,
):
    pagamento = consultar_pagamento(
        transacao_id
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
            f"✅ Pago!\nSaldo: R$ {float(saldo):.2f}",
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

    if not query:
        return

    try:
        await query.answer()
    except Exception:
        pass

    usuario_id = query.from_user.id
    acao = query.data or ""

    # =====================================================
    # ADMIN
    # =====================================================

    if (
        acao == "admin_menu"
        or acao.startswith("admin_")
    ):
        try:
            await botoes_admin(
                update,
                context,
            )
        except Exception as erro:
            print("ERRO NO PAINEL ADMIN:", repr(erro))
            try:
                await query.answer(
                    "❌ Erro no painel administrativo.",
                    show_alert=True,
                )
            except Exception:
                pass
        return

    # =====================================================
    # STATUS PAGAMENTO
    # =====================================================

    if acao.startswith("status_pagamento_"):
        transacao_id = acao.replace(
            "status_pagamento_",
            "",
            1,
        )

        await mostrar_status_pagamento(
            query,
            transacao_id,
        )
        return

    # =====================================================
    # CONSULTAR PAGAMENTO
    # =====================================================

    if acao.startswith("consultar_pagamento_"):
        transacao_id = acao.replace(
            "consultar_pagamento_",
            "",
            1,
        )

        await verificar_pagamento(
            query,
            transacao_id,
        )
        return

    # =====================================================
    # ESTOQUE DE LOGINS (PÚBLICO)
    # =====================================================

    if acao == "estoque_logins":
        await mostrar_estoque_logins(
            query,
        )
        return

    # =====================================================
    # CATÁLOGO (CATEGORIAS)
    # =====================================================

    if acao == "catalogo":
        context.user_data["aguardando_quantidade"] = False
        context.user_data["aguardando_valor"] = False

        await query.edit_message_text(
            "🛒 *LOGINS | CONTAS PREMIUM*\n\n"
            "Selecione a categoria:",
            reply_markup=menu_categorias(),
            parse_mode="Markdown",
        )
        return

    # =====================================================
    # PRODUTOS DE UMA CATEGORIA
    # =====================================================

    if acao.startswith("categoria_"):
        try:
            categoria_id = int(
                acao.split("_", 1)[1]
            )
        except (ValueError, IndexError):
            await query.answer(
                "❌ Categoria inválida.",
                show_alert=True,
            )
            return

        categoria = buscar_categoria(
            categoria_id
        )

        if not categoria:
            await query.answer(
                "❌ Categoria não encontrada.",
                show_alert=True,
            )
            return

        emoji = categoria[2]
        nome_categoria = categoria[1]

        await query.edit_message_text(
            f"{emoji} *{nome_categoria.upper()}*\n\n"
            "Escolha um produto:",
            reply_markup=menu_produtos_categoria(
                categoria_id
            ),
            parse_mode="Markdown",
        )
        return

    # =====================================================
    # PRODUTO
    # =====================================================

    if acao.startswith("produto_"):
        try:
            produto_id = int(
                acao.split("_", 1)[1]
            )
        except (ValueError, IndexError):
            await query.answer(
                "❌ Produto inválido.",
                show_alert=True,
            )
            return

        produto = buscar_produto(produto_id)

        if not produto:
            await query.answer(
                "❌ Produto não encontrado.",
                show_alert=True,
            )
            return

        _, nome, descricao, preco, estoque = produto
        preco = float(preco)

        conn = conectar()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM logins
                WHERE produto_id = ?
                  AND status = 'disponivel'
                """,
                (produto_id,),
            )
            estoque_real = int(cursor.fetchone()[0])
        except Exception as erro:
            print("ERRO AO CONSULTAR ESTOQUE:", repr(erro))
            estoque_real = 0
        finally:
            conn.close()

        if estoque_real <= 0:
            await query.answer(
                "📦 Produto sem contas disponíveis.",
                show_alert=True,
            )
            return

        saldo = float(
            consultar_saldo(usuario_id) or 0
        )

        texto = (
            "🛒 *FINALIZAR COMPRA*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🛍️ *Serviço:* {nome}\n"
            f"💰 *Preço:* R$ {preco:.2f}\n"
            f"💳 *Seu saldo:* R$ {saldo:.2f}\n"
            f"📦 *Disponível:* {estoque_real}\n"
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
                    callback_data=f"comprar_{produto_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🛍️ COMPRAR EM QUANTIDADE",
                    callback_data=f"quantidade_{produto_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "💵 ADICIONAR SALDO",
                    callback_data="adicionar_saldo",
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

    if acao.startswith("quantidade_"):
        try:
            produto_id = int(
                acao.split("_", 1)[1]
            )
        except (ValueError, IndexError):
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

    if acao.startswith("confirmar_compra_"):
        partes = acao.split("_")

        try:
            produto_id = int(partes[2])
            quantidade = int(partes[3])
        except (ValueError, IndexError):
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

        context.user_data["quantidade_produto"] = None
        return

    # =====================================================
    # COMPRAR
    # =====================================================

    if acao.startswith("comprar_"):
        try:
            produto_id = int(
                acao.split("_", 1)[1]
            )
        except (ValueError, IndexError):
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
        saldo = float(
            consultar_saldo(usuario_id) or 0
        )

        botoes_saldo = [
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

        await query.edit_message_text(
            "💳 *MEU SALDO*\n\n"
            f"💰 Saldo atual: R$ {saldo:.2f}\n\n"
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
        context.user_data.clear()

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
        botoes_grupo = InlineKeyboardMarkup(
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
                        callback_data="voltar_menu",
                    )
                ],
            ]
        )

        await query.edit_message_text(
            "👥 *GRUPO DE CLIENTES*\n\n"
            "Entre no nosso grupo para acompanhar "
            "novidades e referências.",
            reply_markup=botoes_grupo,
            parse_mode="Markdown",
        )
        return

    # =====================================================
    # PERFIL
    # =====================================================

    if acao == "perfil":
        usuario = consultar_usuario(usuario_id)
        saldo = float(
            consultar_saldo(usuario_id) or 0
        )

        nome = (
            query.from_user.full_name
            or query.from_user.first_name
            or "Usuário"
        )

        username = query.from_user.username

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
                            callback_data="voltar_menu",
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
            "Escolha um produto no catálogo e clique em Comprar.\n\n"
            "🛍️ *Comprar em quantidade*\n"
            "Escolha a quantidade desejada e confirme a compra.\n\n"
            "💳 *Adicionar saldo*\n"
            "Escolha o valor e o bot irá gerar um PIX automaticamente.\n\n"
            "💰 *Saldo*\n"
            "Veja seu saldo disponível.\n\n"
            "⚡ *Pagamento automático*\n"
            "Depois de pagar o PIX, não é necessário enviar comprovante "
            "nem ficar consultando manualmente.\n\n"
            "🤖 O sistema verifica automaticamente a confirmação.",
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
# ERRO GLOBAL
# =========================================================

async def erro_global(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print("❌ ERRO GLOBAL:")
    print(repr(context.error))


# =========================================================
# MAIN
# =========================================================

def main():
    verificar_configuracao()
    criar_tabelas()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(iniciar_verificador)
        .post_shutdown(parar_verificador)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "admin",
            comando_admin,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            botoes
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            processar_mensagem_texto,
        )
    )

    application.add_error_handler(
        erro_global
    )

    print("🤖 PLAYER STORE iniciado!")
    print("👑 Painel ADM: /admin")
    print(
        "💳 Verificador PIX: asyncio "
        f"(intervalo de {INTERVALO_VERIFICACAO}s)"
    )

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":
    main()
