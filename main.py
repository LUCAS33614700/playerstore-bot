import asyncio
import re
import base64
import binascii
import io
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CopyTextButton,
    InlineQueryResultArticle,
    InputTextMessageContent,
    BotCommand,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    InlineQueryHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    verificar_configuracao,
    GRUPO_CLIENTES,
    ADMIN_ID,
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
    obter_configuracao,
    adicionar_item_carrinho,
    listar_itens_carrinho,
    remover_item_carrinho,
    limpar_carrinho,
    buscar_produtos_por_nome,
    obter_imagem_produto,
    contar_compras_usuario,
    salvar_topico_suporte,
    obter_topico_suporte,
    obter_usuario_por_topico,
    usuario_ja_recebeu_lembrete,
    marcar_lembrete_enviado,
    listar_logins_vencendo,
    marcar_aviso_vencimento_enviado,
    listar_contas_usuario,
    consultar_login,
    produto_ja_alertou_estoque_baixo,
    marcar_alerta_estoque_enviado,
    resetar_alerta_estoque,
    relatorio_vendas_periodo,
    registrar_aviso_reposicao,
    listar_interessados_reposicao,
    remover_avisos_reposicao,
)

from menu import menu_principal
from catalogo import (
    menu_catalogo,
    menu_categorias,
    menu_produtos_categoria,
    texto_selecionar_categoria,
    buscar_produto,
    listar_produtos,
)
from pushinpay import criar_pix, consultar_pix

from admin import (
    comando_admin,
    botoes_admin,
    processar_admin_texto,
    processar_admin_midia,
)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

VALOR_MINIMO = 5.00
VALOR_MAXIMO = 499.00
INTERVALO_VERIFICACAO = 5

VERIFICADOR_TASK = "verificador_pagamentos_task"
VERIFICADOR_VENCIMENTOS_TASK = "verificador_vencimentos_task"
RELATORIO_VENDAS_TASK = "relatorio_vendas_task"
INTERVALO_VERIFICACAO_VENCIMENTOS = 60 * 60


# =========================================================
# MODO MANUTENÇÃO
# =========================================================

TEXTO_MANUTENCAO = (
    "🛠️ *BOT EM MANUTENÇÃO*\n\n"
    "Estamos atualizando nosso estoque/sistema "
    "no momento.\n\n"
    "Voltamos em breve! Tente novamente daqui "
    "a pouco. 🙏"
)


def modo_manutencao_ativo():
    return (
        obter_configuracao("modo_manutencao")
        == "1"
    )


def eh_admin_principal(user_id):
    try:
        return int(user_id) == int(ADMIN_ID)
    except (ValueError, TypeError):
        return False


# =========================================================
# ESTOQUE BAIXO
# =========================================================

ESTOQUE_MINIMO_PADRAO = 3


async def verificar_estoque_baixo(
    bot,
    produto_id,
    nome_produto,
):

    try:

        limite = obter_configuracao(
            "estoque_minimo"
        )

        limite = (
            int(limite)
            if limite
            else ESTOQUE_MINIMO_PADRAO
        )

        estoque_atual = consultar_estoque_logins(
            produto_id
        )

        if estoque_atual > limite:
            resetar_alerta_estoque(
                produto_id
            )
            return

        if produto_ja_alertou_estoque_baixo(
            produto_id
        ):
            return

        marcar_alerta_estoque_enviado(
            produto_id
        )

        destino = (
            obter_configuracao("suporte_chat_id")
            or ADMIN_ID
        )

        await bot.send_message(
            chat_id=destino,
            text=(
                "📉 *ESTOQUE BAIXO*\n\n"
                f"📦 *Produto:* {nome_produto}\n"
                f"🔐 *Restam:* {estoque_atual} "
                "conta(s)\n\n"
                "Considere repor o estoque em "
                "breve."
            ),
            parse_mode="Markdown",
        )

    except Exception as erro:
        print(
            "ERRO NO ALERTA DE ESTOQUE BAIXO:",
            repr(erro),
        )


# =========================================================
# ENVIAR MENU PRINCIPAL (COM BANNER, SE CADASTRADO)
# =========================================================

async def enviar_menu_principal(
    chat_id,
    context: ContextTypes.DEFAULT_TYPE,
    texto,
):

    imagem_id = obter_configuracao(
        "imagem_catalogo_id"
    )
    imagem_tipo = obter_configuracao(
        "imagem_catalogo_tipo"
    )

    if imagem_id:

        try:
            if imagem_tipo == "animation":
                await context.bot.send_animation(
                    chat_id=chat_id,
                    animation=imagem_id,
                    caption=texto,
                    reply_markup=menu_principal(),
                    parse_mode="Markdown",
                )
            else:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=imagem_id,
                    caption=texto,
                    reply_markup=menu_principal(),
                    parse_mode="Markdown",
                )
            return
        except Exception as erro:
            print(
                "ERRO AO ENVIAR BANNER DO MENU:",
                repr(erro),
            )

    await context.bot.send_message(
        chat_id=chat_id,
        text=texto,
        reply_markup=menu_principal(),
        parse_mode="Markdown",
    )


# =========================================================
# LEMBRETE DE COMPRA (5 MINUTOS APÓS O /start)
# =========================================================

LEMBRETE_DELAY_SEGUNDOS = 5 * 60


