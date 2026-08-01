from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import conectar


def listar_produtos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, descricao, preco, estoque
        FROM produtos
        WHERE estoque > 0
        ORDER BY id
    """)

    produtos = cursor.fetchall()

    conn.close()

    return produtos


def menu_catalogo():
    produtos = listar_produtos()

    botoes = []

    if not produtos:
        botoes.append([
            InlineKeyboardButton(
                "📦 Estoque vazio",
                callback_data="sem_estoque"
            )
        ])
    else:
        for produto in produtos:
            produto_id = produto[0]
            nome = produto[1]
            preco = produto[3]

            botoes.append([
                InlineKeyboardButton(
                    f"🛒 {nome} - R$ {preco:.2f}",
                    callback_data=f"produto_{produto_id}"
                )
            ])

    botoes.append([
        InlineKeyboardButton(
            "⬅️ Voltar",
            callback_data="voltar_menu"
        )
    ])

    return InlineKeyboardMarkup(botoes)


def buscar_produto(produto_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, descricao, preco, estoque
        FROM produtos
        WHERE id = ?
    """, (produto_id,))

    produto = cursor.fetchone()

    conn.close()

    return produto
