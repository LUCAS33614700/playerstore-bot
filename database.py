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

    # -----------------------------------------------------
    # CATEGORIAS
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            emoji TEXT DEFAULT '📦',
            ordem INTEGER DEFAULT 0
        )
    """)

    # -----------------------------------------------------
    # CATEGORIAS PADRÃO
    # -----------------------------------------------------

    categorias = [
        ("Telas", "📺", 1),
        ("Contas", "🟢", 2),
        ("Outros", "📦", 3),
    ]

    for nome, emoji, ordem in categorias:

        cursor.execute("""
            INSERT OR IGNORE INTO categorias
            (
                nome,
                emoji,
                ordem
            )
            VALUES (?, ?, ?)
        """, (
            nome,
            emoji,
            ordem
        ))

    # -----------------------------------------------------
    # RELAÇÃO PRODUTO / CATEGORIA
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produto_categorias (
            produto_id INTEGER PRIMARY KEY,
            categoria_id INTEGER NOT NULL
        )
    """)

    # -----------------------------------------------------
    # ESTOQUE INDIVIDUAL DE LOGINS
    #
    # Cada registro representa UMA conta.
    #
    # dados:
    # email:senha
    #
    # ou:
    # email:senha | PIN:1234
    #
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            dados TEXT NOT NULL,
            status TEXT DEFAULT 'disponivel',
            usuario_id INTEGER,
            pedido_id INTEGER,
            vendido_em TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # COMMIT
    # -----------------------------------------------------

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
# CATEGORIAS
# =========================================================

def listar_categorias():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            emoji,
            ordem
        FROM categorias
        ORDER BY ordem, id
    """)

    categorias = cursor.fetchall()

    conn.close()

    return categorias


def buscar_categoria(
    categoria_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            emoji,
            ordem
        FROM categorias
        WHERE id = ?
    """, (
        categoria_id,
    ))

    categoria = cursor.fetchone()

    conn.close()

    return categoria


def buscar_categoria_por_nome(
    nome,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            emoji,
            ordem
        FROM categorias
        WHERE nome = ?
    """, (
        nome,
    ))

    categoria = cursor.fetchone()

    conn.close()

    return categoria


# =========================================================
# RELAÇÃO PRODUTO / CATEGORIA
# =========================================================

def definir_categoria_produto(
    produto_id,
    categoria_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO produto_categorias
        (
            produto_id,
            categoria_id
        )
        VALUES (?, ?)
    """, (
        produto_id,
        categoria_id,
    ))

    conn.commit()
    conn.close()


def consultar_categoria_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.id,
            c.nome,
            c.emoji,
            c.ordem
        FROM categorias c
        INNER JOIN produto_categorias pc
            ON pc.categoria_id = c.id
        WHERE pc.produto_id = ?
    """, (
        produto_id,
    ))

    categoria = cursor.fetchone()

    conn.close()

    return categoria


def listar_produtos_categoria(
    categoria_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.id,
            p.nome,
            p.descricao,
            p.preco,
            p.estoque
        FROM produtos p
        INNER JOIN produto_categorias pc
            ON pc.produto_id = p.id
        WHERE pc.categoria_id = ?
        AND p.estoque > 0
        ORDER BY p.id
    """, (
        categoria_id,
    ))

    produtos = cursor.fetchall()

    conn.close()

    return produtos


# =========================================================
# LOGINS
# =========================================================

def adicionar_login(
    produto_id,
    dados,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO logins
            (
                produto_id,
                dados,
                status
            )
            VALUES (?, ?, 'disponivel')
        """, (
            produto_id,
            dados,
        ))

        login_id = cursor.lastrowid

        cursor.execute("""
            UPDATE produtos
            SET estoque = estoque + 1
            WHERE id = ?
        """, (
            produto_id,
        ))

        conn.commit()

        return login_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


def adicionar_varios_logins(
    produto_id,
    lista_dados,
):

    conn = conectar()
    cursor = conn.cursor()

    adicionados = 0

    try:

        for dados in lista_dados:

            dados = str(
                dados
            ).strip()

            if not dados:
                continue

            cursor.execute("""
                INSERT INTO logins
                (
                    produto_id,
                    dados,
                    status
                )
                VALUES (?, ?, 'disponivel')
            """, (
                produto_id,
                dados,
            ))

            adicionados += 1

        if adicionados > 0:

            cursor.execute("""
                UPDATE produtos
                SET estoque = estoque + ?
                WHERE id = ?
            """, (
                adicionados,
                produto_id,
            ))

        conn.commit()

        return adicionados

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


def listar_logins_disponiveis(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            dados
        FROM logins
        WHERE produto_id = ?
        AND status = 'disponivel'
        ORDER BY id
    """, (
        produto_id,
    ))

    logins = cursor.fetchall()

    conn.close()

    return logins