async def enviar_lembrete_compra(
    bot,
    usuario_id,
):

    await asyncio.sleep(
        LEMBRETE_DELAY_SEGUNDOS
    )

    try:

        if usuario_ja_recebeu_lembrete(
            usuario_id
        ):
            return

        if contar_compras_usuario(
            usuario_id
        ) > 0:
            return

        if modo_manutencao_ativo():
            return

        marcar_lembrete_enviado(
            usuario_id
        )

        await bot.send_message(
            chat_id=usuario_id,
            text=(
                "👋 Olá! Vi que você ainda não "
                "realizou nenhuma compra.\n\n"
                "Posso te ajudar? Escolha uma "
                "das opções abaixo 👇"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🆘 Suporte",
                            callback_data="suporte",
                        ),
                        InlineKeyboardButton(
                            "🛍️ Comprar Agora",
                            callback_data="catalogo",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "🛒 Carrinho",
                            callback_data="carrinho",
                        ),
                        InlineKeyboardButton(
                            "👀 Termos",
                            callback_data="termos",
                        ),
                    ],
                ]
            ),
        )

    except Exception as erro:
        print(
            "ERRO NO LEMBRETE DE COMPRA:",
            repr(erro),
        )


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

    if modo_manutencao_ativo() and not eh_admin_principal(
        usuario.id
    ):
        if update.message:
            await update.message.reply_text(
                TEXTO_MANUTENCAO,
                parse_mode="Markdown",
            )
        return

    criar_usuario(
        usuario.id,
        usuario.first_name or "",
        usuario.username or "",
    )

    context.user_data.clear()

    saldo = float(
        consultar_saldo(usuario.id) or 0
    )

    total_compras = contar_compras_usuario(
        usuario.id
    )

    username_texto = (
        f"`@{usuario.username}`"
        if usuario.username
        else "Não informado"
    )

    texto = (
        "✨ *BEM-VINDO À PLAYER STORE!* ✨\n\n"
        "🎬 O bot mais completo de contas premium "
        "e telas exclusivas!\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👤 *SUAS INFORMAÇÕES*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Nome: {usuario.first_name or 'cliente'}\n"
        f"✏️ Username: {username_texto}\n"
        f"🆔 ID: `{usuario.id}`\n"
        f"💲 Saldo: R$ {saldo:.2f}\n"
        f"🛍️ Compras: {total_compras}\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 Aproveite as melhores ofertas!"
    )

    if update.message:
        await enviar_menu_principal(
            update.message.chat_id,
            context,
            texto,
        )

    if not eh_admin_principal(usuario.id):
        asyncio.create_task(
            enviar_lembrete_compra(
                context.bot,
                usuario.id,
            )
        )


# =========================================================
# COMPRAR PRODUTO
# =========================================================

