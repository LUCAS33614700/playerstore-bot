from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import conectar


# =========================================================
# PRODUTOS PADRÃO
# =========================================================
#
# Os produtos abaixo serão cadastrados automaticamente
# caso ainda não existam no banco de dados.
#
# estoque = quantidade disponível
#
# Você pode alterar nome, descrição, preço e estoque aqui.
# =========================================================

PRODUTOS_PADRAO = [

    {
        "nome": "📺 TELA DISNEY PADRÃO COM ANUNCIO",
        "descricao": (
            "Disney+ padrão com anúncio\n"
            "Duração: 30 dias"
        ),
        "preco": 3.00,
        "estoque": 100,
    },

    {
        "nome": "📺 TELA GLOBO PLAY + CANAIS + TELECINE",
        "descricao": (
            "Globo Play + Canais + Telecine\n"
            "Duração: 30 dias"
        ),
        "preco": 6.00,
        "estoque": 100,
    },

    {
        "nome": "📺 TELA MAX BASICA COM ANUNCIO",
        "descricao": (
            "Max básica com anúncio\n"
            "Duração: 30 dias"
        ),
        "preco": 3.00,
        "estoque": 100,
    },

    {
        "nome": "🎞️ TELA MUBI 30 DIAS",
        "descricao": (
            "MUBI\n"
            "Duração: 30 dias"
        ),
        "preco": 3.00,
        "estoque": 100,
    },

    {
        "nome": "🔴 TELA NETFLIX 4K PRIVADA COM PIN",
        "descricao": (
            "Netflix 4K privada com PIN\n"
            "Duração: 30 dias"
        ),
        "preco": 8.00,
        "estoque": 100,
    },

]


# =========================================================
# CADASTRAR PRODUTOS AUTOMATICAMENTE
# =========================================================

def cadastrar_produtos_automaticamente():

    conn = conectar()
    cursor = conn.cursor()

    cadastrados = 0

    for produto in PRODUTOS_PADRAO:

        nome = produto["nome"]
        descricao = produto["descricao"]
        preco = produto["preco"]
        estoque = produto["estoque"]

        # -------------------------------------------------
        # Verifica se o produto já existe
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Se já existe, não cadastra novamente
        # -------------------------------------------------

        if existente:

            continue

        # -------------------------------------------------
        # Cadastra produto
        # -------------------------------------------------

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
                preco,
                estoque,
            ),
        )

        cadastrados += 1

    conn.commit()
    conn.close()

    if cadastrados > 0:

        print(
            f"📦 {cadastrados} produto(s) "
            "cadastrado(s) automaticamente."
        )

    else:

        print(
            "📦 Produtos já cadastrados."
        )


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
# MENU DO CATÁLOGO
# =========================================================

def menu_catalogo():

    # Garante que os produtos existam
    cadastrar_produtos_automaticamente()

    produtos = listar_produtos()

    botoes = []

    # -----------------------------------------------------
    # ESTOQUE VAZIO
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
            preco = produto[3]

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
