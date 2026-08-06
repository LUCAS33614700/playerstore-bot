from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import (
    conectar,
    listar_categorias,
    listar_produtos_categoria,
)


# =========================================================
# PRODUTOS PADRÃO
# =========================================================
#
# Estes produtos serão cadastrados automaticamente
# caso ainda não existam no banco.
#
# Para alterar preço ou estoque posteriormente,
# use o sistema de estoque/admin.
#
# IMPORTANTE: produtos cadastrados automaticamente aqui
# não têm categoria definida. Use o painel admin para
# associá-los a uma categoria (Telas, Contas, Outros),
# ou eles não aparecerão no menu por categoria.
# =========================================================

PRODUTOS_PADRAO = [

    {
        "nome": "📺 TELA DISNEY PADRÃO COM ANUNCIO",
        "descricao": "Acesso Disney+ - duração de 30 dias.",
        "preco": 3.00,
        "estoque": 0,
    },

    {
        "nome": "📺 TELA GLOBO PLAY + CANAIS + TELECINE",
        "descricao": "Acesso Globoplay + canais + Telecine - 30 dias.",
        "preco": 6.00,
        "estoque": 0,
    },

    {
        "nome": "📺 TELA MAX BASICA COM ANUNCIO",
        "descricao": "Acesso Max básico com anúncio - 30 dias.",
        "preco": 3.00,
        "estoque": 0,
    },

    {
        "nome": "🗃️ TELA MUBI 30 DIAS",
        "descricao": "Acesso MUBI - duração de 30 dias.",
        "preco": 3.00,
        "estoque": 0,
    },

    {
        "nome": "🔴 TELA NETFLIX 4K PRIVADA COM PIN",
        "descricao": "Acesso Netflix 4K privada com PIN - 30 dias.",
        "preco": 8.00,
        "estoque": 0,
    },
]


# =========================================================
# CADASTRAR PRODUTOS AUTOMATICAMENTE
# =========================================================

def cadastrar_produtos_automaticamente():

    conn = conectar()
    cursor = conn.cursor()

    try:

        for produto in PRODUTOS_PADRAO:

            cursor.execute(
                """
                SELECT id
                FROM produtos
                WHERE nome = ?
                """,
                (
                    produto["nome"],
                ),
            )

            existente = cursor.fetchone()

            # ---------------------------------------------
            # NÃO CADASTRA DUPLICADO
            # ---------------------------------------------

            if existente:
                continue

            cursor.execute(
                """
                INSERT INTO produtos
                (
                    nome,
                    descricao,
                    preco,
                    estoque
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    produto["nome"],
                    produto["descricao"],
                    produto["preco"],
                    produto["estoque"],
                ),
            )

            print(
                f"✅ Produto cadastrado: "
                f"{produto['nome']}"
            )

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# =========================================================
# LISTAR PRODUTOS
# =========================================================

def listar_produtos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            nome,
            descricao,
            preco,
            estoque
        FROM produtos
        WHERE estoque > 0
        ORDER BY id
        """
    )

    produtos = cursor.fetchall()

    conn.close()

    return produtos


# =========================================================
# MENU DE CATEGORIAS
# =========================================================