def consultar_estoque_logins(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM logins
        WHERE produto_id = ?
        AND status = 'disponivel'
    """, (
        produto_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:

        return resultado[0]

    return 0


def retirar_login_disponivel(
    produto_id,
    usuario_id,
    pedido_id=None,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "BEGIN IMMEDIATE"
        )

        # -------------------------------------------------
        # BUSCAR UM LOGIN DISPONÍVEL
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                dados
            FROM logins
            WHERE produto_id = ?
            AND status = 'disponivel'
            ORDER BY id
            LIMIT 1
        """, (
            produto_id,
        ))

        login = cursor.fetchone()

        if not login:

            conn.rollback()
            conn.close()

            return None

        login_id = login[0]
        dados = login[1]

        # -------------------------------------------------
        # MARCAR COMO VENDIDO
        # -------------------------------------------------

        cursor.execute("""
            UPDATE logins
            SET status = 'vendido',
                usuario_id = ?,
                pedido_id = ?,
                vendido_em = CURRENT_TIMESTAMP
            WHERE id = ?
            AND status = 'disponivel'
        """, (
            usuario_id,
            pedido_id,
            login_id,
        ))

        if cursor.rowcount != 1:

            conn.rollback()
            conn.close()

            return None

        # -------------------------------------------------
        # DIMINUIR ESTOQUE
        # -------------------------------------------------

        cursor.execute("""
            UPDATE produtos
            SET estoque = CASE
                WHEN estoque > 0 THEN estoque - 1
                ELSE 0
            END
            WHERE id = ?
        """, (
            produto_id,
        ))

        conn.commit()
        conn.close()

        return {
            "id": login_id,
            "dados": dados,
        }

    except Exception:

        conn.rollback()
        conn.close()

        raise


# =========================================================
# COMPRA SEGURA DE LOGIN
#
# Esta função:
#
# 1. trava a transação;
# 2. verifica produto;
# 3. verifica saldo;
# 4. pega UM login disponível;
# 5. desconta o saldo;
# 6. cria o pedido;
# 7. marca o login como vendido;
# 8. diminui o estoque;
# 9. confirma tudo junto.
#
# Se alguma etapa falhar, nada é alterado.
# =========================================================

def processar_compra_login(
    usuario_id,
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "BEGIN IMMEDIATE"
        )

        # -------------------------------------------------
        # BUSCAR PRODUTO
        # -------------------------------------------------

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

        if not produto:

            conn.rollback()
            conn.close()

            return {
                "sucesso": False,
                "erro": "produto_nao_encontrado",
            }

        produto_id_db = produto[0]
        nome = produto[1]
        descricao = produto[2]
        preco = float(produto[3])
        estoque = int(produto[4])

        # -------------------------------------------------
        # BUSCAR SALDO
        # -------------------------------------------------

        cursor.execute("""
            SELECT saldo
            FROM usuarios
            WHERE id = ?
        """, (
            usuario_id,
        ))

        usuario = cursor.fetchone()

        if not usuario:

            conn.rollback()
            conn.close()

            return {
                "sucesso": False,
                "erro": "usuario_nao_encontrado",
            }

        saldo = float(
            usuario[0]
        )

        # -------------------------------------------------
        # VERIFICAR SALDO
        # -------------------------------------------------

        if saldo < preco:

            conn.rollback()
            conn.close()

            return {
                "sucesso": False,
                "erro": "saldo_insuficiente",
                "saldo": saldo,
                "preco": preco,
                "faltam": preco - saldo,
            }

        # -------------------------------------------------
        # BUSCAR LOGIN
        # -------------------------------------------------

        cursor.execute("""
            SELECT
                id,
                dados
            FROM logins
            WHERE produto_id = ?
            AND status = 'disponivel'
            ORDER BY id
            LIMIT 1
        """, (
            produto_id_db,
        ))

        login = cursor.fetchone()

        if not login:

            conn.rollback()
            conn.close()

            return {
                "sucesso": False,
                "erro": "login_indisponivel",
            }

        login_id = login[0]
        dados = login[1]

        # -------------------------------------------------
        # DESCONTAR SALDO
        # -------------------------------------------------

        cursor.execute("""
            UPDATE usuarios
            SET saldo = saldo - ?
            WHERE id = ?
            AND saldo >= ?
        """, (
            preco,
            usuario_id,
            preco,
        ))

        if cursor.rowcount != 1:

            conn.rollback()
            conn.close()

            return {
                "sucesso": False,
                "erro": "saldo_insuficiente",
            }

        # -------------------------------------------------
        # CRIAR PEDIDO
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO pedidos
            (
                usuario_id,
                produto_id,
                quantidade,
                valor,
                status
            )
            VALUES (?, ?, 1, ?, 'pago')
        """, (
            usuario_id,
            produto_id_db,
            preco,
        ))

        pedido_id = cursor.lastrowid

        # -------------------------------------------------
        # MARCAR LOGIN COMO VENDIDO
        # -------------------------------------------------

        cursor.execute("""
            UPDATE logins
            SET status = 'vendido',
                usuario_id = ?,
                pedido_id = ?,
                vendido_em = CURRENT_TIMESTAMP
            WHERE id = ?
            AND status = 'disponivel'
        """, (
            usuario_id,
            pedido_id,
            login_id,
        ))

        if cursor.rowcount != 1:

            conn.rollback()
            conn.close()

            return {
                "sucesso": False,
                "erro": "login_indisponivel",
            }

        # -------------------------------------------------
        # DIMINUIR ESTOQUE
        # -------------------------------------------------

        cursor.execute("""
            UPDATE produtos
            SET estoque = CASE
                WHEN estoque > 0 THEN estoque - 1
                ELSE 0
            END
            WHERE id = ?
            AND estoque > 0
        """, (
            produto_id_db,
        ))

        if cursor.rowcount != 1:

            conn.rollback()
            conn.close()

            return {
                "sucesso": False,
                "erro": "estoque_indisponivel",
            }

        # -------------------------------------------------
        # NOVO SALDO
        # -------------------------------------------------

        cursor.execute("""
            SELECT saldo
            FROM usuarios
            WHERE id = ?
        """, (
            usuario_id,
        ))

        novo_saldo_resultado = (
            cursor.fetchone()
        )

        novo_saldo = float(
            novo_saldo_resultado[0]
        )

        # -------------------------------------------------
        # CONFIRMAR TUDO
        # -------------------------------------------------

        conn.commit()
        conn.close()

        return {
            "sucesso": True,
            "pedido_id": pedido_id,
            "login_id": login_id,
            "dados": dados,
            "produto_id": produto_id_db,
            "nome": nome,
            "descricao": descricao,
            "preco": preco,
            "saldo_anterior": saldo,
            "novo_saldo": novo_saldo,
        }

    except Exception:

        conn.rollback()
        conn.close()

        raise


def consultar_login(
    login_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            produto_id,
            dados,
            status,
            usuario_id,
            pedido_id,
            vendido_em
        FROM logins
        WHERE id = ?
    """, (
        login_id,
    ))

    login = cursor.fetchone()

    conn.close()

    return login


