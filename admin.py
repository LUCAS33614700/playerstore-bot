from urllib.parse import urlparse

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

    botoes = [

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

    texto = (
        "📦 *GERENCIAR PRODUTO*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ *Produto:* {nome}\n"
        f"💰 *Preço:* R$ {float(preco):.2f}\n"
        f"📦 *Estoque:* {estoque}\n"
        f"🔐 *Contas disponíveis:* {estoque_real}\n"
        f"🗂️ *Categoria:* {texto_categoria}\n"
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
        "➕ *ADICIONAR CONTA AO ESTOQUE*\n\n"
        f"📦 *Produto:* {nome}\n\n"
        "Envie agora os dados da conta.\n\n"
        "Você pode enviar, por exemplo:\n\n"
        "`email@gmail.com:senha123`\n\n"
        "Ou:\n\n"
        "`Email: email@gmail.com`\n"
        "`Senha: senha123`\n"
        "`PIN: 1234`\n\n"
        "Tudo que você enviar será salvo "
        "como uma única conta.\n\n"
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

        login_id = adicionar_login(
            produto_id,
            texto,
        )

        estoque = consultar_estoque_logins(
            produto_id
        )

        nome = produto[1]

        limpar_estado(context)

        await update.message.reply_text(
            "✅ *CONTA ADICIONADA!*\n\n"
            f"📦 *Produto:* {nome}\n"
            f"🆔 *ID da conta:* `{login_id}`\n"
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
