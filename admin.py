from urllib.parse import urlparse

from log import log_erro

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import ContextTypes

from config import ADMIN_ID

from database import (
    listar_todos_produtos,
    buscar_produto,
    adicionar_login,
    adicionar_varios_logins,
    listar_logins_produto,
    listar_logins_disponiveis,
    consultar_estoque_logins,
    excluir_login,
    alterar_preco,
    cadastrar_produto,
    excluir_produto,
    listar_categorias,
    definir_categoria_produto,
    consultar_categoria_produto,
    definir_configuracao,
    obter_configuracao,
    remover_configuracao,
    definir_imagem_produto,
    definir_duracao_produto,
    obter_duracao_produto,
    listar_interessados_reposicao,
    remover_avisos_reposicao,
    listar_todos_usuarios,
    adicionar_grupo_obrigatorio,
    listar_grupos_obrigatorios,
    remover_grupo_obrigatorio,
    registrar_mensagem_grupo_anuncios,
)


# =========================================================
# NOTIFICAR REPOSIÇÃO DE ESTOQUE
# =========================================================

async def notificar_reposicao_estoque(
    context,
    produto_id,
    nome_produto,
):

    try:

        interessados = listar_interessados_reposicao(
            produto_id
        )

        if not interessados:
            return

        for usuario_id in interessados:

            try:
                await context.bot.send_message(
                    chat_id=usuario_id,
                    text=(
                        "🔔 *DE VOLTA AO ESTOQUE!*\n\n"
                        f"📦 *{nome_produto}* já está "
                        "disponível novamente!"
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🛒 Comprar agora",
                                    callback_data=(
                                        f"produto_{produto_id}"
                                    ),
                                )
                            ]
                        ]
                    ),
                    parse_mode="Markdown",
                )
            except Exception as erro_envio:
                log_erro(
                    "ERRO AO AVISAR REPOSIÇÃO "
                    "(usuário):",
                    repr(erro_envio),
                )

        remover_avisos_reposicao(
            produto_id
        )

    except Exception as erro:
        log_erro(
            "ERRO AO NOTIFICAR REPOSIÇÃO:",
            repr(erro),
        )


# =========================================================
# ANUNCIAR ABASTECIMENTO NO GRUPO PÚBLICO
# =========================================================

