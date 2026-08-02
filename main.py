import requests
from datetime import date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import (
    BOT_TOKEN,
    ASAAS_API_KEY,
    verificar_configuracao,
)

from database import (
    criar_tabelas,
    criar_usuario,
    consultar_saldo,
    conectar,
    retirar_saldo,
)

from menu import menu_principal
from catalogo import menu_catalogo, buscar_produto


GRUPO_CLIENTES = "https://t.me/PLAYERSTORYREFERENCIA"


# ============================================================
# ASAAS
# ============================================================

ASAAS_URL = "https://api.asaas.com/v3"


def criar_cobranca_pix(valor, usuario_id):
    """
    Cria uma cobrança PIX no Asaas.
    """

    headers = {
        "access_token": ASAAS_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "PLAYER-STORE-BOT"
    }

    dados = {
        "customer": None,
        "billingType": "PIX",
        "value": float(valor),
        "dueDate": date.today().isoformat(),
        "description": f"Adição de saldo - Usuario {usuario_id}",
        "externalReference": str(usuario_id),
    }

    # O Asaas exige um cliente para a cobrança.
    # Por isso, primeiro procuramos um cliente existente.
    resposta_clientes = requests.get(
        f"{ASAAS_URL}/customers",
        headers=headers,
        params={
            "externalReference": str(usuario_id),
            "limit": 1
        },
        timeout=30
    )

    if resposta_clientes.status_code != 200:
        return None, "Não foi possível consultar o cliente no Asaas."

    clientes = resposta_clientes.json().get("data", [])

    if clientes:
        customer_id = clientes[0]["id"]
    else:
        # Cria o cliente no Asaas
        cliente_data = {
            "name": f"Cliente {usuario_id}",
            "externalReference": str(usuario_id)
        }

        resposta_cliente = requests.post(
            f"{ASAAS_URL}/customers",
            headers=headers,
            json=cliente_data,
            timeout=30
        )

        if resposta_cliente.status_code not in (200, 201):
            return None, "Não foi possível criar o cliente no Asaas."

        customer_id = resposta_cliente.json()["id"]

    dados["customer"] = customer_id

    resposta = requests.post(
        f"{ASAAS_URL}/payments",
        headers=headers,
        json=dados,
        timeout=30
    )

    if resposta.status_code not in (200, 201):
        try:
            erro = resposta.json()
        except Exception:
            erro = resposta.text

        print("ERRO ASAAS:", erro)

        return None, "Não foi possível criar a cobrança PIX."

    pagamento = resposta.json()

    payment_id = pagamento.get("id")

    if not payment_id:
        return None, "O Asaas não retornou o ID da cobrança."

    # Busca o QR Code / Pix Copia e Cola
    resposta_pix = requests.get(
        f"{ASAAS_URL}/payments/{payment_id}/pixQrCode",
        headers={
            "access_token": ASAAS_API_KEY,
            "User-Agent": "PLAYER-STORE-BOT"
        },
        timeout=30
    )

    if resposta_pix.status_code != 200:
        print("ERRO PIX ASAAS:", resposta_pix.text)

        return None, "A cobrança foi criada, mas não foi possível obter o PIX."

    dados_pix = resposta_pix.json()

    return {
        "payment_id": payment_id,
        "payload": dados_pix.get("payload"),
        "encoded_image": dados_pix.get("encodedImage"),
        "expiration_date": dados_pix.get("expirationDate"),
    }, None


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


# ============================================================
# COMPRA
# ============================================================

