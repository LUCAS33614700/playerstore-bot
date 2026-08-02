import sqlite3

from config import DATABASE_NAME


def conectar():
    return sqlite3.connect(DATABASE_NAME)


# =========================================================
# CRIAR TABELAS
# =========================================================

def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            nome TEXT,
            username TEXT,
            saldo REAL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            estoque INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER DEFAULT 1,
            valor REAL NOT NULL,
            status TEXT DEFAULT 'pendente'
        )
    """)

    # =====================================================
    # PAGAMENTOS ASAAS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            asaas_id TEXT,
            status TEXT DEFAULT 'pendente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# USUÁRIOS
# =========================================================

def criar_usuario(user_id, nome, username):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO usuarios
        (id, nome, username, saldo)
        VALUES (?, ?, ?, 0)
    """, (user_id, nome, username))

    conn.commit()
    conn.close()


def consultar_usuario(user_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM usuarios WHERE id = ?",
        (user_id,)
    )

    usuario = cursor.fetchone()

    conn.close()

    return usuario


def consultar_saldo(user_id):
    usuario = consultar_usuario(user_id)

    if usuario:
        return usuario[3]

    return 0.0


# =========================================================
# SALDO
# =========================================================

def adicionar_saldo(user_id, valor):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET saldo = saldo + ?
        WHERE id = ?
    """, (valor, user_id))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def retirar_saldo(user_id, valor):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET saldo = saldo - ?
        WHERE id = ?
        AND saldo >= ?
    """, (valor, user_id, valor))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


# =========================================================
# PRODUTOS
# =========================================================

def adicionar_produto(nome, descricao, preco, estoque):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO produtos
        (nome, descricao, preco, estoque)
        VALUES (?, ?, ?, ?)
    """, (nome, descricao, preco, estoque))

    conn.commit()

    produto_id = cursor.lastrowid

    conn.close()

    return produto_id


def listar_todos_produtos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, descricao, preco, estoque
        FROM produtos
        ORDER BY id
    """)

    produtos = cursor.fetchall()

    conn.close()

    return produtos


def excluir_produto(produto_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM produtos WHERE id = ?",
        (produto_id,)
    )

    excluido = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return excluido


def atualizar_estoque(produto_id, estoque):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE produtos
        SET estoque = ?
        WHERE id = ?
    """, (estoque, produto_id))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


# =========================================================
# PAGAMENTOS ASAAS
# =========================================================

def criar_pagamento(
    usuario_id,
    valor,
    asaas_id
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO pagamentos
        (
            usuario_id,
            valor,
            asaas_id,
            status
        )
        VALUES (?, ?, ?, 'pendente')
    """, (
        usuario_id,
        valor,
        asaas_id
    ))

    conn.commit()

    pagamento_id = cursor.lastrowid

    conn.close()

    return pagamento_id


def consultar_pagamento(asaas_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            usuario_id,
            valor,
            asaas_id,
            status,
            criado_em
        FROM pagamentos
        WHERE asaas_id = ?
    """, (asaas_id,))

    pagamento = cursor.fetchone()

    conn.close()

    return pagamento


def atualizar_status_pagamento(
    asaas_id,
    status
):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE pagamentos
        SET status = ?
        WHERE asaas_id = ?
    """, (
        status,
        asaas_id
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def listar_pagamentos_usuario(user_id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            valor,
            asaas_id,
            status,
            criado_em
        FROM pagamentos
        WHERE usuario_id = ?
        ORDER BY id DESC
    """, (user_id,))

    pagamentos = cursor.fetchall()

    conn.close()

    return pagamentos