def excluir_login(
    login_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            produto_id,
            status
        FROM logins
        WHERE id = ?
    """, (
        login_id,
    ))

    login = cursor.fetchone()

    if not login:

        conn.close()

        return False

    produto_id = login[0]
    status = login[1]

    cursor.execute("""
        DELETE FROM logins
        WHERE id = ?
    """, (
        login_id,
    ))

    excluido = (
        cursor.rowcount > 0
    )

    # -----------------------------------------------------
    # SE ESTAVA DISPONÍVEL, DIMINUI ESTOQUE
    # -----------------------------------------------------

    if excluido and status == "disponivel":

        cursor.execute("""
            UPDATE produtos
            SET estoque = CASE
                WHEN estoque > 0 THEN estoque - 1
                ELSE 0
            END
            WHERE id = ?
        """, (
            produto_id,
        ))

    conn.commit()
    conn.close()

    return excluido


def listar_logins_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            dados,
            status,
            usuario_id,
            pedido_id,
            vendido_em
        FROM logins
        WHERE produto_id = ?
        ORDER BY id
    """, (
        produto_id,
    ))

    logins = cursor.fetchall()

    conn.close()

    return logins


# =========================================================
# ESTATÍSTICAS DE LOGINS
# =========================================================

def contar_logins_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*)
        FROM logins
        WHERE produto_id = ?
    """, (
        produto_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return int(resultado[0])

    return 0


def contar_logins_vendidos(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*)
        FROM logins
        WHERE produto_id = ?
        AND status = 'vendido'
    """, (
        produto_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return int(resultado[0])

    return 0


# =========================================================
# PEDIDOS
# =========================================================

def listar_pedidos_usuario(
    user_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            produto_id,
            quantidade,
            valor,
            status
        FROM pedidos
        WHERE usuario_id = ?
        ORDER BY id DESC
    """, (
        user_id,
    ))

    pedidos = cursor.fetchall()

    conn.close()

    return pedidos


def consultar_pedido(
    pedido_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            usuario_id,
            produto_id,
            quantidade,
            valor,
            status
        FROM pedidos
        WHERE id = ?
    """, (
        pedido_id,
    ))

    pedido = cursor.fetchone()

    conn.close()

    return pedido


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

        if status == "pago":

            conn.rollback()
            conn.close()

            return None

        if status != "pendente":

            conn.rollback()
            conn.close()

            return None

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
