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

    texto = (
        "📦 *GERENCIAR PRODUTO*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ *Produto:* {nome}\n"
        f"💰 *Preço:* R$ {float(preco):.2f}\n"
        f"📦 *Estoque:* {estoque}\n"
        f"🔐 *Contas disponíveis:* {estoque_real}\n"
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

        from database import alterar_preco

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
    # PREÇO NOVO PRODUTO
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
            "✅ *PRODUTO CADASTRADO!*\n\n"
            f"📦 {nome}\n"
            f"💰 R$ {preco:.2f}\n"
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