async def comprar_produto(query, produto_id, usuario_id):
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

    sucesso = retirar_saldo(usuario_id, preco)

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
        (usuario_id, produto_id, quantidade, valor, status)
        VALUES (?, ?, 1, ?, 'pago')
        """,
        (usuario_id, produto_id, preco)
    )

    conn.commit()
    conn.close()

    novo_saldo = consultar_saldo(usuario_id)

    await query.edit_message_text(
        f"✅ *Compra realizada!*\n\n"
        f"🛒 Produto: {nome}\n"
        f"💰 Valor: R$ {preco:.2f}\n"
        f"💳 Saldo restante: R$ {novo_saldo:.2f}\n\n"
        "📦 Seu pedido foi registrado.",
        reply_markup=menu_principal(),
        parse_mode="Markdown"
    )


# ============================================================
# BOTÕES
# ============================================================

async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    usuario_id = query.from_user.id
    acao = query.data

    # --------------------------------------------------------
    # CATÁLOGO
    # --------------------------------------------------------

    if acao == "catalogo":

        await query.edit_message_text(
            "🛒 *LOGINS | CONTAS PREMIUM*\n\n"
            "Escolha um produto:",
            reply_markup=menu_catalogo(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # PRODUTO
    # --------------------------------------------------------

    elif acao.startswith("produto_"):

        produto_id = int(acao.split("_")[1])
        produto = buscar_produto(produto_id)

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
            reply_markup=InlineKeyboardMarkup(botoes_compra),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # COMPRAR
    # --------------------------------------------------------

    elif acao.startswith("comprar_"):

        produto_id = int(acao.split("_")[1])

        await comprar_produto(
            query,
            produto_id,
            usuario_id
        )

    # --------------------------------------------------------
    # SALDO / PIX
    # --------------------------------------------------------

    elif acao == "saldo":

        botoes_saldo = [
            [
                InlineKeyboardButton(
                    "💰 R$ 10,00",
                    callback_data="pix_10"
                ),
                InlineKeyboardButton(
                    "💰 R$ 20,00",
                    callback_data="pix_20"
                )
            ],
            [
                InlineKeyboardButton(
                    "💰 R$ 50,00",
                    callback_data="pix_50"
                ),
                InlineKeyboardButton(
                    "💰 R$ 100,00",
                    callback_data="pix_100"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="voltar_menu"
                )
            ]
        ]

        saldo = consultar_saldo(usuario_id)

        await query.edit_message_text(
            f"💵 *ADICIONAR SALDO*\n\n"
            f"💰 Seu saldo atual: R$ {saldo:.2f}\n\n"
            "Escolha o valor que deseja adicionar:",
            reply_markup=InlineKeyboardMarkup(botoes_saldo),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # GERAR PIX
    # --------------------------------------------------------

    elif acao.startswith("pix_"):

        valor = float(acao.split("_")[1])

        await query.edit_message_text(
            "⏳ *Gerando sua cobrança PIX...*\n\n"
            "Aguarde alguns segundos.",
            parse_mode="Markdown"
        )

        cobranca, erro = criar_cobranca_pix(
            valor,
            usuario_id
        )

        if erro:

            await query.edit_message_text(
                f"❌ *Erro ao gerar PIX*\n\n"
                f"{erro}",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "⬅️ Voltar",
                            callback_data="saldo"
                        )
                    ]
                ]),
                parse_mode="Markdown"
            )

            return

        payload = cobranca.get("payload")

        if not payload:

            await query.edit_message_text(
                "❌ O Asaas não retornou o código PIX.",
                reply_markup=menu_principal()
            )

            return

        botoes_pix = [
            [
                InlineKeyboardButton(
                    "🔄 Verificar pagamento",
                    callback_data=f"verificar_{cobranca['payment_id']}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="saldo"
                )
            ]
        ]

        await query.edit_message_text(
            f"💳 *PAGAMENTO PIX*\n\n"
            f"💰 Valor: R$ {valor:.2f}\n\n"
            "📲 Copie o código PIX abaixo e pague pelo aplicativo do seu banco:\n\n"
            f"`{payload}`\n\n"
            "⏳ Depois de pagar, toque em:\n"
            "🔄 *Verificar pagamento*",
            reply_markup=InlineKeyboardMarkup(botoes_pix),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # VERIFICAR PAGAMENTO
    # --------------------------------------------------------

    elif acao.startswith("verificar_"):

        payment_id = acao.split("_", 1)[1]

        headers = {
            "access_token": ASAAS_API_KEY,
            "User-Agent": "PLAYER-STORE-BOT"
        }

        resposta = requests.get(
            f"{ASAAS_URL}/payments/{payment_id}",
            headers=headers,
            timeout=30
        )

        if resposta.status_code != 200:

            await query.answer(
                "❌ Não foi possível consultar o pagamento.",
                show_alert=True
            )

            return

        pagamento = resposta.json()

        status = pagamento.get("status")

        print(
            f"Pagamento {payment_id} - "
            f"Status: {status}"
        )

        if status in ("RECEIVED", "CONFIRMED"):

            # IMPORTANTE:
            # Nesta primeira versão ainda não vamos adicionar
            # automaticamente o saldo para evitar duplicidade.
            # Isso será feito na próxima etapa com registro
            # da cobrança no banco.

            await query.edit_message_text(
                "✅ *PAGAMENTO IDENTIFICADO!*\n\n"
                "O Asaas confirmou o pagamento.\n\n"
                "🔄 A liberação automática do saldo será "
                "ativada no próximo passo.",
                reply_markup=menu_principal(),
                parse_mode="Markdown"
            )

        else:

            await query.answer(
                f"⏳ Pagamento ainda não confirmado.\n\n"
                f"Status: {status}",
                show_alert=True
            )

    # --------------------------------------------------------
    # PERFIL
    # --------------------------------------------------------

    elif acao == "perfil":

        saldo = consultar_saldo(usuario_id)

        await query.edit_message_text(
            f"👤 *SEU PERFIL*\n\n"
            f"🆔 ID: `{usuario_id}`\n"
            f"💰 Saldo: R$ {saldo:.2f}",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # VOLTAR
    # --------------------------------------------------------

    elif acao == "voltar_menu":

        await query.edit_message_text(
            "🏠 *MENU PRINCIPAL*\n\n"
            "Escolha uma opção:",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # CARRINHO
    # --------------------------------------------------------

    elif acao == "carrinho":

        await query.edit_message_text(
            "🛍️ *CARRINHO*\n\n"
            "Seu carrinho está vazio.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # PESQUISAR
    # --------------------------------------------------------

    elif acao == "pesquisar":

        await query.edit_message_text(
            "🔎 *PESQUISAR SERVIÇO*\n\n"
            "Sistema de pesquisa em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # ESTOQUE
    # --------------------------------------------------------

    elif acao == "estoque":

        await query.edit_message_text(
            "📦 *ESTOQUE DE LOGINS*\n\n"
            "Consulte os produtos disponíveis no catálogo.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # MAC
    # --------------------------------------------------------

    elif acao == "mac":

        await query.edit_message_text(
            "🎮 *ATIVAÇÃO DE MAC*\n\n"
            "Sistema de ativação em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # JOGOS
    # --------------------------------------------------------

    elif acao == "jogos":

        await query.edit_message_text(
            "⚽ *JOGOS NA TV*\n\n"
            "Informações sobre jogos serão adicionadas aqui.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # RENOVAR
    # --------------------------------------------------------

    elif acao == "renovar":

        await query.edit_message_text(
            "♻️ *RENOVAR CONTA*\n\n"
            "Sistema de renovação em desenvolvimento.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # SUPORTE
    # --------------------------------------------------------

    elif acao == "suporte":

        await query.edit_message_text(
            "🆘 *SUPORTE*\n\n"
            "Entre em contato com o suporte.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # TERMOS
    # --------------------------------------------------------

    elif acao == "termos":

        await query.edit_message_text(
            "📜 *TERMOS DE USO*\n\n"
            "Os termos de uso serão adicionados aqui.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # OUTROS BOTS
    # --------------------------------------------------------

    elif acao == "outros_bots":

        await query.edit_message_text(
            "🤖 *OUTROS BOTS*\n\n"
            "Em breve.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # GRUPO
    # --------------------------------------------------------

    elif acao == "grupo":

        await query.edit_message_text(
            "👥 *GRUPO DE CLIENTES*\n\n"
            "Entre no nosso grupo de clientes pelo botão abaixo.",
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

    # --------------------------------------------------------
    # ALUGAR
    # --------------------------------------------------------

    elif acao == "alugar":

        await query.edit_message_text(
            "📣 *ALUGAR ESTE BOT*\n\n"
            "Em breve você poderá solicitar seu próprio bot.",
            reply_markup=menu_principal(),
            parse_mode="Markdown"
        )

    # --------------------------------------------------------
    # SEM ESTOQUE
    # --------------------------------------------------------

    elif acao == "sem_estoque":

        await query.answer(
            "📦 O estoque está vazio.",
            show_alert=True
        )


# ============================================================
# MAIN
# ============================================================

def main():

    verificar_configuracao()
    criar_tabelas()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            botoes
        )
    )

    print("🤖 Bot iniciado!")

    app.run_polling()


if __name__ == "__main__":
    main()
