import sqlite3

from config import DATABASE_NAME


# =========================================================
# CONEXÃO
# =========================================================

def conectar():

    return sqlite3.connect(
        DATABASE_NAME
    )


# =========================================================
# CRIAR TABELAS
# =========================================================

def criar_tabelas():

    conn = conectar()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # USUÁRIOS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            nome TEXT,
            username TEXT,
            saldo REAL DEFAULT 0
        )
    """)

    # -----------------------------------------------------
    # PRODUTOS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            estoque INTEGER DEFAULT 0
        )
    """)

    # -----------------------------------------------------
    # PEDIDOS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # PAGAMENTOS PIX
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            pushinpay_id TEXT UNIQUE,
            status TEXT DEFAULT 'pendente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# USUÁRIOS
# =========================================================

def criar_usuario(
    user_id,
    nome,
    username,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO usuarios
        (
            id,
            nome,
            username,
            saldo
        )
        VALUES (?, ?, ?, 0)
    """, (
        user_id,
        nome,
        username,
    ))

    cursor.execute("""
        UPDATE usuarios
        SET nome = ?,
            username = ?
        WHERE id = ?
    """, (
        nome,
        username,
        user_id,
    ))

    conn.commit()
    conn.close()


def consultar_usuario(
    user_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM usuarios
        WHERE id = ?
        """,
        (
            user_id,
        ),
    )

    usuario = cursor.fetchone()

    conn.close()

    return usuario


def consultar_saldo(
    user_id,
):

    usuario = consultar_usuario(
        user_id
    )

    if usuario:

        return float(
            usuario[3]
        )

    return 0.0


# =========================================================
# SALDO
# =========================================================

def adicionar_saldo(
    user_id,
    valor,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET saldo = saldo + ?
        WHERE id = ?
    """, (
        valor,
        user_id,
    ))

    alterado = (
        cursor.rowcount > 0
    )

    conn.commit()
    conn.close()

    return alterado


def retirar_saldo(
    user_id,
    valor,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET saldo = saldo - ?
        WHERE id = ?
        AND saldo >= ?
    """, (
        valor,
        user_id,
        valor,
        ))

    alterado = (
        cursor.rowcount > 0
    )

    conn.commit()
    conn.close()

    return alterado


# =========================================================
# PRODUTOS
# =========================================================

def adicionar_produto(
    nome,
    descricao,
    preco,
    estoque,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO produtos
        (
            nome,
            descricao,
            preco,
            estoque
        )
        VALUES (?, ?, ?, ?)
    """, (
        nome,
        descricao,
        preco,
        estoque,
    ))

    conn.commit()

    produto_id = (
        cursor.lastrowid
    )

    conn.close()

    return produto_id


def listar_todos_produtos():

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
        ORDER BY id
    """)

    produtos = cursor.fetchall()

    conn.close()

    return produtos


def excluir_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

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
    conn.close()

    return excluido


def atualizar_estoque(
    produto_id,
    estoque,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE produtos
        SET estoque = ?
        WHERE id = ?
    """, (
        estoque,
        produto_id,
    ))

    alterado = (
        cursor.rowcount > 0
    )

    conn.commit()
    conn.close()

    return alterado


# =========================================================
# PAGAMENTOS
# =========================================================

def criar_pagamento(
    usuario_id,
    valor,
    pushinpay_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO pagamentos
        (
            usuario_id,
            valor,
            pushinpay_id,
            status
        )
        VALUES (?, ?, ?, 'pendente')
    """, (
        usuario_id,
        valor,
        pushinpay_id,
    ))

    conn.commit()

    pagamento_id = (
        cursor.lastrowid
    )

    conn.close()

    return pagamento_id


def consultar_pagamento(
    pushinpay_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            usuario_id,
            valor,
            pushinpay_id,
            status,
            criado_em
        FROM pagamentos
        WHERE pushinpay_id = ?
    """, (
        pushinpay_id,
    ))

    pagamento = cursor.fetchone()

    conn.close()

    return pagamento


def atualizar_status_pagamento(
    pushinpay_id,
    status,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE pagamentos
        SET status = ?
        WHERE pushinpay_id = ?
        AND status = 'pendente'
    """, (
        status,
        pushinpay_id,
    ))

    alterado = (
        cursor.rowcount > 0
    )

    conn.commit()
    conn.close()

    return alterado


# =========================================================
# PAGAMENTOS PENDENTES
# =========================================================

def listar_pagamentos_pendentes():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            usuario_id,
            valor,
            pushinpay_id,
            status,
            criado_em
        FROM pagamentos
        WHERE status = 'pendente'
        ORDER BY id ASC
    """)

    pagamentos = (
        cursor.fetchall()
    )

    conn.close()

    return pagamentos


# =========================================================
# CONFIRMAR PAGAMENTO COM SEGURANÇA
#
# Esta função faz:
#
# 1. Localiza o PIX pendente
# 2. Confirma que ainda está pendente
# 3. Marca como pago
# 4. Adiciona o saldo
# 5. Tudo na mesma transação SQLite
#
# Assim o mesmo PIX não pode gerar
# dois créditos.
# =========================================================

def processar_pagamento_pago(
    pushinpay_id,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "BEGIN IMMEDIATE"
        )

        cursor.execute("""
            SELECT
                usuario_id,
                valor,
                status
            FROM pagamentos
            WHERE pushinpay_id = ?
        """, (
            pushinpay_id,
        ))

        pagamento = (
            cursor.fetchone()
        )

        if not pagamento:

            conn.rollback()
            conn.close()

            return None

        usuario_id = pagamento[0]
        valor = float(
            pagamento[1]
        )
        status = pagamento[2]

        # Já processado
        if status == "pago":

            conn.rollback()
            conn.close()

            return None

        # Só processa pagamento pendente
        if status != "pendente":

            conn.rollback()
            conn.close()

            return None

        # Marca como pago
        cursor.execute("""
            UPDATE pagamentos
            SET status = 'pago'
            WHERE pushinpay_id = ?
            AND status = 'pendente'
        """, (
            pushinpay_id,
        ))

        if cursor.rowcount != 1:

            conn.rollback()
            conn.close()

            return None

        # Adiciona saldo
        cursor.execute("""
            UPDATE usuarios
            SET saldo = saldo + ?
            WHERE id = ?
        """, (
            valor,
            usuario_id,
        ))

        if cursor.rowcount != 1:

            conn.rollback()
            conn.close()

            return None

        conn.commit()
        conn.close()

        return {
            "usuario_id": usuario_id,
            "valor": valor,
        }

    except Exception:

        conn.rollback()
        conn.close()

        raise


# =========================================================
# PAGAMENTOS DO USUÁRIO
# =========================================================

def listar_pagamentos_usuario(
    user_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            valor,
            pushinpay_id,
            status,
            criado_em
        FROM pagamentos
        WHERE usuario_id = ?
        ORDER BY id DESC
    """, (
        user_id,
    ))

    pagamentos = (
        cursor.fetchall()
    )

    conn.close()

    return pagamentos