def menu_categorias():

    # Garante que os produtos padrão existam
    cadastrar_produtos_automaticamente()

    categorias = listar_categorias()

    botoes = []

    if not categorias:

        botoes.append(
            [
                InlineKeyboardButton(
                    "📦 Nenhuma categoria cadastrada",
                    callback_data="sem_estoque",
                )
            ]
        )

    else:

        linha_atual = []

        for categoria in categorias:

            categoria_id = categoria[0]
            nome = categoria[1]
            emoji = categoria[2]

            produtos_categoria = listar_produtos_categoria(
                categoria_id
            )

            quantidade = len(
                produtos_categoria
            )

            linha_atual.append(
                InlineKeyboardButton(
                    f"{emoji} {nome} ({quantidade})",
                    callback_data=(
                        f"categoria_{categoria_id}"
                    ),
                )
            )

            # Duas categorias por linha, igual ao layout
            # de referência (Telas | Contas / Outros).
            if len(linha_atual) == 2:

                botoes.append(linha_atual)
                linha_atual = []

        if linha_atual:

            botoes.append(linha_atual)

    botoes.append(
        [
            InlineKeyboardButton(
                "↩️ Voltar ao menu",
                callback_data="voltar_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(
        botoes
    )


# =========================================================
# TEXTO DE APRESENTAÇÃO DO CATÁLOGO
# =========================================================

def texto_selecionar_categoria():

    categorias = listar_categorias()

    linhas_categorias = "\n".join(
        f"{categoria[2]} {categoria[1]}"
        for categoria in categorias
    )

    texto = (
        "✨ *Selecione a categoria de serviços:* ✨\n"
        "👉 Escolha uma opção abaixo para visualizar "
        "os logins disponíveis!\n\n"
        f"{linhas_categorias}\n\n"
        "🎁 _Aproveite também nossos Gift Cards "
        "exclusivos!_"
    )

    return texto


# =========================================================
# MENU DE PRODUTOS DE UMA CATEGORIA
# =========================================================

def menu_produtos_categoria(
    categoria_id,
):

    produtos = listar_produtos_categoria(
        categoria_id
    )

    botoes = []

    if not produtos:

        botoes.append(
            [
                InlineKeyboardButton(
                    "📦 Sem produtos nesta categoria",
                    callback_data="sem_estoque",
                )
            ]
        )

    else:

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
                "⬅️ Voltar às categorias",
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

    return InlineKeyboardMarkup(
        botoes
    )


# =========================================================
# MENU DO CATÁLOGO (LISTA GERAL - MANTIDO PARA COMPATIBILIDADE)
# =========================================================

def menu_catalogo():

    # Garante que os produtos padrão existam
    cadastrar_produtos_automaticamente()

    produtos = listar_produtos()

    botoes = []

    # -----------------------------------------------------
    # SEM ESTOQUE
    # -----------------------------------------------------

    if not produtos:

        botoes.append(
            [
                InlineKeyboardButton(
                    "📦 Estoque vazio",
                    callback_data="sem_estoque",
                )
            ]
        )

    # -----------------------------------------------------
    # PRODUTOS
    # -----------------------------------------------------

    else:

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

    # -----------------------------------------------------
    # VOLTAR
    # -----------------------------------------------------

    botoes.append(
        [
            InlineKeyboardButton(
                "⬅️ Voltar",
                callback_data="voltar_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(
        botoes
    )


# =========================================================
# BUSCAR PRODUTO
# =========================================================

def buscar_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            nome,
            descricao,
            preco,
            estoque
        FROM produtos
        WHERE id = ?
        """,
        (
            produto_id,
        ),
    )

    produto = cursor.fetchone()

    conn.close()

    return produto


# =========================================================
# CADASTRAR UM PRODUTO
# =========================================================

def cadastrar_produto(
    nome,
    descricao,
    preco,
    estoque,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        # Verifica se já existe
        cursor.execute(
            """
            SELECT id
            FROM produtos
            WHERE nome = ?
            """,
            (
                nome,
            ),
        )

        existente = cursor.fetchone()

        if existente:

            conn.close()

            return existente[0]

        # Cadastra
        cursor.execute(
            """
            INSERT INTO produtos
            (
                nome,
                descricao,
                preco,
                estoque
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                nome,
                descricao,
                float(preco),
                int(estoque),
            ),
        )

        produto_id = cursor.lastrowid

        conn.commit()

        return produto_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# =========================================================
# ADICIONAR ESTOQUE
# =========================================================

def adicionar_estoque(
    produto_id,
    quantidade,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            UPDATE produtos
            SET estoque = estoque + ?
            WHERE id = ?
            """,
            (
                int(quantidade),
                produto_id,
            ),
        )

        alterado = (
            cursor.rowcount > 0
        )

        conn.commit()

        return alterado

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# =========================================================
# ALTERAR PREÇO
# =========================================================

def alterar_preco(
    produto_id,
    novo_preco,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            UPDATE produtos
            SET preco = ?
            WHERE id = ?
            """,
            (
                float(novo_preco),
                produto_id,
            ),
        )

        alterado = (
            cursor.rowcount > 0
        )

        conn.commit()

        return alterado

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# =========================================================
# EXCLUIR PRODUTO
# =========================================================

def excluir_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            DELETE FROM produtos
            WHERE id = ?
            """,
            (
                produto_id,
            ),
        )

        excluido = (
            cursor.rowcount > 0
        )

        conn.commit()

        return excluido

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# =========================================================
# INICIALIZAÇÃO
# =========================================================

def inicializar_catalogo():

    cadastrar_produtos_automaticamente()

    print(
        "🛒 Catálogo inicializado."
    )
