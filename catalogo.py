from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from database import conectar


# =========================================================
# LISTAR PRODUTOS
# =========================================================

def listar_produtos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            descricao,
            preco,
            estoque
        FROM produtos
        WHERE estoque > 0
        ORDER BY id
    """)

    produtos = cursor.fetchall()

    conn.close()

    return produtos


# =========================================================
# MENU DO CATÁLOGO
# =========================================================

def menu_catalogo():

    produtos = listar_produtos()

    botoes = []

    # -----------------------------------------------------
    # ESTOQUE VAZIO
    # -----------------------------------------------------

    if not produtos:

        botoes.append([
            InlineKeyboardButton(
                "📦 Estoque vazio",
                callback_data="sem_estoque"
            )
        ])

    # -----------------------------------------------------
    # PRODUTOS
    # -----------------------------------------------------

    else:

        for produto in produtos:

            produto_id = produto[0]
            nome = produto[1]
            preco = float(produto[3])

            botoes.append([
                InlineKeyboardButton(
                    f"🛒 {nome} - R${preco:.2f}",
                    callback_data=(
                        f"produto_{produto_id}"
                    )
                )
            ])

    # -----------------------------------------------------
    # VOLTAR
    # -----------------------------------------------------

    botoes.append([
        InlineKeyboardButton(
            "⬅️ Voltar",
            callback_data="voltar_menu"
        )
    ])

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

    cursor.execute("""
        SELECT
            id,
            nome,
            descricao,
            preco,
            estoque
        FROM produtos
        WHERE id = ?
    """, (
        produto_id,
    ))

    produto = cursor.fetchone()

    conn.close()

    return produto


# =========================================================
# VERIFICAR ESTOQUE
# =========================================================

def produto_disponivel(
    produto_id,
):

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        return False

    estoque = produto[4]

    return estoque > 0


# =========================================================
# PREÇO DO PRODUTO
# =========================================================

def obter_preco_produto(
    produto_id,
):

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        return None

    return float(
        produto[3]
    )


# =========================================================
# QUANTIDADE DISPONÍVEL
# =========================================================

def obter_estoque_produto(
    produto_id,
):

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        return 0

    return int(
        produto[4]
    )


# =========================================================
# NOME DO PRODUTO
# =========================================================

def obter_nome_produto(
    produto_id,
):

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        return None

    return produto[1]


# =========================================================
# DESCRIÇÃO DO PRODUTO
# =========================================================

def obter_descricao_produto(
    produto_id,
):

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        return None

    return produto[2]


# =========================================================
# DADOS COMPLETOS DO PRODUTO
# =========================================================

def dados_produto(
    produto_id,
):

    produto = buscar_produto(
        produto_id
    )

    if not produto:

        return None

    return {
        "id": produto[0],
        "nome": produto[1],
        "descricao": produto[2],
        "preco": float(produto[3]),
        "estoque": int(produto[4]),
    }
