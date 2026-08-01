import sqlite3

from config import DATABASE_NAME


def conectar():
    return sqlite3.connect(DATABASE_NAME)


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

    conn.commit()
    conn.close()


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


def adicionar_saldo(user_id, valor):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET saldo = saldo + ?
        WHERE id = ?
    """, (valor, user_id))

    conn.commit()
    conn.close()


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