async def anunciar_abastecimento_grupo(
    context,
    produto_id,
    nome_produto,
    preco,
    quantidade_adicionada,
):

    try:

        grupo_id = obter_configuracao(
            "grupo_anuncios_id"
        )

        if not grupo_id:
            return

        try:
            grupo_id_int = int(grupo_id)
        except ValueError:
            return

        me = await context.bot.get_me()

        mensagem_enviada = await context.bot.send_message(
            chat_id=grupo_id_int,
            text=(
                "🎉 *ESTOQUE ABASTECIDO!* "
                f"{nome_produto}\n\n"
                f"➕ Entraram "
                f"{quantidade_adicionada} "
                "login(s)\n"
                f"💰 A partir de R$ {preco:.2f}\n"
                "⚡ Corra antes que acabe — "
                "boas compras! 🛒🔥"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🤖 Acessar o bot",
                            url=(
                                f"https://t.me/"
                                f"{me.username}"
                            ),
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        registrar_mensagem_grupo_anuncios(
            grupo_id_int,
            mensagem_enviada.message_id,
        )

    except Exception as erro:
        log_erro(
            "ERRO AO ANUNCIAR ABASTECIMENTO:",
            repr(erro),
        )


# =========================================================
# VALIDAR URL DE IMAGEM
# =========================================================

EXTENSOES_IMAGEM_VALIDAS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
)


def url_parece_imagem(url):
    """
    Verifica se a URL aponta direto para um arquivo de
    imagem (termina em .jpg/.jpeg/.png/.webp/.gif),
    ignorando parâmetros de query (?...) e âncoras (#...).
    Isso evita aceitar links de página (ex: share.google,
    encurtadores, posts do Instagram) que não são a
    imagem em si.
    """

    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        return False

    caminho = urlparse(url).path.lower()

    return caminho.endswith(
        EXTENSOES_IMAGEM_VALIDAS
    )


# =========================================================
# VERIFICAR ADM
# =========================================================

def is_admin(user_id):

    try:
        return int(user_id) == int(ADMIN_ID)

    except (ValueError, TypeError):

        return False


# =========================================================
# PAINEL ADMIN
# =========================================================

async def abrir_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    if not is_admin(usuario.id):

        if update.callback_query:

            await update.callback_query.answer(
                "❌ Você não tem permissão para acessar o painel.",
                show_alert=True,
            )

        elif update.message:

            await update.message.reply_text(
                "❌ Acesso negado."
            )

        return

    limpar_estado(context)

    if update.callback_query:

        query = update.callback_query

        await query.answer()

        await query.edit_message_text(
            "👑 *PAINEL ADMINISTRATIVO*\n\n"
            "Bem-vindo ao painel de administração "
            "da PLAYER STORE.\n\n"
            "Escolha uma opção:",
            reply_markup=menu_admin(),
            parse_mode="Markdown",
        )

    else:

        await update.message.reply_text(
            "👑 *PAINEL ADMINISTRATIVO*\n\n"
            "Bem-vindo ao painel de administração "
            "da PLAYER STORE.\n\n"
            "Escolha uma opção:",
            reply_markup=menu_admin(),
            parse_mode="Markdown",
        )


# =========================================================
# MENU ADMIN
# =========================================================

def menu_admin():

    manutencao_ativa = (
        obter_configuracao("modo_manutencao")
        == "1"
    )

    label_manutencao = (
        "🔴 MANUTENÇÃO: LIGADA (tocar p/ desligar)"
        if manutencao_ativa
        else "🟢 MANUTENÇÃO: DESLIGADA (tocar p/ ligar)"
    )

    botoes = [

        [
            InlineKeyboardButton(
                label_manutencao,
                callback_data="admin_toggle_manutencao",
            )
        ],

        [
            InlineKeyboardButton(
                "📦 PRODUTOS",
                callback_data="admin_produtos",
            )
        ],

        [
            InlineKeyboardButton(
                "➕ ADICIONAR CONTAS",
                callback_data="admin_adicionar_conta",
            )
        ],

        [
            InlineKeyboardButton(
                "📊 ESTOQUE",
                callback_data="admin_estoque",
            )
        ],

        [
            InlineKeyboardButton(
                "➕ NOVO PRODUTO",
                callback_data="admin_novo_produto",
            )
        ],

        [
            InlineKeyboardButton(
                "🖼️ IMAGEM DO CATÁLOGO",
                callback_data="admin_imagem_catalogo",
            )
        ],

        [
            InlineKeyboardButton(
                "⚽ JOGOS NA TV",
                callback_data="admin_jogos_tv",
            )
        ],

        [
            InlineKeyboardButton(
                "🆘 CHAT DE SUPORTE",
                callback_data="admin_chat_suporte",
            )
        ],

        [
            InlineKeyboardButton(
                "🗂️ GRUPO DE SUPORTE (TÓPICOS)",
                callback_data="admin_grupo_suporte",
            )
        ],

        [
            InlineKeyboardButton(
                "📉 ESTOQUE MÍNIMO",
                callback_data="admin_estoque_minimo",
            )
        ],

        [
            InlineKeyboardButton(
                "📊 RELATÓRIO DE VENDAS",
                callback_data="admin_relatorio_vendas",
            )
        ],

        [
            InlineKeyboardButton(
                "📣 GRUPO DE ANÚNCIOS (ESTOQUE)",
                callback_data="admin_grupo_anuncios",
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 GRUPO OBRIGATÓRIO",
                callback_data="admin_grupo_obrigatorio",
            )
        ],

        [
            InlineKeyboardButton(
                "📢 ENVIAR NOVIDADE",
                callback_data="admin_broadcast",
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ VOLTAR AO MENU",
                callback_data="admin_voltar",
            )
        ],
    ]

    return InlineKeyboardMarkup(botoes)


# =========================================================
# LIMPAR ESTADO
# =========================================================

def limpar_estado(context):

    context.user_data[
        "admin_acao"
    ] = None

    context.user_data[
        "admin_produto_id"
    ] = None

    context.user_data[
        "admin_login_id"
    ] = None

    context.user_data[
        "admin_dados_conta"
    ] = None

    context.user_data[
        "admin_novo_nome"
    ] = None

    context.user_data[
        "admin_novo_descricao"
    ] = None

    context.user_data[
        "admin_novo_preco"
    ] = None


# =========================================================
# VERIFICAR ACESSO
# =========================================================

async def verificar_admin_query(query):

    if not is_admin(query.from_user.id):

        await query.answer(
            "❌ Acesso negado.",
            show_alert=True,
        )

        return False

    return True


# =========================================================
# LISTAR PRODUTOS ADMIN
# =========================================================

async def admin_produtos(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    produtos = listar_todos_produtos()

    botoes = []

    if not produtos:

        texto = (
            "📦 *PRODUTOS*\n\n"
            "Nenhum produto cadastrado."
        )

    else:

        texto = (
            "📦 *PRODUTOS*\n\n"
            "Escolha um produto para administrar:"
        )

        for produto in produtos:

            produto_id = produto[0]
            nome = produto[1]
            preco = float(produto[3])
            estoque = int(produto[4])

            botoes.append(
                [
                    InlineKeyboardButton(
                        f"📦 {nome[:35]}",
                        callback_data=(
                            f"admin_produto_{produto_id}"
                        ),
                    )
                ]
            )

            botoes.append(
                [
                    InlineKeyboardButton(
                        f"💰 R$ {preco:.2f} | 📦 {estoque}",
                        callback_data=(
                            f"admin_produto_{produto_id}"
                        ),
                    )
                ]
            )

    botoes.append(
        [
            InlineKeyboardButton(
                "⬅️ Voltar",
                callback_data="admin_menu",
            )
        ]
    )

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(botoes),
        parse_mode="Markdown",
    )


# =========================================================
# DETALHES DO PRODUTO
# =========================================================

async def admin_detalhes_produto(
    query,
    context,
    produto_id,
):

    if not await verificar_admin_query(query):

        return

    produto = buscar_produto(produto_id)

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

    estoque = int(estoque)

    estoque_real = consultar_estoque_logins(
        produto_id
    )

    categoria_atual = consultar_categoria_produto(
        produto_id
    )

    if categoria_atual:
        texto_categoria = (
            f"{categoria_atual[2]} {categoria_atual[1]}"
        )
    else:
        texto_categoria = "⚠️ Sem categoria"

    duracao_atual = obter_duracao_produto(
        produto_id
    )

    texto_duracao = (
        f"{duracao_atual} dias"
        if duracao_atual
        else "⚠️ Não definida"
    )

    texto = (
        "📦 *GERENCIAR PRODUTO*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ *Produto:* {nome}\n"
        f"💰 *Preço:* R$ {float(preco):.2f}\n"
        f"📦 *Estoque:* {estoque}\n"
        f"🔐 *Contas disponíveis:* {estoque_real}\n"
        f"🗂️ *Categoria:* {texto_categoria}\n"
        f"⏳ *Duração:* {texto_duracao}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 {descricao or 'Sem descrição'}"
    )

    botoes = [

        [
            InlineKeyboardButton(
                "➕ ADICIONAR CONTAS",
                callback_data=(
                    f"admin_add_login_{produto_id}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "📋 VER CONTAS",
                callback_data=(
                    f"admin_ver_logins_{produto_id}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "💰 ALTERAR PREÇO",
                callback_data=(
                    f"admin_preco_{produto_id}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "⏳ DURAÇÃO (DIAS)",
                callback_data=(
                    f"admin_duracao_{produto_id}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "🗂️ DEFINIR CATEGORIA",
                callback_data=(
                    f"admin_definir_categoria_{produto_id}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "🖼️ IMAGEM (URL)",
                callback_data=(
                    f"admin_imagem_produto_{produto_id}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "🗑️ EXCLUIR PRODUTO",
                callback_data=(
                    f"admin_excluir_produto_{produto_id}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ Voltar",
                callback_data="admin_produtos",
            )
        ],
    ]

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(botoes),
        parse_mode="Markdown",
    )


# =========================================================
# ADICIONAR CONTA
# =========================================================

async def iniciar_adicionar_conta(
    query,
    context,
    produto_id,
):

    if not await verificar_admin_query(query):

        return

    produto = buscar_produto(produto_id)

    if not produto:

        await query.answer(
            "❌ Produto não encontrado.",
            show_alert=True,
        )

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "adicionar_conta"

    context.user_data[
        "admin_produto_id"
    ] = produto_id

    nome = produto[1]

    await query.edit_message_text(
        "➕ *ADICIONAR CONTA(S) AO ESTOQUE*\n\n"
        f"📦 *Produto:* {nome}\n\n"
        "Envie agora os dados da conta.\n\n"
        "Para uma única conta, envie, por exemplo:\n\n"
        "`email@gmail.com:senha123`\n\n"
        "Ou:\n\n"
        "`Email: email@gmail.com`\n"
        "`Senha: senha123`\n"
        "`PIN: 1234`\n\n"
        "📋 *Para várias contas de uma vez,* "
        "envie uma por linha, por exemplo:\n\n"
        "`email1@gmail.com:senha1`\n"
        "`email2@gmail.com:senha2`\n"
        "`email3@gmail.com:senha3`\n\n"
        "Cada linha vira uma conta separada no "
        "estoque.\n\n"
        "⬅️ Para cancelar, clique no botão abaixo.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data=(
                            f"admin_produto_{produto_id}"
                        ),
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# DIVIDIR TEXTO EM VÁRIAS CONTAS
# =========================================================
# Regras:
# - Blocos separados por linha em branco -> cada bloco é
#   uma conta (permite formato com Email/Senha/PIN em
#   várias linhas por conta).
# - Sem linha em branco, mas com várias linhas onde nenhuma
#   usa rótulos (Email:, Senha:, PIN:...) -> cada linha é
#   uma conta (formato simples "usuario:senha" por linha).
# - Qualquer outro caso -> o texto inteiro é uma única conta.

ROTULOS_CAMPO_UNICO = (
    "email:",
    "e-mail:",
    "usuário:",
    "usuario:",
    "user:",
    "login:",
    "senha:",
    "password:",
    "pin:",
)


def dividir_contas_do_texto(texto):

    blocos = [
        bloco.strip()
        for bloco in texto.split("\n\n")
        if bloco.strip()
    ]

    if len(blocos) > 1:
        return blocos

    linhas = [
        linha.strip()
        for linha in texto.split("\n")
        if linha.strip()
    ]

    todas_linhas_simples = (
        len(linhas) > 1
        and all(
            not linha.lower().startswith(
                ROTULOS_CAMPO_UNICO
            )
            for linha in linhas
        )
    )

    if todas_linhas_simples:
        return linhas

    return [texto.strip()]


# =========================================================
# PROCESSAR ADIÇÃO DE CONTA
# =========================================================

async def processar_admin_texto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    if not is_admin(usuario.id):

        return False

    acao = context.user_data.get(
        "admin_acao"
    )

    if not acao:

        return False

    texto = (
        update.message.text.strip()
        if update.message
        and update.message.text
        else ""
    )

    if not texto:

        await update.message.reply_text(
            "❌ Envie os dados da conta em formato de texto."
        )

        return True

    # =====================================================
    # ADICIONAR CONTA
    # =====================================================

    if acao == "adicionar_conta":

        produto_id = context.user_data.get(
            "admin_produto_id"
        )

        if not produto_id:

            limpar_estado(context)

            await update.message.reply_text(
                "❌ Produto não selecionado."
            )

            return True

        produto = buscar_produto(
            produto_id
        )

        if not produto:

            limpar_estado(context)

            await update.message.reply_text(
                "❌ Produto não encontrado."
            )

            return True

        contas = dividir_contas_do_texto(texto)

        nome = produto[1]
        preco = produto[3]

        if len(contas) > 1:

            quantidade_adicionada = (
                adicionar_varios_logins(
                    produto_id,
                    contas,
                )
            )

            resumo_id = (
                f"🔢 *Contas adicionadas:* "
                f"{quantidade_adicionada}"
            )

        else:

            login_id = adicionar_login(
                produto_id,
                contas[0],
            )

            quantidade_adicionada = 1

            resumo_id = (
                f"🆔 *ID da conta:* `{login_id}`"
            )

        estoque = consultar_estoque_logins(
            produto_id
        )

        await anunciar_abastecimento_grupo(
            context,
            produto_id,
            nome,
            float(preco),
            quantidade_adicionada,
        )

        await notificar_reposicao_estoque(
            context,
            produto_id,
            nome,
        )

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *CONTA(S) ADICIONADA(S)!*\n\n"
            f"📦 *Produto:* {nome}\n"
            f"{resumo_id}\n"
            f"📊 *Contas disponíveis:* {estoque}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "➕ ADICIONAR OUTRA",
                            callback_data=(
                                f"admin_add_login_{produto_id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📦 GERENCIAR PRODUTO",
                            callback_data=(
                                f"admin_produto_{produto_id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    # =====================================================
    # ALTERAR PREÇO
    # =====================================================

    if acao == "alterar_preco":

        produto_id = context.user_data.get(
            "admin_produto_id"
        )

        try:

            preco = float(
                texto.replace(",", ".")
            )

        except ValueError:

            await update.message.reply_text(
                "❌ Digite um preço válido.\n\n"
                "Exemplo: `5.00` ou `5,00`",
                parse_mode="Markdown",
            )

            return True

        if preco <= 0:

            await update.message.reply_text(
                "❌ O preço precisa ser maior que zero."
            )

            return True

        sucesso = alterar_preco(
            produto_id,
            preco,
        )

        limpar_estado(context)

        if not sucesso:

            await update.message.reply_text(
                "❌ Não foi possível alterar o preço."
            )

            return True

        await update.message.reply_text(
            "✅ *PREÇO ALTERADO!*\n\n"
            f"💰 Novo preço: R$ {preco:.2f}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📦 GERENCIAR PRODUTO",
                            callback_data=(
                                f"admin_produto_{produto_id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    # =====================================================
    # ALTERAR DURAÇÃO (DIAS)
    # =====================================================

    if acao == "alterar_duracao":

        produto_id = context.user_data.get(
            "admin_produto_id"
        )

        try:

            dias = int(
                texto.strip()
            )

        except ValueError:

            await update.message.reply_text(
                "❌ Digite só um número inteiro de "
                "dias.\n\n"
                "Exemplo: `30`",
                parse_mode="Markdown",
            )

            return True

        if dias <= 0:

            await update.message.reply_text(
                "❌ A duração precisa ser maior "
                "que zero."
            )

            return True

        sucesso = definir_duracao_produto(
            produto_id,
            dias,
        )

        limpar_estado(context)

        if not sucesso:

            await update.message.reply_text(
                "❌ Não foi possível alterar a "
                "duração."
            )

            return True

        await update.message.reply_text(
            "✅ *DURAÇÃO ATUALIZADA!*\n\n"
            f"⏳ Nova duração: {dias} dias",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📦 GERENCIAR PRODUTO",
                            callback_data=(
                                f"admin_produto_{produto_id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    # =====================================================
    # NOVO PRODUTO
    # =====================================================

    if acao == "novo_produto_nome":

        context.user_data[
            "admin_novo_nome"
        ] = texto

        context.user_data[
            "admin_acao"
        ] = "novo_produto_descricao"

        await update.message.reply_text(
            "📝 *NOVO PRODUTO*\n\n"
            "Agora envie a descrição do produto.\n\n"
            "Exemplo:\n"
            "`Acesso por 30 dias.`",
            parse_mode="Markdown",
        )

        return True

    # =====================================================
    # DESCRIÇÃO
    # =====================================================

    if acao == "novo_produto_descricao":

        context.user_data[
            "admin_novo_descricao"
        ] = texto

        context.user_data[
            "admin_acao"
        ] = "novo_produto_preco"

        await update.message.reply_text(
            "💰 *PREÇO DO PRODUTO*\n\n"
            "Digite o preço.\n\n"
            "Exemplo:\n"
            "`5.00`\n"
            "`5,00`",
            parse_mode="Markdown",
        )

        return True

    # =====================================================
    # PREÇO NOVO PRODUTO → AGORA PEDE A CATEGORIA
    # =====================================================

    if acao == "novo_produto_preco":

        try:

            preco = float(
                texto.replace(",", ".")
            )

        except ValueError:

            await update.message.reply_text(
                "❌ Digite um preço válido."
            )

            return True

        if preco <= 0:

            await update.message.reply_text(
                "❌ O preço precisa ser maior que zero."
            )

            return True

        context.user_data[
            "admin_novo_preco"
        ] = preco

        context.user_data[
            "admin_acao"
        ] = "novo_produto_categoria"

        categorias = listar_categorias()

        if not categorias:

            # Sem categorias cadastradas: cadastra sem categoria.
            nome = context.user_data.get(
                "admin_novo_nome"
            )

            descricao = context.user_data.get(
                "admin_novo_descricao"
            )

            produto_id = cadastrar_produto(
                nome,
                descricao,
                preco,
                0,
            )

            limpar_estado(context)

            await update.message.reply_text(
                "⚠️ Nenhuma categoria cadastrada. "
                "O produto foi criado sem categoria.\n\n"
                "✅ *PRODUTO CADASTRADO!*\n\n"
                f"📦 {nome}\n"
                f"💰 R$ {preco:.2f}\n"
                f"🆔 ID: `{produto_id}`",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ ADICIONAR CONTAS",
                                callback_data=(
                                    f"admin_add_login_{produto_id}"
                                ),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "👑 PAINEL ADMIN",
                                callback_data="admin_menu",
                            )
                        ],
                    ]
                ),
                parse_mode="Markdown",
            )

            return True

        botoes = []

        for categoria in categorias:

            categoria_id = categoria[0]
            nome_categoria = categoria[1]
            emoji = categoria[2]

            botoes.append(
                [
                    InlineKeyboardButton(
                        f"{emoji} {nome_categoria}",
                        callback_data=(
                            f"admin_categoria_produto_{categoria_id}"
                        ),
                    )
                ]
            )

        await update.message.reply_text(
            "🗂️ *CATEGORIA DO PRODUTO*\n\n"
            "Escolha em qual categoria este produto "
            "vai aparecer:",
            reply_markup=InlineKeyboardMarkup(
                botoes
            ),
            parse_mode="Markdown",
        )

        return True

    # =====================================================
    # DEFINIR IMAGEM DO PRODUTO (URL)
    # =====================================================

    if acao == "definir_imagem_produto":

        produto_id = context.user_data.get(
            "admin_produto_id"
        )

        if not produto_id:

            limpar_estado(context)

            await update.message.reply_text(
                "❌ Produto não selecionado."
            )

            return True

        url = texto.strip()

        if not url_parece_imagem(url):

            await update.message.reply_text(
                "❌ Esse link não parece ser uma "
                "imagem direta.\n\n"
                "Precisa ser um link `http://` ou "
                "`https://` que termine em `.jpg`, "
                "`.jpeg`, `.png`, `.webp` ou `.gif` "
                "— não um link de página (como "
                "share.google, encurtadores, posts "
                "de rede social, etc).\n\n"
                "Dica: se não tiver onde hospedar, "
                "suba a imagem em imgur.com (sem "
                "precisar de conta) e use o "
                "\"Copy image link\" gerado por lá.\n\n"
                "Envie o link novamente.",
                parse_mode="Markdown",
            )

            return True

        definir_imagem_produto(
            produto_id,
            url,
        )

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *IMAGEM DO PRODUTO ATUALIZADA!*\n\n"
            "Ela vai aparecer nos resultados de "
            "busca inline a partir de agora.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📦 GERENCIAR PRODUTO",
                            callback_data=(
                                f"admin_produto_{produto_id}"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    # =====================================================
    # JOGOS NA TV
    # =====================================================

    if acao == "editar_jogos_tv":

        definir_configuracao(
            "jogos_tv_texto",
            texto,
        )

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *LISTA DE JOGOS ATUALIZADA!*\n\n"
            "Ela já está valendo pro botão "
            "\"⚽ JOGOS NA TV\" do menu.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    # =====================================================
    # CHAT DE SUPORTE (DESTINO DOS TICKETS)
    # =====================================================

    if acao == "definir_chat_suporte":

        valor = texto.strip()

        if not valor.lstrip("-").isdigit():

            await update.message.reply_text(
                "❌ Isso não parece um ID válido.\n\n"
                "Digite só o número (ex: `123456789`).",
                parse_mode="Markdown",
            )

            return True

        definir_configuracao(
            "suporte_chat_id",
            valor,
        )

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *CHAT DE SUPORTE ATUALIZADO!*\n\n"
            f"📋 Novo ID: `{valor}`\n\n"
            "Os próximos tickets de suporte vão "
            "chegar por lá. Se essa conta ainda "
            "não deu `/start` no bot, peça pra "
            "ela fazer isso agora — senão o "
            "envio vai falhar.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    if acao == "definir_estoque_minimo":

        valor = texto.strip()

        if not valor.isdigit() or int(valor) < 0:

            await update.message.reply_text(
                "❌ Digite um número inteiro "
                "válido (0 ou maior)."
            )

            return True

        definir_configuracao(
            "estoque_minimo",
            valor,
        )

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *ESTOQUE MÍNIMO ATUALIZADO!*\n\n"
            f"📉 Novo valor: {valor}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    if acao == "definir_grupo_anuncios":

        valor = texto.strip()

        if not (
            valor.lstrip("-").isdigit()
            and valor.startswith("-")
        ):

            await update.message.reply_text(
                "❌ Isso não parece um ID de grupo "
                "válido.\n\n"
                "IDs de grupo/canal começam com "
                "`-` (ex: `-1001234567890`). Use "
                "`/grupoid` dentro do grupo pra "
                "pegar o ID certo.",
                parse_mode="Markdown",
            )

            return True

        definir_configuracao(
            "grupo_anuncios_id",
            valor,
        )

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *GRUPO DE ANÚNCIOS ATUALIZADO!*\n\n"
            f"📋 Novo ID: `{valor}`\n\n"
            "⚠️ Confirme que o bot é *admin* "
            "desse grupo/canal, senão os posts "
            "vão falhar.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    if acao == "definir_grupo_obrigatorio_id":

        valor = texto.strip()

        if not (
            valor.lstrip("-").isdigit()
            and valor.startswith("-")
        ):

            await update.message.reply_text(
                "❌ Isso não parece um ID de grupo "
                "válido.\n\n"
                "IDs de grupo/canal começam com "
                "`-` (ex: `-1001234567890`). Use "
                "`/grupoid` dentro do grupo pra "
                "pegar o ID certo.",
                parse_mode="Markdown",
            )

            return True

        context.user_data[
            "novo_grupo_obrigatorio_id"
        ] = valor

        context.user_data[
            "admin_acao"
        ] = "definir_grupo_obrigatorio_link"

        await update.message.reply_text(
            "✅ ID salvo!\n\n"
            "Agora cole o *link de convite* "
            "desse grupo/canal (o que aparece "
            "quando você toca em \"Adicionar "
            "membro\" → \"Compartilhar link\").\n\n"
            "Exemplo:\n"
            "`https://t.me/+AbCdEfGhIjK`",
            parse_mode="Markdown",
        )

        return True

    if acao == "definir_grupo_obrigatorio_link":

        valor = texto.strip()

        if not (
            valor.startswith("https://t.me/")
            or valor.startswith("http://t.me/")
        ):

            await update.message.reply_text(
                "❌ Isso não parece um link do "
                "Telegram. Precisa começar com "
                "`https://t.me/`.",
                parse_mode="Markdown",
            )

            return True

        grupo_id = context.user_data.get(
            "novo_grupo_obrigatorio_id"
        )

        if not grupo_id:

            limpar_estado(context)

            await update.message.reply_text(
                "❌ Sessão expirada. Comece de "
                "novo pelo painel."
            )

            return True

        adicionar_grupo_obrigatorio(
            grupo_id,
            valor,
        )

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *GRUPO ADICIONADO!*\n\n"
            "A partir de agora, o bot também "
            "vai exigir que o cliente entre "
            "nesse grupo antes de usar o "
            "`/start`.\n\n"
            "⚠️ Confirme que o bot é *admin* "
            "desse grupo/canal (precisa disso "
            "pra checar quem é membro).\n\n"
            "Quer adicionar outro grupo?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "➕ ADICIONAR OUTRO",
                            callback_data=(
                                "admin_add_"
                                "grupo_obrigatorio"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔒 VER GRUPOS",
                            callback_data=(
                                "admin_grupo_"
                                "obrigatorio"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    if acao == "definir_broadcast_texto":

        context.user_data[
            "broadcast_texto"
        ] = texto

        limpar_estado(context)

        total_usuarios = len(
            listar_todos_usuarios()
        )

        await update.message.reply_text(
            "👀 *PRÉVIA DA MENSAGEM*\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"{texto}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"Vai ser enviada pra "
            f"{total_usuarios} cliente(s). "
            "Confirmar?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ CONFIRMAR ENVIO",
                            callback_data=(
                                "admin_confirmar_broadcast"
                            ),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ CANCELAR",
                            callback_data="admin_menu",
                        )
                    ],
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    if acao == "definir_grupo_suporte":

        valor = texto.strip()

        if not (
            valor.lstrip("-").isdigit()
            and valor.startswith("-")
        ):

            await update.message.reply_text(
                "❌ Isso não parece um ID de grupo "
                "válido.\n\n"
                "IDs de grupo/supergrupo começam "
                "com `-` (ex: `-1001234567890`). "
                "Use o comando `/grupoid` dentro "
                "do grupo pra pegar o ID certo.",
                parse_mode="Markdown",
            )

            return True

        definir_configuracao(
            "suporte_grupo_id",
            valor,
        )

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *GRUPO DE SUPORTE ATUALIZADO!*\n\n"
            f"📋 Novo ID: `{valor}`\n\n"
            "A partir de agora, cada cliente que "
            "abrir um ticket ganha um tópico "
            "novo nesse grupo.\n\n"
            "⚠️ Confirme que o bot é *admin* do "
            "grupo com permissão de \"Gerenciar "
            "Tópicos\", senão a criação dos "
            "tópicos vai falhar.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "👑 PAINEL ADMIN",
                            callback_data="admin_menu",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )

        return True

    return False


# =========================================================
# ALTERAR PREÇO
# =========================================================

async def iniciar_alterar_preco(
    query,
    context,
    produto_id,
):

    if not await verificar_admin_query(query):

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

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "alterar_preco"

    context.user_data[
        "admin_produto_id"
    ] = produto_id

    await query.edit_message_text(
        "💰 *ALTERAR PREÇO*\n\n"
        f"📦 Produto: {produto[1]}\n"
        f"💰 Preço atual: R$ {float(produto[3]):.2f}\n\n"
        "Digite o novo preço.\n\n"
        "Exemplo:\n"
        "`5`\n"
        "`5,50`\n"
        "`10.00`",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data=(
                            f"admin_produto_{produto_id}"
                        ),
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# ALTERAR DURAÇÃO (DIAS)
# =========================================================

async def iniciar_alterar_duracao(
    query,
    context,
    produto_id,
):

    if not await verificar_admin_query(query):

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

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "alterar_duracao"

    context.user_data[
        "admin_produto_id"
    ] = produto_id

    duracao_atual = obter_duracao_produto(
        produto_id
    )

    await query.edit_message_text(
        "⏳ *DURAÇÃO DO PRODUTO*\n\n"
        f"📦 Produto: {produto[1]}\n"
        f"⏳ Duração atual: {duracao_atual} dias\n\n"
        "Digite a nova duração em dias "
        "(usada pra calcular o vencimento e "
        "te avisar quando uma conta estiver "
        "perto de vencer).\n\n"
        "Exemplo:\n"
        "`30`\n"
        "`7`",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data=(
                            f"admin_produto_{produto_id}"
                        ),
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# VER LOGINS
# =========================================================

async def admin_ver_logins(
    query,
    produto_id,
):

    if not await verificar_admin_query(query):

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

    logins = listar_logins_disponiveis(
        produto_id
    )

    if not logins:

        texto = (
            "📋 *CONTAS DISPONÍVEIS*\n\n"
            f"📦 {produto[1]}\n\n"
            "❌ Nenhuma conta disponível."
        )

        botoes = [
            [
                InlineKeyboardButton(
                    "➕ ADICIONAR CONTA",
                    callback_data=(
                        f"admin_add_login_{produto_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data=(
                        f"admin_produto_{produto_id}"
                    ),
                )
            ],
        ]

        await query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(botoes),
            parse_mode="Markdown",
        )

        return

    texto = (
        "📋 *CONTAS DISPONÍVEIS*\n\n"
        f"📦 *Produto:* {produto[1]}\n"
        f"📊 *Total:* {len(logins)}\n\n"
    )

    botoes = []

    # Mostra no máximo 30 por página/mensagem
    for login in logins[:30]:

        login_id = login[0]
        dados = login[1]

        resumo = dados.replace(
            "\n",
            " | ",
        )

        if len(resumo) > 45:

            resumo = (
                resumo[:45]
                + "..."
            )

        botoes.append(
            [
                InlineKeyboardButton(
                    f"🗑️ #{login_id} {resumo}",
                    callback_data=(
                        f"admin_excluir_login_{login_id}"
                    ),
                )
            ]
        )

    if len(logins) > 30:

        texto += (
            "⚠️ Mostrando somente as "
            "30 primeiras contas.\n\n"
        )

    texto += (
        "Clique em uma conta para excluir."
    )

    botoes.append(
        [
            InlineKeyboardButton(
                "➕ ADICIONAR CONTA",
                callback_data=(
                    f"admin_add_login_{produto_id}"
                ),
            )
        ]
    )

    botoes.append(
        [
            InlineKeyboardButton(
                "⬅️ Voltar",
                callback_data=(
                    f"admin_produto_{produto_id}"
                ),
            )
        ]
    )

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(botoes),
        parse_mode="Markdown",
    )


# =========================================================
# CONFIRMAR EXCLUSÃO LOGIN
# =========================================================

async def confirmar_excluir_login(
    query,
    login_id,
):

    if not await verificar_admin_query(query):

        return

    from database import consultar_login

    login = consultar_login(
        login_id
    )

    if not login:

        await query.answer(
            "❌ Conta não encontrada.",
            show_alert=True,
        )

        return

    produto_id = login[1]
    dados = login[2]
    status = login[3]

    if status != "disponivel":

        await query.answer(
            "❌ Essa conta já foi vendida.",
            show_alert=True,
        )

        return

    resumo = dados

    if len(resumo) > 500:

        resumo = (
            resumo[:500]
            + "..."
        )

    await query.edit_message_text(
        "⚠️ *EXCLUIR CONTA?*\n\n"
        f"🆔 ID: `{login_id}`\n\n"
        f"📦 Dados:\n"
        f"`{resumo}`\n\n"
        "Essa ação não pode ser desfeita.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🗑️ SIM, EXCLUIR",
                        callback_data=(
                            f"admin_confirmar_excluir_login_{login_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data=(
                            f"admin_ver_logins_{produto_id}"
                        ),
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# EXCLUIR LOGIN
# =========================================================

async def executar_excluir_login(
    query,
    login_id,
):

    if not await verificar_admin_query(query):

        return

    from database import consultar_login

    login = consultar_login(
        login_id
    )

    if not login:

        await query.answer(
            "❌ Conta não encontrada.",
            show_alert=True,
        )

        return

    produto_id = login[1]
    status = login[3]

    if status != "disponivel":

        await query.answer(
            "❌ Essa conta já foi vendida.",
            show_alert=True,
        )

        return

    sucesso = excluir_login(
        login_id
    )

    if not sucesso:

        await query.answer(
            "❌ Não foi possível excluir.",
            show_alert=True,
        )

        return

    await query.answer(
        "✅ Conta excluída.",
        show_alert=True,
    )

    await admin_ver_logins(
        query,
        produto_id,
    )


# =========================================================
# ESTOQUE GERAL
# =========================================================

async def admin_estoque(
    query,
):

    if not await verificar_admin_query(query):

        return

    produtos = listar_todos_produtos()

    texto = (
        "📊 *ESTOQUE GERAL*\n\n"
    )

    if not produtos:

        texto += (
            "❌ Nenhum produto cadastrado."
        )

    else:

        for produto in produtos:

            produto_id = produto[0]
            nome = produto[1]
            estoque = consultar_estoque_logins(
                produto_id
            )

            texto += (
                f"📦 *{nome}*\n"
                f"🔐 Contas: {estoque}\n"
                f"💰 Preço: R$ {float(produto[3]):.2f}\n\n"
            )

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 ATUALIZAR",
                        callback_data="admin_estoque",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Voltar",
                        callback_data="admin_menu",
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# IMAGEM DO CATÁLOGO
# =========================================================

async def iniciar_imagem_catalogo(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "aguardando_imagem_catalogo"

    imagem_atual = obter_configuracao(
        "imagem_catalogo_id"
    )

    texto = (
        "🖼️ *IMAGEM DO CATÁLOGO*\n\n"
        "Envie agora uma foto ou GIF "
        "para aparecer no topo do catálogo "
        "(antes de \"Selecione a categoria\").\n\n"
    )

    if imagem_atual:
        texto += "✅ Já existe uma imagem configurada.\n\n"

    texto += "⬅️ Para cancelar, clique no botão abaixo."

    botoes = [
        [
            InlineKeyboardButton(
                "❌ CANCELAR",
                callback_data="admin_menu",
            )
        ]
    ]

    if imagem_atual:

        botoes.insert(
            0,
            [
                InlineKeyboardButton(
                    "🗑️ REMOVER IMAGEM ATUAL",
                    callback_data="admin_remover_imagem_catalogo",
                )
            ],
        )

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            botoes
        ),
        parse_mode="Markdown",
    )


# =========================================================
# ESTOQUE MÍNIMO (LIMITE DO ALERTA DE ESTOQUE BAIXO)
# =========================================================

async def iniciar_estoque_minimo(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "definir_estoque_minimo"

    atual = (
        obter_configuracao("estoque_minimo")
        or "3"
    )

    await query.edit_message_text(
        "📉 *ESTOQUE MÍNIMO*\n\n"
        f"📋 *Valor atual:* {atual}\n\n"
        "Digite o número mínimo de contas "
        "que um produto pode ter antes de "
        "você receber um aviso de estoque "
        "baixo.\n\n"
        "Exemplo:\n"
        "`3`\n"
        "`5`",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# GRUPO DE ANÚNCIOS (ESTOQUE)
# =========================================================

async def iniciar_grupo_anuncios(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "definir_grupo_anuncios"

    atual = obter_configuracao(
        "grupo_anuncios_id"
    )

    texto = (
        "📣 *GRUPO DE ANÚNCIOS (ESTOQUE)*\n\n"
        "Esse grupo/canal recebe um post "
        "automático toda vez que um produto "
        "reabastece do zero, ou esgota.\n\n"
        "*Como configurar:*\n\n"
        "1️⃣ Crie um grupo ou canal\n"
        "2️⃣ Adicione este bot como *admin*\n"
        "3️⃣ Dentro dele, mande `/grupoid`\n"
        "4️⃣ Cole o ID aqui\n\n"
    )

    if atual:
        texto += f"📋 *ID atual:* `{atual}`\n\n"

    texto += "⬅️ Para cancelar, clique no botão abaixo."

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# GRUPO OBRIGATÓRIO (ENTRAR ANTES DE USAR O BOT)
# =========================================================

async def iniciar_grupo_obrigatorio(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    grupos = listar_grupos_obrigatorios()

    texto = (
        "🔒 *GRUPOS OBRIGATÓRIOS*\n\n"
        "Se configurado, o cliente só consegue "
        "usar o bot depois de entrar em *todos* "
        "os grupos/canais cadastrados abaixo.\n\n"
    )

    botoes = []

    if grupos:

        texto += "📋 *Cadastrados:*\n\n"

        for registro_id, grupo_id, link in grupos:

            texto += f"• `{grupo_id}` — {link}\n"

            botoes.append(
                [
                    InlineKeyboardButton(
                        f"🗑️ Remover {grupo_id}",
                        callback_data=(
                            "admin_rm_grupo_obg_"
                            f"{registro_id}"
                        ),
                    )
                ]
            )

        texto += "\n"

    else:
        texto += (
            "📋 *Nenhum cadastrado* — hoje "
            "qualquer pessoa pode usar o bot "
            "livremente.\n\n"
        )

    botoes.append(
        [
            InlineKeyboardButton(
                "➕ ADICIONAR GRUPO",
                callback_data=(
                    "admin_add_grupo_obrigatorio"
                ),
            )
        ]
    )

    botoes.append(
        [
            InlineKeyboardButton(
                "⬅️ VOLTAR",
                callback_data="admin_menu",
            )
        ]
    )

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(botoes),
        parse_mode="Markdown",
    )


async def iniciar_adicionar_grupo_obrigatorio(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "definir_grupo_obrigatorio_id"

    texto = (
        "➕ *ADICIONAR GRUPO OBRIGATÓRIO*\n\n"
        "*Como configurar:*\n\n"
        "1️⃣ Mande `/grupoid` dentro do grupo\n"
        "2️⃣ Cole o ID aqui\n"
        "3️⃣ Depois eu vou pedir o link de "
        "convite\n\n"
        "⬅️ Para cancelar, clique no botão abaixo."
    )

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data=(
                            "admin_grupo_obrigatorio"
                        ),
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


async def executar_remover_grupo_obrigatorio(
    query,
    context,
    registro_id,
):

    if not await verificar_admin_query(query):

        return

    remover_grupo_obrigatorio(registro_id)

    await query.answer(
        "✅ Grupo removido!",
    )

    await iniciar_grupo_obrigatorio(
        query,
        context,
    )


# =========================================================
# BROADCAST (ENVIAR NOVIDADE PRA TODOS)
# =========================================================

async def iniciar_broadcast(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "definir_broadcast_texto"

    await query.edit_message_text(
        "📢 *ENVIAR NOVIDADE*\n\n"
        "Digite a mensagem que vai ser "
        "enviada pra *todos* os clientes "
        "cadastrados no bot.\n\n"
        "Você vai poder revisar antes de "
        "confirmar o envio.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


async def executar_broadcast(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    texto = context.user_data.get(
        "broadcast_texto"
    )

    if not texto:

        await query.answer(
            "❌ Nenhuma mensagem pendente.",
            show_alert=True,
        )
        return

    usuarios = listar_todos_usuarios()

    sucesso = 0
    falha = 0

    for usuario_id in usuarios:

        try:
            await context.bot.send_message(
                chat_id=usuario_id,
                text=texto,
                parse_mode="Markdown",
            )
            sucesso += 1

        except Exception:
            falha += 1

    context.user_data.pop(
        "broadcast_texto", None
    )

    await query.edit_message_text(
        "✅ *BROADCAST ENVIADO!*\n\n"
        f"📨 Entregue: {sucesso}\n"
        f"❌ Falhou: {falha}",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "👑 PAINEL ADMIN",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# GRUPO DE SUPORTE COM TÓPICOS (HELPDESK)
# =========================================================

async def iniciar_grupo_suporte(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "definir_grupo_suporte"

    grupo_atual = obter_configuracao(
        "suporte_grupo_id"
    )

    texto = (
        "🗂️ *GRUPO DE SUPORTE (TÓPICOS)*\n\n"
        "Cada cliente que abrir um ticket "
        "ganha um tópico separado dentro de "
        "um grupo — organizado tipo um "
        "helpdesk, e qualquer pessoa que "
        "você adicionar no grupo pode "
        "responder.\n\n"
        "*Como configurar:*\n\n"
        "1️⃣ Crie um grupo novo no Telegram\n"
        "2️⃣ Ative *Tópicos* nas configurações "
        "do grupo (Editar → Tópicos)\n"
        "3️⃣ Adicione este bot como *admin* do "
        "grupo, com permissão de "
        "\"Gerenciar Tópicos\"\n"
        "4️⃣ Dentro do grupo, mande o comando "
        "`/grupoid` — o bot responde com o ID\n"
        "5️⃣ Cole esse ID aqui\n\n"
    )

    if grupo_atual:
        texto += (
            f"📋 *ID atual:* `{grupo_atual}`\n\n"
        )
    else:
        texto += (
            "📋 *Nenhum cadastrado* — os tickets "
            "continuam indo pro chat de suporte "
            "individual (se configurado) ou pra "
            "conta admin padrão.\n\n"
        )

    texto += "⬅️ Para cancelar, clique no botão abaixo."

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# JOGOS NA TV
# =========================================================

async def iniciar_jogos_tv(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "editar_jogos_tv"

    jogos_atual = obter_configuracao(
        "jogos_tv_texto"
    )

    texto = (
        "⚽ *JOGOS NA TV*\n\n"
        "Envie o texto com a lista de jogos "
        "que vai aparecer pros clientes "
        "(pode ser em várias linhas).\n\n"
        "Exemplo:\n"
        "`🔴 16h - Flamengo x Palmeiras`\n"
        "`🔵 18h30 - Corinthians x São Paulo`\n\n"
    )

    if jogos_atual:
        texto += (
            "📋 *Lista atual:*\n\n"
            f"{jogos_atual}\n\n"
        )

    texto += "⬅️ Para cancelar, clique no botão abaixo."

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# CHAT DE SUPORTE (DESTINO DOS TICKETS)
# =========================================================

async def iniciar_chat_suporte(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "definir_chat_suporte"

    destino_atual = obter_configuracao(
        "suporte_chat_id"
    )

    texto = (
        "🆘 *CHAT DE SUPORTE*\n\n"
        "Envie o ID numérico da conta do "
        "Telegram que vai receber os tickets "
        "de suporte (pode ser diferente da "
        "conta admin do bot).\n\n"
        "⚠️ *Importante:* essa conta precisa "
        "ter dado `/start` no bot pelo menos "
        "uma vez antes — sem isso o Telegram "
        "não deixa o bot enviar mensagem pra "
        "ela.\n\n"
        "Pra descobrir o ID de uma conta, "
        "peça pra ela mandar `/start` nesse "
        "bot e me avise; ou use um bot como "
        "@userinfobot.\n\n"
    )

    if destino_atual:
        texto += (
            f"📋 *ID atual:* `{destino_atual}`\n\n"
        )
    else:
        texto += (
            "📋 *Nenhum cadastrado* — os tickets "
            "vão continuar chegando na conta "
            "admin padrão.\n\n"
        )

    texto += "⬅️ Para cancelar, clique no botão abaixo."

    await query.edit_message_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# PROCESSAR MÍDIA (FOTO OU GIF) DO ADMIN
# =========================================================

async def processar_admin_midia(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    usuario = update.effective_user

    if not usuario or not is_admin(usuario.id):

        return False

    acao = context.user_data.get(
        "admin_acao"
    )

    if acao != "aguardando_imagem_catalogo":

        return False

    if not update.message:

        return True

    file_id = None
    tipo = None

    if update.message.photo:

        file_id = update.message.photo[-1].file_id
        tipo = "photo"

    elif update.message.animation:

        file_id = update.message.animation.file_id
        tipo = "animation"

    if not file_id:

        await update.message.reply_text(
            "❌ Envie uma foto ou um GIF."
        )

        return True

    definir_configuracao(
        "imagem_catalogo_id",
        file_id,
    )

    definir_configuracao(
        "imagem_catalogo_tipo",
        tipo,
    )

    limpar_estado(context)

    await update.message.reply_text(
        "✅ *IMAGEM DO CATÁLOGO ATUALIZADA!*\n\n"
        "Ela vai aparecer no topo do catálogo "
        "a partir de agora.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "👑 PAINEL ADMIN",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )

    return True


# =========================================================
# REMOVER IMAGEM DO CATÁLOGO
# =========================================================

async def remover_imagem_catalogo(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    remover_configuracao(
        "imagem_catalogo_id"
    )

    remover_configuracao(
        "imagem_catalogo_tipo"
    )

    limpar_estado(context)

    await query.edit_message_text(
        "✅ Imagem do catálogo removida.\n\n"
        "O catálogo volta a mostrar somente texto.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "👑 PAINEL ADMIN",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# IMAGEM DO PRODUTO (URL)
# =========================================================

async def iniciar_imagem_produto(
    query,
    context,
    produto_id,
):

    if not await verificar_admin_query(query):

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

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "definir_imagem_produto"

    context.user_data[
        "admin_produto_id"
    ] = produto_id

    await query.edit_message_text(
        "🖼️ *IMAGEM DO PRODUTO (URL)*\n\n"
        f"📦 Produto: {produto[1]}\n\n"
        "Envie o link (URL) da imagem que vai "
        "aparecer nos resultados de busca inline.\n\n"
        "Precisa ser um link direto pra imagem "
        "(terminando em `.jpg`, `.png`, `.webp` "
        "ou `.gif`) — não um link de página ou "
        "de compartilhamento.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data=(
                            f"admin_produto_{produto_id}"
                        ),
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# NOVO PRODUTO
# =========================================================

async def iniciar_novo_produto(
    query,
    context,
):

    if not await verificar_admin_query(query):

        return

    limpar_estado(context)

    context.user_data[
        "admin_acao"
    ] = "novo_produto_nome"

    await query.edit_message_text(
        "➕ *NOVO PRODUTO*\n\n"
        "Digite o nome do produto.\n\n"
        "Exemplo:\n"
        "`📺 NETFLIX PREMIUM 30 DIAS`",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data="admin_menu",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# FINALIZAR CADASTRO DE PRODUTO COM CATEGORIA
# =========================================================

async def finalizar_novo_produto_com_categoria(
    query,
    context,
    categoria_id,
):

    if not await verificar_admin_query(query):

        return

    if context.user_data.get(
        "admin_acao"
    ) != "novo_produto_categoria":

        await query.answer(
            "❌ Nenhum cadastro de produto em andamento.",
            show_alert=True,
        )

        return

    nome = context.user_data.get(
        "admin_novo_nome"
    )

    descricao = context.user_data.get(
        "admin_novo_descricao"
    )

    preco = context.user_data.get(
        "admin_novo_preco"
    )

    if not nome or preco is None:

        limpar_estado(context)

        await query.answer(
            "❌ Dados do produto incompletos. "
            "Cadastre novamente.",
            show_alert=True,
        )

        return

    produto_id = cadastrar_produto(
        nome,
        descricao,
        preco,
        0,
    )

    definir_categoria_produto(
        produto_id,
        categoria_id,
    )

    limpar_estado(context)

    await query.edit_message_text(
        "✅ *PRODUTO CADASTRADO!*\n\n"
        f"📦 {nome}\n"
        f"💰 R$ {float(preco):.2f}\n"
        f"🆔 ID: `{produto_id}`\n\n"
        "Agora você pode adicionar as contas "
        "pelo painel.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ ADICIONAR CONTAS",
                        callback_data=(
                            f"admin_add_login_{produto_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📦 GERENCIAR PRODUTO",
                        callback_data=(
                            f"admin_produto_{produto_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "👑 PAINEL ADMIN",
                        callback_data="admin_menu",
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# DEFINIR CATEGORIA DE PRODUTO EXISTENTE
# =========================================================

async def iniciar_definir_categoria_produto(
    query,
    context,
    produto_id,
):

    if not await verificar_admin_query(query):

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

    categorias = listar_categorias()

    if not categorias:

        await query.answer(
            "❌ Nenhuma categoria cadastrada.",
            show_alert=True,
        )

        return

    botoes = []

    for categoria in categorias:

        categoria_id = categoria[0]
        nome_categoria = categoria[1]
        emoji = categoria[2]

        botoes.append(
            [
                InlineKeyboardButton(
                    f"{emoji} {nome_categoria}",
                    callback_data=(
                        f"admin_set_categoria_"
                        f"{produto_id}_{categoria_id}"
                    ),
                )
            ]
        )

    botoes.append(
        [
            InlineKeyboardButton(
                "⬅️ Voltar",
                callback_data=(
                    f"admin_produto_{produto_id}"
                ),
            )
        ]
    )

    await query.edit_message_text(
        "🗂️ *DEFINIR CATEGORIA*\n\n"
        f"📦 Produto: {produto[1]}\n\n"
        "Escolha a categoria:",
        reply_markup=InlineKeyboardMarkup(
            botoes
        ),
        parse_mode="Markdown",
    )


async def executar_definir_categoria_produto(
    query,
    context,
    produto_id,
    categoria_id,
):

    if not await verificar_admin_query(query):

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

    definir_categoria_produto(
        produto_id,
        categoria_id,
    )

    await query.answer(
        "✅ Categoria definida.",
        show_alert=True,
    )

    await admin_detalhes_produto(
        query,
        context,
        produto_id,
    )


# =========================================================
# CONFIRMAR EXCLUSÃO DE PRODUTO
# =========================================================

async def confirmar_excluir_produto(
    query,
    produto_id,
):

    if not await verificar_admin_query(query):

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

    estoque = consultar_estoque_logins(
        produto_id
    )

    await query.edit_message_text(
        "⚠️ *EXCLUIR PRODUTO?*\n\n"
        f"📦 {produto[1]}\n"
        f"💰 R$ {float(produto[3]):.2f}\n"
        f"🔐 Contas disponíveis: {estoque}\n\n"
        "⚠️ Esta ação excluirá o produto.\n"
        "Essa operação não pode ser desfeita.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🗑️ SIM, EXCLUIR",
                        callback_data=(
                            f"admin_confirmar_excluir_produto_{produto_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ CANCELAR",
                        callback_data=(
                            f"admin_produto_{produto_id}"
                        ),
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# =========================================================
# EXECUTAR EXCLUSÃO PRODUTO
# =========================================================

async def executar_excluir_produto(
    query,
    produto_id,
):

    if not await verificar_admin_query(query):

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

    sucesso = excluir_produto(
        produto_id
    )

    if not sucesso:

        await query.answer(
            "❌ Não foi possível excluir o produto.",
            show_alert=True,
        )

        return

    await query.answer(
        "✅ Produto excluído.",
        show_alert=True,
    )

    await admin_produtos(
        query,
        None,
    )


# =========================================================
# HANDLER DOS BOTÕES ADMIN
# =========================================================

async def botoes_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if not is_admin(query.from_user.id):

        await query.answer(
            "❌ Acesso negado.",
            show_alert=True,
        )

        return

    acao = query.data

    await query.answer()

    # =====================================================
    # MENU ADMIN
    # =====================================================

    if acao == "admin_menu":

        await abrir_admin(
            update,
            context,
        )

        return

    if acao == "admin_toggle_manutencao":

        atual = obter_configuracao(
            "modo_manutencao"
        )

        novo = (
            "0" if atual == "1" else "1"
        )

        definir_configuracao(
            "modo_manutencao",
            novo,
        )

        await query.answer(
            "🔴 Manutenção ativada."
            if novo == "1"
            else "🟢 Manutenção desativada.",
            show_alert=True,
        )

        await abrir_admin(
            update,
            context,
        )

        return

    # =====================================================
    # PRODUTOS
    # =====================================================

    if acao == "admin_produtos":

        await admin_produtos(
            query,
            context,
        )

        return

    # =====================================================
    # ESTOQUE
    # =====================================================

    if acao == "admin_estoque":

        await admin_estoque(
            query,
        )

        return

    # =====================================================
    # NOVO PRODUTO
    # =====================================================

    if acao == "admin_novo_produto":

        await iniciar_novo_produto(
            query,
            context,
        )

        return

    # =====================================================
    # IMAGEM DO CATÁLOGO
    # =====================================================

    if acao == "admin_imagem_catalogo":

        await iniciar_imagem_catalogo(
            query,
            context,
        )

        return

    if acao == "admin_remover_imagem_catalogo":

        await remover_imagem_catalogo(
            query,
            context,
        )

        return

    if acao == "admin_jogos_tv":

        await iniciar_jogos_tv(
            query,
            context,
        )

        return

    if acao == "admin_chat_suporte":

        await iniciar_chat_suporte(
            query,
            context,
        )

        return

    if acao == "admin_grupo_suporte":

        await iniciar_grupo_suporte(
            query,
            context,
        )

        return

    if acao == "admin_grupo_anuncios":

        await iniciar_grupo_anuncios(
            query,
            context,
        )

        return

    if acao == "admin_grupo_obrigatorio":

        await iniciar_grupo_obrigatorio(
            query,
            context,
        )

        return

    if acao == "admin_add_grupo_obrigatorio":

        await iniciar_adicionar_grupo_obrigatorio(
            query,
            context,
        )

        return

    if acao.startswith("admin_rm_grupo_obg_"):

        try:
            registro_id = int(
                acao.replace(
                    "admin_rm_grupo_obg_",
                    "",
                    1,
                )
            )
        except ValueError:
            await query.answer(
                "❌ Grupo inválido.",
                show_alert=True,
            )
            return

        await executar_remover_grupo_obrigatorio(
            query,
            context,
            registro_id,
        )

        return

    if acao == "admin_broadcast":

        await iniciar_broadcast(
            query,
            context,
        )

        return

    if acao == "admin_confirmar_broadcast":

        await executar_broadcast(
            query,
            context,
        )

        return

    if acao == "admin_estoque_minimo":

        await iniciar_estoque_minimo(
            query,
            context,
        )

        return

    # =====================================================
    # CATEGORIA DO NOVO PRODUTO
    # =====================================================

    if acao.startswith(
        "admin_categoria_produto_"
    ):

        try:

            categoria_id = int(
                acao.replace(
                    "admin_categoria_produto_",
                    "",
                    1,
                )
            )

        except ValueError:

            await query.answer(
                "❌ Categoria inválida.",
                show_alert=True,
            )

            return

        await finalizar_novo_produto_com_categoria(
            query,
            context,
            categoria_id,
        )

        return

    # =====================================================
    # ADICIONAR CONTA - MENU
    # =====================================================

    if acao == "admin_adicionar_conta":

        produtos = listar_todos_produtos()

        if not produtos:

            await query.edit_message_text(
                "➕ *ADICIONAR CONTAS*\n\n"
                "❌ Nenhum produto cadastrado.\n\n"
                "Primeiro crie um produto.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ NOVO PRODUTO",
                                callback_data=(
                                    "admin_novo_produto"
                                ),
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "⬅️ Voltar",
                                callback_data="admin_menu",
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

            botoes.append(
                [
                    InlineKeyboardButton(
                        f"📦 {nome[:40]}",
                        callback_data=(
                            f"admin_add_login_{produto_id}"
                        ),
                    )
                ]
            )

        botoes.append(
            [
                InlineKeyboardButton(
                    "⬅️ Voltar",
                    callback_data="admin_menu",
                )
            ]
        )

        await query.edit_message_text(
            "➕ *ADICIONAR CONTAS*\n\n"
            "Escolha o produto onde deseja "
            "adicionar as contas:",
            reply_markup=InlineKeyboardMarkup(
                botoes
            ),
            parse_mode="Markdown",
        )

        return

    # =====================================================
    # PRODUTO ESPECÍFICO
    # =====================================================

    if acao.startswith(
        "admin_produto_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_produto_",
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

        await admin_detalhes_produto(
            query,
            context,
            produto_id,
        )

        return

    # =====================================================
    # ADICIONAR LOGIN
    # =====================================================

    if acao.startswith(
        "admin_add_login_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_add_login_",
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

        await iniciar_adicionar_conta(
            query,
            context,
            produto_id,
        )

        return

    # =====================================================
    # VER LOGINS
    # =====================================================

    if acao.startswith(
        "admin_ver_logins_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_ver_logins_",
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

        await admin_ver_logins(
            query,
            produto_id,
        )

        return

    # =====================================================
    # ALTERAR PREÇO
    # =====================================================

    if acao.startswith(
        "admin_preco_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_preco_",
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

        await iniciar_alterar_preco(
            query,
            context,
            produto_id,
        )

        return

    # =====================================================
    # ALTERAR DURAÇÃO (DIAS)
    # =====================================================

    if acao.startswith(
        "admin_duracao_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_duracao_",
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

        await iniciar_alterar_duracao(
            query,
            context,
            produto_id,
        )

        return

    # =====================================================
    # DEFINIR CATEGORIA DE PRODUTO EXISTENTE
    # =====================================================

    if acao.startswith(
        "admin_definir_categoria_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_definir_categoria_",
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

        await iniciar_definir_categoria_produto(
            query,
            context,
            produto_id,
        )

        return

    if acao.startswith(
        "admin_set_categoria_"
    ):

        partes = acao.replace(
            "admin_set_categoria_",
            "",
            1,
        ).split("_")

        try:

            produto_id = int(partes[0])
            categoria_id = int(partes[1])

        except (ValueError, IndexError):

            await query.answer(
                "❌ Dados inválidos.",
                show_alert=True,
            )

            return

        await executar_definir_categoria_produto(
            query,
            context,
            produto_id,
            categoria_id,
        )

        return

    # =====================================================
    # IMAGEM DO PRODUTO (URL)
    # =====================================================

    if acao.startswith(
        "admin_imagem_produto_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_imagem_produto_",
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

        await iniciar_imagem_produto(
            query,
            context,
            produto_id,
        )

        return

    # =====================================================
    # EXCLUIR LOGIN
    # =====================================================

    if acao.startswith(
        "admin_excluir_login_"
    ):

        try:

            login_id = int(
                acao.replace(
                    "admin_excluir_login_",
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

        await confirmar_excluir_login(
            query,
            login_id,
        )

        return

    # =====================================================
    # CONFIRMAR EXCLUSÃO LOGIN
    # =====================================================

    if acao.startswith(
        "admin_confirmar_excluir_login_"
    ):

        try:

            login_id = int(
                acao.replace(
                    "admin_confirmar_excluir_login_",
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

        await executar_excluir_login(
            query,
            login_id,
        )

        return

    # =====================================================
    # EXCLUIR PRODUTO
    # =====================================================

    if acao.startswith(
        "admin_excluir_produto_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_excluir_produto_",
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

        await confirmar_excluir_produto(
            query,
            produto_id,
        )

        return

    # =====================================================
    # CONFIRMAR EXCLUSÃO PRODUTO
    # =====================================================

    if acao.startswith(
        "admin_confirmar_excluir_produto_"
    ):

        try:

            produto_id = int(
                acao.replace(
                    "admin_confirmar_excluir_produto_",
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

        await executar_excluir_produto(
            query,
            produto_id,
        )

        return


# =========================================================
# COMANDO /ADMIN
# =========================================================

async def comando_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.effective_user:

        return

    if not is_admin(
        update.effective_user.id
    ):

        await update.message.reply_text(
            "❌ Você não tem permissão para acessar "
            "o painel administrativo."
        )

        return

    await abrir_admin(
        update,
        context,
    )