async def comprar_produto(
    query,
    context,
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
        await editar_ou_substituir(
            query,
            context,
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

        await editar_ou_substituir(
            query,
            context,
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

    await verificar_estoque_baixo(
        context.bot,
        produto_id,
        nome,
    )

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

    await editar_ou_substituir(
        query,
        context,
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

    await editar_ou_substituir(
        query,
        context,
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

    await editar_ou_substituir(
        query,
        context,
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
# PROCESSAR MÍDIA (FOTOS / GIFS)
# =========================================================

async def processar_midia_generico(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    usuario = update.effective_user

    if (
        usuario
        and modo_manutencao_ativo()
        and not eh_admin_principal(usuario.id)
    ):
        if update.message:
            await update.message.reply_text(
                TEXTO_MANUTENCAO,
                parse_mode="Markdown",
            )
        return

    try:
        tratado_admin = await processar_admin_midia(
            update,
            context,
        )
        if tratado_admin:
            return
    except Exception as erro:
        print(
            "ERRO NO PROCESSAMENTO DE MÍDIA ADMIN:",
            repr(erro),
        )

    if context.user_data.get("aguardando_suporte"):
        await processar_suporte(
            update,
            context,
        )
        return


# =========================================================
# PROCESSAR TEXTO
# =========================================================

async def processar_mensagem_texto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    usuario = update.effective_user

    if (
        usuario
        and modo_manutencao_ativo()
        and not eh_admin_principal(usuario.id)
    ):
        if update.message:
            await update.message.reply_text(
                TEXTO_MANUTENCAO,
                parse_mode="Markdown",
            )
        return

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

    if context.user_data.get("aguardando_pesquisa"):
        await processar_pesquisa_servico(
            update,
            context,
        )
        return

    if context.user_data.get("aguardando_suporte"):
        await processar_suporte(
            update,
            context,
        )
        return


# =========================================================
# VERIFICAR PAGAMENTO MANUAL
# =========================================================

async def verificar_pagamento(
    query,
    context,
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

                await editar_ou_substituir(
                    query,
                    context,
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

            await editar_ou_substituir(
                query,
                context,
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


# =========================================================
# AVISO DE VENCIMENTO (1 DIA ANTES) PRO ADMIN
# =========================================================

async def verificar_vencimentos_proximos(
    bot,
):

    contas = listar_logins_vencendo()

    if not contas:
        return

    print(
        f"⏳ {len(contas)} conta(s) vencendo em "
        "até 24h."
    )

    for conta in contas:

        try:
            (
                login_id,
                usuario_id,
                nome_cliente,
                username_cliente,
                produto_id,
                nome_produto,
                vendido_em,
                duracao_dias,
            ) = conta

            username_texto = (
                f"@{username_cliente}"
                if username_cliente
                else "Não informado"
            )

            texto = (
                "⏳ *CONTA VENCENDO EM ATÉ 24H*\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"📦 *Produto:* {nome_produto}\n"
                f"👤 *Cliente:* {nome_cliente or 'Não informado'}\n"
                f"🔗 *Username:* {username_texto}\n"
                f"🆔 *ID do cliente:* `{usuario_id}`\n"
                f"📅 *Vendido em:* {vendido_em}\n"
                f"⏳ *Duração:* {duracao_dias} dias\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "Considere entrar em contato pra "
                "oferecer renovação."
            )

            await bot.send_message(
                chat_id=ADMIN_ID,
                text=texto,
                parse_mode="Markdown",
            )

            marcar_aviso_vencimento_enviado(
                login_id
            )

        except Exception as erro:
            print(
                "ERRO AO AVISAR VENCIMENTO:",
                repr(erro),
            )


async def loop_verificador_vencimentos(
    application: Application,
):
    print(
        "⏳ Verificador de vencimentos iniciado."
    )

    while True:
        try:
            await verificar_vencimentos_proximos(
                application.bot
            )

        except asyncio.CancelledError:
            print(
                "⏳ Verificador de vencimentos "
                "encerrado."
            )
            raise

        except Exception as erro:
            print(
                "ERRO NO LOOP DE VENCIMENTOS:",
                repr(erro),
            )

        await asyncio.sleep(
            INTERVALO_VERIFICACAO_VENCIMENTOS
        )


INTERVALO_RELATORIO_VENDAS = 24 * 60 * 60


async def enviar_relatorio_vendas(
    bot,
):

    try:

        qtd_dia, total_dia = relatorio_vendas_periodo(24)
        qtd_semana, total_semana = relatorio_vendas_periodo(
            24 * 7
        )

        destino = (
            obter_configuracao("suporte_chat_id")
            or ADMIN_ID
        )

        await bot.send_message(
            chat_id=destino,
            text=(
                "📊 *RELATÓRIO DE VENDAS*\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "🗓️ *Últimas 24h*\n"
                f"🛍️ Vendas: {qtd_dia}\n"
                f"💰 Faturamento: R$ {total_dia:.2f}\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "🗓️ *Últimos 7 dias*\n"
                f"🛍️ Vendas: {qtd_semana}\n"
                f"💰 Faturamento: R$ {total_semana:.2f}\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            parse_mode="Markdown",
        )

    except Exception as erro:
        print(
            "ERRO NO RELATÓRIO DE VENDAS:",
            repr(erro),
        )


async def loop_relatorio_vendas(
    application: Application,
):
    print(
        "📊 Relatório automático de vendas iniciado."
    )

    while True:

        await asyncio.sleep(
            INTERVALO_RELATORIO_VENDAS
        )

        try:
            await enviar_relatorio_vendas(
                application.bot
            )

        except asyncio.CancelledError:
            print(
                "📊 Relatório automático de "
                "vendas encerrado."
            )
            raise

        except Exception as erro:
            print(
                "ERRO NO LOOP DE RELATÓRIO:",
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
    try:
        await application.bot.set_my_commands(
            [
                BotCommand(
                    "start",
                    "Iniciar Bot",
                ),
                BotCommand(
                    "pix",
                    "Adicionar saldo",
                ),
                BotCommand(
                    "admin",
                    "Menu adm",
                ),
                BotCommand(
                    "id",
                    "Mostrar seu ID do Telegram",
                ),
            ]
        )
    except Exception as erro:
        print(
            "ERRO AO REGISTRAR COMANDOS:",
            repr(erro),
        )

    task = asyncio.create_task(
        loop_verificador_pagamentos(application),
        name=VERIFICADOR_TASK,
    )

    application.bot_data[
        VERIFICADOR_TASK
    ] = task

    task_vencimentos = asyncio.create_task(
        loop_verificador_vencimentos(application),
        name=VERIFICADOR_VENCIMENTOS_TASK,
    )

    application.bot_data[
        VERIFICADOR_VENCIMENTOS_TASK
    ] = task_vencimentos

    task_relatorio = asyncio.create_task(
        loop_relatorio_vendas(application),
        name=RELATORIO_VENDAS_TASK,
    )

    application.bot_data[
        RELATORIO_VENDAS_TASK
    ] = task_relatorio


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

    task_vencimentos = application.bot_data.get(
        VERIFICADOR_VENCIMENTOS_TASK
    )

    if task_vencimentos:
        task_vencimentos.cancel()

        try:
            await task_vencimentos
        except asyncio.CancelledError:
            pass

    task_relatorio = application.bot_data.get(
        RELATORIO_VENDAS_TASK
    )

    if task_relatorio:
        task_relatorio.cancel()

        try:
            await task_relatorio
        except asyncio.CancelledError:
            pass


# =========================================================
# ESTOQUE PÚBLICO DE LOGINS
# =========================================================

async def mostrar_estoque_logins(
    query,
    context,
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

    await editar_ou_substituir(
        query,
        context,
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
# BUSCA INLINE (@seubot termo, em qualquer chat)
# =========================================================

async def pesquisa_inline(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    inline_query = update.inline_query

    if not inline_query:
        return

    if modo_manutencao_ativo() and not eh_admin_principal(
        inline_query.from_user.id
    ):
        try:
            await inline_query.answer(
                [
                    InlineQueryResultArticle(
                        id="manutencao",
                        title="🛠️ Bot em manutenção",
                        description=(
                            "Tente novamente em breve."
                        ),
                        input_message_content=(
                            InputTextMessageContent(
                                TEXTO_MANUTENCAO,
                                parse_mode="Markdown",
                            )
                        ),
                    )
                ],
                cache_time=1,
                is_personal=True,
            )
        except Exception:
            pass
        return

    termo = (inline_query.query or "").strip()

    if termo.lower().startswith("buscar_loguin"):
        termo = termo[len("buscar_loguin"):].strip()

    if termo:
        produtos = buscar_produtos_por_nome(
            termo
        )
    else:
        produtos = listar_produtos()

    resultados = []

    for produto in produtos[:50]:

        produto_id = produto[0]
        nome = produto[1]
        preco = float(produto[3])
        estoque = int(produto[4])

        imagem_url = obter_imagem_produto(
            produto_id
        )

        kwargs = {}

        if imagem_url:
            kwargs["thumbnail_url"] = imagem_url

        resultados.append(
            InlineQueryResultArticle(
                id=str(produto_id),
                title=nome,
                description=(
                    f"Valor: R${preco:.2f} | "
                    f"Estoque: {estoque}"
                ),
                input_message_content=(
                    InputTextMessageContent(
                        f"🛍️ *{nome}*\n\n"
                        f"💰 *Valor:* R$ {preco:.2f}\n"
                        f"📦 *Estoque:* {estoque}",
                        parse_mode="Markdown",
                    )
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🛒 Ver produto",
                                callback_data=(
                                    f"produto_{produto_id}"
                                ),
                            )
                        ]
                    ]
                ),
                **kwargs,
            )
        )

    try:
        await inline_query.answer(
            resultados,
            cache_time=1,
            is_personal=True,
        )
    except Exception as erro:
        print(
            "ERRO NA BUSCA INLINE:",
            repr(erro),
        )


# =========================================================
# SUPORTE (TICKET)
# =========================================================

async def pedir_suporte(
    query,
    context,
):

    context.user_data["aguardando_suporte"] = True
    context.user_data["aguardando_quantidade"] = False
    context.user_data["aguardando_valor"] = False
    context.user_data["aguardando_pesquisa"] = False

    await editar_ou_substituir(
        query,
        context,
        "🆘 *SUPORTE*\n\n"
        "Descreva o seu problema com clareza.\n\n"
        "📌 Lembre-se de enviar:\n"
        "• 📸 Print do erro\n"
        "• 🔑 Login exatamente como recebido\n"
        "• 📅 Data da compra\n\n"
        "Você pode mandar tudo em uma mensagem só "
        "(inclusive com foto). Nossa equipe "
        "responde por aqui mesmo, em até 24-48h.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ Cancelar",
                        callback_data="voltar_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


async def processar_suporte(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.user_data.get("aguardando_suporte"):
        return False

    if not update.message:
        return True

    usuario = update.effective_user

    if not usuario:
        return True

    context.user_data["aguardando_suporte"] = False

    nome = usuario.first_name or "cliente"
    username_texto = (
        f"@{usuario.username}"
        if usuario.username
        else "Não informado"
    )

    grupo_suporte_id = obter_configuracao(
        "suporte_grupo_id"
    )

    # -----------------------------------------------------
    # CAMINHO 1: GRUPO DE SUPORTE COM TÓPICOS (HELPDESK)
    # -----------------------------------------------------

    if grupo_suporte_id:

        try:
            grupo_id_int = int(grupo_suporte_id)
        except ValueError:
            grupo_id_int = None

        if grupo_id_int:

            topico_id = obter_topico_suporte(
                usuario.id
            )

            try:

                if not topico_id:

                    nome_topico = (
                        f"{nome} "
                        f"(@{usuario.username or 'sem_user'}) "
                        f"#{usuario.id}"
                    )

                    topico = await context.bot.create_forum_topic(
                        chat_id=grupo_id_int,
                        name=nome_topico[:128],
                    )

                    topico_id = (
                        topico.message_thread_id
                    )

                    salvar_topico_suporte(
                        usuario.id,
                        topico_id,
                    )

                    await context.bot.send_message(
                        chat_id=grupo_id_int,
                        message_thread_id=topico_id,
                        text=(
                            "📩 *NOVO TICKET*\n\n"
                            f"👤 Nome: {nome}\n"
                            f"🔗 Username: {username_texto}\n"
                            f"🆔 ID: `{usuario.id}`\n\n"
                            "Responda direto aqui neste "
                            "tópico — a mensagem vai "
                            "pro cliente automaticamente."
                        ),
                        parse_mode="Markdown",
                    )

                await update.message.forward(
                    chat_id=grupo_id_int,
                    message_thread_id=topico_id,
                )

                await update.message.reply_text(
                    "✅ *Mensagem enviada ao suporte!*\n\n"
                    "Nossa equipe vai responder por "
                    "aqui mesmo assim que possível.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "↩️ Voltar ao menu",
                                    callback_data="voltar_menu",
                                )
                            ]
                        ]
                    ),
                    parse_mode="Markdown",
                )

                return True

            except Exception as erro:
                print(
                    "ERRO NO GRUPO DE SUPORTE COM "
                    "TÓPICOS:",
                    repr(erro),
                )
                # Cai pro caminho antigo abaixo.

    # -----------------------------------------------------
    # CAMINHO 2 (FALLBACK): CHAT INDIVIDUAL
    # -----------------------------------------------------

    texto_info = (
        "📩 *NOVO TICKET DE SUPORTE*\n\n"
        f"👤 Nome: {nome}\n"
        f"🔗 Username: {username_texto}\n"
        f"🆔 ID do cliente: `{usuario.id}`\n\n"
        "↩️ Para responder, dê *Reply* nesta "
        "mensagem com a resposta (texto ou foto)."
    )

    destino = (
        obter_configuracao("suporte_chat_id")
        or ADMIN_ID
    )

    try:
        await update.message.forward(
            chat_id=destino
        )

        await context.bot.send_message(
            chat_id=destino,
            text=texto_info,
            parse_mode="Markdown",
        )

    except Exception as erro:
        print(
            "ERRO AO ENCAMINHAR TICKET DE SUPORTE:",
            repr(erro),
        )

        await update.message.reply_text(
            "❌ Não foi possível enviar sua "
            "mensagem ao suporte agora. Tente "
            "novamente em instantes."
        )

        return True

    await update.message.reply_text(
        "✅ *Mensagem enviada ao suporte!*\n\n"
        "Nossa equipe vai responder por aqui "
        "mesmo assim que possível.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "↩️ Voltar ao menu",
                        callback_data="voltar_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )

    return True


# =========================================================
# COMANDO /pix (ATALHO PRA ADICIONAR SALDO)
# =========================================================

async def comando_pix(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    if not usuario or not update.message:
        return

    if modo_manutencao_ativo() and not eh_admin_principal(
        usuario.id
    ):
        await update.message.reply_text(
            TEXTO_MANUTENCAO,
            parse_mode="Markdown",
        )
        return

    context.user_data["aguardando_valor"] = True
    context.user_data["valor_saldo"] = None
    context.user_data["aguardando_quantidade"] = False
    context.user_data["produto_quantidade_id"] = None

    await update.message.reply_text(
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
# COMANDO /id (MOSTRA O ID DO TELEGRAM)
# =========================================================

async def comando_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    if not usuario or not update.message:
        return

    await update.message.reply_text(
        "🆔 *SEU ID DO TELEGRAM*\n\n"
        f"`{usuario.id}`",
        parse_mode="Markdown",
    )


# =========================================================
# COMANDO /grupoid (AJUDA A CONFIGURAR O GRUPO DE SUPORTE)
# =========================================================

async def comando_grupo_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.effective_chat:
        return

    await update.message.reply_text(
        "🆔 *ID deste chat:*\n"
        f"`{update.effective_chat.id}`\n\n"
        "Cole esse número no painel admin, em "
        "\"🗂️ GRUPO DE SUPORTE (TÓPICOS)\".",
        parse_mode="Markdown",
    )


# =========================================================
# RESPONDER SUPORTE DE DENTRO DO GRUPO (TÓPICOS)
# =========================================================

async def responder_suporte_topico(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    mensagem = update.message

    if not mensagem:
        return

    grupo_suporte_id = obter_configuracao(
        "suporte_grupo_id"
    )

    if not grupo_suporte_id:
        return

    try:
        if int(grupo_suporte_id) != int(
            mensagem.chat_id
        ):
            return
    except (ValueError, TypeError):
        return

    topico_id = mensagem.message_thread_id

    if not topico_id:
        return

    cliente_id = obter_usuario_por_topico(
        topico_id
    )

    if not cliente_id:
        return

    try:
        if mensagem.text:

            await context.bot.send_message(
                chat_id=cliente_id,
                text=(
                    "💬 *Resposta do suporte:*\n\n"
                    f"{mensagem.text}"
                ),
                parse_mode="Markdown",
            )

        elif mensagem.photo:

            legenda = mensagem.caption or ""

            await context.bot.send_photo(
                chat_id=cliente_id,
                photo=mensagem.photo[-1].file_id,
                caption=(
                    "💬 *Resposta do suporte:*\n\n"
                    f"{legenda}"
                ),
                parse_mode="Markdown",
            )

        else:
            return

    except Exception as erro:
        print(
            "ERRO AO RESPONDER TICKET (TÓPICO):",
            repr(erro),
        )

        try:
            await mensagem.reply_text(
                "❌ Não foi possível entregar a "
                "resposta (o cliente pode ter "
                "bloqueado o bot)."
            )
        except Exception:
            pass


async def responder_suporte_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    if not usuario:
        return

    destino_configurado = obter_configuracao(
        "suporte_chat_id"
    )

    contas_autorizadas = {
        str(ADMIN_ID)
    }

    if destino_configurado:
        contas_autorizadas.add(
            str(destino_configurado)
        )

    if str(usuario.id) not in contas_autorizadas:
        return

    mensagem = update.message

    if not mensagem or not mensagem.reply_to_message:
        return

    texto_original = (
        mensagem.reply_to_message.text or ""
    )

    correspondencia = re.search(
        r"ID do cliente:\s*`?(\d+)`?",
        texto_original,
    )

    if not correspondencia:
        return

    cliente_id = int(
        correspondencia.group(1)
    )

    try:
        if mensagem.text:

            await context.bot.send_message(
                chat_id=cliente_id,
                text=(
                    "💬 *Resposta do suporte:*\n\n"
                    f"{mensagem.text}"
                ),
                parse_mode="Markdown",
            )

        elif mensagem.photo:

            legenda = mensagem.caption or ""

            await context.bot.send_photo(
                chat_id=cliente_id,
                photo=mensagem.photo[-1].file_id,
                caption=(
                    "💬 *Resposta do suporte:*\n\n"
                    f"{legenda}"
                ),
                parse_mode="Markdown",
            )

        else:
            return

        await mensagem.reply_text(
            "✅ Resposta enviada ao cliente."
        )

    except Exception as erro:
        print(
            "ERRO AO RESPONDER TICKET DE SUPORTE:",
            repr(erro),
        )

        await mensagem.reply_text(
            "❌ Não foi possível enviar a resposta "
            "ao cliente (ele pode ter bloqueado "
            "o bot)."
        )


# =========================================================
# RENOVAR CONTA (HISTÓRICO + RENOVAÇÃO)
# =========================================================

DIAS_GRACA_RENOVACAO = 7


async def mostrar_historico_renovacao(
    query,
    context,
    usuario_id,
):

    contas = listar_contas_usuario(
        usuario_id
    )

    if not contas:
        await editar_ou_substituir(
            query,
            context,
            "♻️ *RENOVAR CONTA*\n\n"
            "Você ainda não tem contas compradas.\n\n"
            "Aparecem aqui as contas que você "
            "comprou, desde a compra até um "
            "pouco depois do vencimento.",
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

    agora = datetime.now()

    texto = (
        "♻️ *RENOVAR CONTA*\n\n"
        "Histórico das suas contas:\n\n"
    )

    botoes = []

    for conta in contas[:20]:

        (
            login_id,
            produto_id,
            nome_produto,
            vendido_em,
            duracao_dias,
        ) = conta

        try:
            data_compra = datetime.strptime(
                vendido_em[:19],
                "%Y-%m-%d %H:%M:%S",
            )
        except (ValueError, TypeError):
            data_compra = None

        data_texto = (
            data_compra.strftime("%d/%m/%Y")
            if data_compra
            else "Data desconhecida"
        )

        if not duracao_dias or not data_compra:

            texto += (
                f"📦 *{nome_produto}*\n"
                f"🗓️ Comprado em: {data_texto}\n"
                "ℹ️ Duração não cadastrada\n\n"
            )
            continue

        vencimento = data_compra + timedelta(
            days=duracao_dias
        )

        dias_restantes = (
            vencimento - agora
        ).days

        if dias_restantes >= 0:

            status = (
                f"✅ Ativo (vence em "
                f"{dias_restantes}d)"
            )

            elegivel = True

        else:

            dias_vencido = abs(
                dias_restantes
            )

            if dias_vencido <= DIAS_GRACA_RENOVACAO:

                status = (
                    f"🔴 Vencido há "
                    f"{dias_vencido}d"
                )

                elegivel = True

            else:

                status = (
                    f"⚫ Vencido há "
                    f"{dias_vencido}d"
                )

                elegivel = False

        texto += (
            f"📦 *{nome_produto}*\n"
            f"🗓️ Comprado em: {data_texto}\n"
            f"{status}\n\n"
        )

        if elegivel:

            botoes.append(
                [
                    InlineKeyboardButton(
                        f"🔁 Renovar {nome_produto[:30]}",
                        callback_data=(
                            f"renovar_login_{login_id}"
                        ),
                    )
                ]
            )

    if len(contas) > 20:
        texto += (
            "_Mostrando as 20 compras mais "
            "recentes._\n\n"
        )

    botoes.append(
        [
            InlineKeyboardButton(
                "↩️ Voltar ao menu",
                callback_data="voltar_menu",
            )
        ]
    )

    await editar_ou_substituir(
        query,
        context,
        texto,
        reply_markup=InlineKeyboardMarkup(
            botoes
        ),
        parse_mode="Markdown",
    )


async def renovar_conta(
    query,
    context,
    usuario_id,
    login_id,
):

    login = consultar_login(
        login_id
    )

    if not login:
        await query.answer(
            "❌ Conta não encontrada.",
            show_alert=True,
        )
        return

    (
        _,
        produto_id,
        _dados,
        _status,
        login_usuario_id,
        _pedido_id,
        _vendido_em,
    ) = login

    if int(login_usuario_id or 0) != int(
        usuario_id
    ):
        await query.answer(
            "❌ Essa conta não é sua.",
            show_alert=True,
        )
        return

    await comprar_produto(
        query,
        context,
        produto_id,
        usuario_id,
        1,
    )


# =========================================================
# JOGOS NA TV
# =========================================================

async def mostrar_jogos_tv(
    query,
    context,
):

    jogos_texto = obter_configuracao(
        "jogos_tv_texto"
    )

    if not jogos_texto:
        texto = (
            "⚽ *JOGOS NA TV*\n\n"
            "❌ Nenhum jogo cadastrado no momento."
        )
    else:
        texto = (
            "⚽ *JOGOS NA TV*\n\n"
            f"{jogos_texto}"
        )

    await editar_ou_substituir(
        query,
        context,
        texto,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "↩️ Voltar ao menu",
                        callback_data="voltar_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# PESQUISAR SERVIÇO
# =========================================================

async def pedir_pesquisa_servico(
    query,
    context,
):

    context.user_data["aguardando_pesquisa"] = True
    context.user_data["aguardando_quantidade"] = False
    context.user_data["aguardando_valor"] = False
    context.user_data["produto_quantidade_id"] = None

    await editar_ou_substituir(
        query,
        context,
        "🔎 *PESQUISAR SERVIÇO*\n\n"
        "Digite o nome do produto que você "
        "está procurando.\n\n"
        "Exemplo:\n"
        "`netflix`\n"
        "`disney`",
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


async def processar_pesquisa_servico(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    termo = (update.message.text or "").strip()

    if not termo:

        await update.message.reply_text(
            "❌ Digite um termo para pesquisar."
        )
        return

    context.user_data["aguardando_pesquisa"] = False

    produtos = buscar_produtos_por_nome(
        termo
    )

    if not produtos:

        await update.message.reply_text(
            "🔎 *PESQUISAR SERVIÇO*\n\n"
            f"❌ Nenhum resultado para: "
            f"\"{termo}\"",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔎 Pesquisar de novo",
                            callback_data="pesquisar_servico",
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
            ),
            parse_mode="Markdown",
        )
        return

    botoes = []

    for produto in produtos:

        produto_id = produto[0]
        nome = produto[1]
        preco = float(produto[3])

        botoes.append(
            [
                InlineKeyboardButton(
                    f"{nome} R${preco:.2f}",
                    callback_data=(
                        f"produto_{produto_id}"
                    ),
                )
            ]
        )

    botoes.append(
        [
            InlineKeyboardButton(
                "🔎 Pesquisar de novo",
                callback_data="pesquisar_servico",
            )
        ]
    )

    botoes.append(
        [
            InlineKeyboardButton(
                "↩️ Voltar ao menu",
                callback_data="voltar_menu",
            )
        ]
    )

    await update.message.reply_text(
        "🔎 *RESULTADO DA PESQUISA*\n\n"
        f"Encontrado(s) {len(produtos)} "
        f"resultado(s) para \"{termo}\":",
        reply_markup=InlineKeyboardMarkup(
            botoes
        ),
        parse_mode="Markdown",
    )


# =========================================================
# CARRINHO
# =========================================================

async def mostrar_carrinho(
    query,
    context,
    usuario_id,
):

    itens = listar_itens_carrinho(
        usuario_id
    )

    if not itens:

        await editar_ou_substituir(
            query,
            context,
            "🛍️ *CARRINHO*\n\n"
            "Seu carrinho está vazio.\n\n"
            "Adicione produtos pelo catálogo.",
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

    texto = (
        "🛍️ *CARRINHO*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    total = 0.0
    botoes = []

    for item in itens:

        item_id, produto_id, nome, preco, quantidade = item

        preco = float(preco)
        quantidade = int(quantidade)
        subtotal = preco * quantidade
        total += subtotal

        texto += (
            f"📦 *{nome}*\n"
            f"   {quantidade}x R$ {preco:.2f} = "
            f"R$ {subtotal:.2f}\n\n"
        )

        botoes.append(
            [
                InlineKeyboardButton(
                    f"🗑️ Remover {nome[:25]}",
                    callback_data=(
                        f"remover_carrinho_{item_id}"
                    ),
                )
            ]
        )

    saldo = float(
        consultar_saldo(usuario_id) or 0
    )

    texto += (
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 *Total:* R$ {total:.2f}\n"
        f"💳 *Seu saldo:* R$ {saldo:.2f}"
    )

    botoes.append(
        [
            InlineKeyboardButton(
                "✅ FINALIZAR COMPRA",
                callback_data="finalizar_carrinho",
            )
        ]
    )

    botoes.append(
        [
            InlineKeyboardButton(
                "🗑️ ESVAZIAR CARRINHO",
                callback_data="esvaziar_carrinho",
            )
        ]
    )

    botoes.append(
        [
            InlineKeyboardButton(
                "🛒 Ver catálogo",
                callback_data="catalogo",
            )
        ]
    )

    botoes.append(
        [
            InlineKeyboardButton(
                "↩️ Voltar ao menu",
                callback_data="voltar_menu",
            )
        ]
    )

    await editar_ou_substituir(
        query,
        context,
        texto,
        reply_markup=InlineKeyboardMarkup(
            botoes
        ),
        parse_mode="Markdown",
    )


async def finalizar_compra_carrinho(
    query,
    context,
    usuario_id,
):

    itens = listar_itens_carrinho(
        usuario_id
    )

    if not itens:

        await query.answer(
            "🛍️ Seu carrinho está vazio.",
            show_alert=True,
        )
        return

    # ---------------------------------------------------
    # Confere estoque real de cada item antes de cobrar.
    # ---------------------------------------------------

    itens_insuficientes = []
    total = 0.0

    for item in itens:

        _, produto_id, nome, preco, quantidade = item

        preco = float(preco)
        quantidade = int(quantidade)

        estoque_real = consultar_estoque_logins(
            produto_id
        )

        if estoque_real < quantidade:

            itens_insuficientes.append(
                f"📦 {nome} "
                f"(disponível: {estoque_real}, "
                f"pedido: {quantidade})"
            )

        total += preco * quantidade

    if itens_insuficientes:

        texto_erro = (
            "❌ *ESTOQUE INSUFICIENTE*\n\n"
            "Os itens abaixo não têm estoque "
            "suficiente:\n\n"
            + "\n".join(itens_insuficientes)
            + "\n\nAjuste as quantidades no carrinho "
            "e tente novamente."
        )

        await editar_ou_substituir(
            query,
            context,
            texto_erro,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🛍️ Voltar ao carrinho",
                            callback_data="carrinho",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )
        return

    saldo = float(
        consultar_saldo(usuario_id) or 0
    )

    if saldo < total:

        await editar_ou_substituir(
            query,
            context,
            "❌ *SALDO INSUFICIENTE*\n\n"
            f"💰 *Total do carrinho:* R$ {total:.2f}\n"
            f"💳 *Seu saldo:* R$ {saldo:.2f}\n"
            f"💵 *Faltam:* R$ {total - saldo:.2f}",
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
                            "🛍️ Voltar ao carrinho",
                            callback_data="carrinho",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
        )
        return

    sucesso = retirar_saldo(
        usuario_id,
        total,
    )

    if not sucesso:

        await query.answer(
            "❌ Não foi possível processar o pagamento.",
            show_alert=True,
        )
        return

    entregas = []
    falhou = False

    for item in itens:

        _, produto_id, nome, preco, quantidade = item

        preco = float(preco)
        quantidade = int(quantidade)
        valor_item = preco * quantidade

        pedido_id = None

        try:
            conn = conectar()
            cursor = conn.cursor()

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
                    valor_item,
                ),
            )

            pedido_id = cursor.lastrowid
            conn.commit()
            conn.close()

        except Exception as erro:
            print(
                "ERRO AO REGISTRAR PEDIDO DO CARRINHO:",
                repr(erro),
            )
            falhou = True
            break

        contas_produto = []

        for _ in range(quantidade):

            login = retirar_login_disponivel(
                produto_id,
                usuario_id,
                pedido_id,
            )

            if not login:
                falhou = True
                break

            contas_produto.append(
                login["dados"]
            )

        if falhou:
            break

        entregas.append(
            (nome, contas_produto)
        )

        await verificar_estoque_baixo(
            context.bot,
            produto_id,
            nome,
        )

    if falhou:

        adicionar_saldo(
            usuario_id,
            total,
        )

        await editar_ou_substituir(
            query,
            context,
            "❌ *COMPRA NÃO CONCLUÍDA*\n\n"
            "O estoque de algum item acabou "
            "durante o processamento.\n\n"
            "💰 O valor foi devolvido ao seu saldo.\n"
            "Confira o carrinho e tente novamente.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🛍️ Ver carrinho",
                            callback_data="carrinho",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )
        return

    limpar_carrinho(
        usuario_id
    )

    novo_saldo = float(
        consultar_saldo(usuario_id) or 0
    )

    texto = (
        "✅ *COMPRA REALIZADA!*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    for nome, contas in entregas:

        texto += f"🛍️ *{nome}*\n"

        for indice, dados in enumerate(
            contas, start=1
        ):
            texto += (
                f"🔐 *Conta {indice}*\n"
                f"```\n{dados}\n```\n"
            )

        texto += "\n"

    texto += (
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 *Total pago:* R$ {total:.2f}\n"
        f"💳 *Saldo restante:* R$ {novo_saldo:.2f}\n\n"
        "⚡ Entrega realizada automaticamente."
    )

    await editar_ou_substituir(
        query,
        context,
        texto,
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


# =========================================================
# EDITAR TEXTO (COM SUPORTE A MENSAGENS QUE SÃO FOTO/GIF)
# =========================================================
#
# query.edit_message_text falha quando a mensagem original
# é uma foto ou GIF (como o catálogo com imagem configurada
# pelo admin). Nesses casos, apagamos a mensagem e mandamos
# uma nova mensagem de texto no lugar.

async def editar_ou_substituir(
    query,
    context,
    texto,
    reply_markup=None,
    parse_mode="Markdown",
):

    mensagem = query.message

    e_midia = bool(
        mensagem
        and (
            mensagem.photo
            or mensagem.animation
        )
    )

    if e_midia:

        try:
            await mensagem.delete()
        except Exception:
            pass

        await context.bot.send_message(
            chat_id=mensagem.chat_id,
            text=texto,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )

    else:

        await query.edit_message_text(
            texto,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
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

    if (
        modo_manutencao_ativo()
        and not eh_admin_principal(usuario_id)
        and not acao.startswith("admin_")
    ):
        await query.answer(
            "🛠️ Bot em manutenção. Tente "
            "novamente em breve.",
            show_alert=True,
        )
        return

    # =====================================================
    # RELATÓRIO DE VENDAS SOB DEMANDA (INTERCEPTADO ANTES
    # DE DELEGAR PRO PAINEL ADMIN, POIS A FUNÇÃO VIVE AQUI)
    # =====================================================

    if acao == "admin_relatorio_vendas":

        if not eh_admin_principal(usuario_id):
            await query.answer(
                "❌ Acesso negado.",
                show_alert=True,
            )
            return

        await query.answer(
            "📊 Gerando relatório..."
        )

        await enviar_relatorio_vendas(
            context.bot
        )

        return

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
            context,
            transacao_id,
        )
        return

    # =====================================================
    # ESTOQUE DE LOGINS (PÚBLICO)
    # =====================================================

    if acao == "estoque_logins":
        await mostrar_estoque_logins(
            query,
            context,
        )
        return

    # =====================================================
    # PESQUISAR SERVIÇO
    # =====================================================

    if acao == "pesquisar_servico":
        await pedir_pesquisa_servico(
            query,
            context,
        )
        return

    # =====================================================
    # CARRINHO
    # =====================================================

    if acao == "carrinho":
        await mostrar_carrinho(
            query,
            context,
            usuario_id,
        )
        return

    if acao.startswith("add_carrinho_"):

        try:
            produto_id = int(
                acao.replace(
                    "add_carrinho_",
                    "",
                    1,
                )
            )
        except ValueError:
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

        estoque_real = consultar_estoque_logins(
            produto_id
        )

        if estoque_real <= 0:
            await query.answer(
                "📦 Produto sem contas disponíveis.",
                show_alert=True,
            )
            return

        adicionar_item_carrinho(
            usuario_id,
            produto_id,
            1,
        )

        await query.answer(
            "✅ Adicionado ao carrinho!",
            show_alert=True,
        )
        return

    if acao.startswith("remover_carrinho_"):

        try:
            item_id = int(
                acao.replace(
                    "remover_carrinho_",
                    "",
                    1,
                )
            )
        except ValueError:
            await query.answer(
                "❌ Item inválido.",
                show_alert=True,
            )
            return

        remover_item_carrinho(
            item_id,
            usuario_id,
        )

        await query.answer(
            "🗑️ Item removido."
        )

        await mostrar_carrinho(
            query,
            context,
            usuario_id,
        )
        return

    if acao == "esvaziar_carrinho":

        limpar_carrinho(
            usuario_id
        )

        await query.answer(
            "🗑️ Carrinho esvaziado."
        )

        await mostrar_carrinho(
            query,
            context,
            usuario_id,
        )
        return

    if acao == "finalizar_carrinho":

        await finalizar_compra_carrinho(
            query,
            context,
            usuario_id,
        )
        return

    # =====================================================
    # CATÁLOGO (CATEGORIAS)
    # =====================================================

    if acao == "catalogo":
        context.user_data["aguardando_quantidade"] = False
        context.user_data["aguardando_valor"] = False

        texto_catalogo = (
            texto_selecionar_categoria()
        )

        imagem_id = obter_configuracao(
            "imagem_catalogo_id"
        )
        imagem_tipo = obter_configuracao(
            "imagem_catalogo_tipo"
        )

        if imagem_id:

            try:
                await query.message.delete()
            except Exception:
                pass

            try:
                if imagem_tipo == "animation":
                    await context.bot.send_animation(
                        chat_id=usuario_id,
                        animation=imagem_id,
                        caption=texto_catalogo,
                        reply_markup=menu_categorias(),
                        parse_mode="Markdown",
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=usuario_id,
                        photo=imagem_id,
                        caption=texto_catalogo,
                        reply_markup=menu_categorias(),
                        parse_mode="Markdown",
                    )
                return
            except Exception as erro:
                print(
                    "ERRO AO ENVIAR IMAGEM DO CATÁLOGO:",
                    repr(erro),
                )
                await context.bot.send_message(
                    chat_id=usuario_id,
                    text=texto_catalogo,
                    reply_markup=menu_categorias(),
                    parse_mode="Markdown",
                )
                return

        await editar_ou_substituir(
            query,
            context,
            texto_catalogo,
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

        await editar_ou_substituir(
            query,
            context,
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

            await editar_ou_substituir(
                query,
                context,
                "📦 *ESGOTADO NO MOMENTO*\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🛍️ *Serviço:* {nome}\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 {descricao or 'Sem descrição'}\n\n"
                "Esse produto está sem contas "
                "disponíveis agora. Quer que eu "
                "te avise assim que voltar ao "
                "estoque?",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔔 Avisar quando disponível",
                                callback_data=(
                                    f"avisar_reposicao_{produto_id}"
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
                ),
                parse_mode="Markdown",
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
                    "➕ ADICIONAR AO CARRINHO",
                    callback_data=f"add_carrinho_{produto_id}",
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

        await editar_ou_substituir(
            query,
            context,
            texto,
            reply_markup=InlineKeyboardMarkup(
                botoes_compra
            ),
            parse_mode="Markdown",
        )
        return

    # =====================================================
    # AVISAR QUANDO REPOSTO
    # =====================================================

    if acao.startswith("avisar_reposicao_"):

        try:
            produto_id = int(
                acao.replace(
                    "avisar_reposicao_",
                    "",
                    1,
                )
            )
        except ValueError:
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

        registrar_aviso_reposicao(
            usuario_id,
            produto_id,
        )

        await query.answer(
            "🔔 Combinado! Você vai receber uma "
            "mensagem assim que esse produto "
            "voltar ao estoque.",
            show_alert=True,
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
            context,
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
            context,
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

        await editar_ou_substituir(
            query,
            context,
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

        try:
            await query.message.delete()
        except Exception:
            pass

        await enviar_menu_principal(
            query.message.chat_id,
            context,
            "🛒 *PLAYER STORE*\n\n"
            "Escolha uma opção abaixo:",
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

        await editar_ou_substituir(
            query,
            context,
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

        await editar_ou_substituir(
            query,
            context,
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
    # TERMOS DE USO
    # =====================================================

    if acao == "termos":
        await editar_ou_substituir(
            query,
            context,
            "📜 *TERMOS DE USO*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ Ao confirmar uma compra, você concorda "
            "com todas as regras abaixo.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🕐 *HORÁRIO DE ATENDIMENTO*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Nosso suporte funciona, em geral, das "
            "11h às 21h.\n"
            "Aos finais de semana e feriados o "
            "atendimento pode estar indisponível.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🆘 *COMO SOLICITAR SUPORTE*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Clique em SUPORTE no menu do bot\n"
            "2️⃣ Descreva o seu problema com clareza\n"
            "3️⃣ Aguarde um administrador responder\n\n"
            "📌 É obrigatório enviar:\n"
            "• 📸 Print do erro\n"
            "• 🔑 Login exatamente como recebido\n"
            "• 📅 Data da compra\n\n"
            "Sem esses dados não é possível dar "
            "suporte.\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "❗ *REGRAS IMPORTANTES*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "• ❌ Não altere o e-mail das contas — "
            "perde o suporte\n"
            "• 💰 Reembolso só em saldo do bot, "
            "nunca em Pix\n"
            "• 🤝 Respeito é essencial — ofensas "
            "levam a banimento e perda do saldo\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⏳ *PRAZOS*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "• Retorno em até 24 a 48 horas\n"
            "• Se passar disso, você recebe em "
            "saldo o valor proporcional aos dias "
            "pendentes\n"
            "• Problemas com login online: "
            "resolvidos na hora\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "✅ Ao prosseguir, você confirma que "
            "leu e aceita.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "↩️ Voltar ao menu",
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
        await editar_ou_substituir(
            query,
            context,
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
    # SUPORTE
    # =====================================================

    if acao == "suporte":
        await pedir_suporte(
            query,
            context,
        )
        return

    # =====================================================
    # RENOVAR CONTA
    # =====================================================

    if acao == "renovar_conta":
        await mostrar_historico_renovacao(
            query,
            context,
            usuario_id,
        )
        return

    if acao.startswith("renovar_login_"):

        try:
            login_id = int(
                acao.replace(
                    "renovar_login_",
                    "",
                    1,
                )
            )
        except ValueError:
            await query.answer(
                "❌ Conta inválida.",
                show_alert=True,
            )
            return

        await renovar_conta(
            query,
            context,
            usuario_id,
            login_id,
        )
        return

    # =====================================================
    # JOGOS NA TV
    # =====================================================

    if acao == "jogos_tv":
        await mostrar_jogos_tv(
            query,
            context,
        )
        return

    # =====================================================
    # TERMOS DE USO (bloco duplicado removido)
    # =====================================================

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
        CommandHandler(
            "grupoid",
            comando_grupo_id,
        )
    )

    application.add_handler(
        CommandHandler(
            "pix",
            comando_pix,
        )
    )

    application.add_handler(
        CommandHandler(
            "id",
            comando_id,
        )
    )

    application.add_handler(
        InlineQueryHandler(
            pesquisa_inline
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            botoes
        )
    )

    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & (filters.TEXT | filters.PHOTO),
            responder_suporte_topico,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & filters.REPLY
            & (filters.TEXT | filters.PHOTO),
            responder_suporte_admin,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.ANIMATION,
            processar_midia_generico,
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
