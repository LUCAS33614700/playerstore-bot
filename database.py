import sqlite3

from config import DATABASE_NAME


# =========================================================
# CONEXÃO
# =========================================================

def conectar():
    return sqlite3.connect(DATABASE_NAME)


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
    # LOGINS
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
    # CONFIGURAÇÕES (chave/valor)
    # -----------------------------------------------------
    # Usada para guardar coisas ajustáveis pelo admin sem
    # precisar mexer no código, como a imagem do catálogo.

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    # -----------------------------------------------------
    # CARRINHO
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS carrinho_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER DEFAULT 1
        )
    """)

    # -----------------------------------------------------
    # IMAGEM POR PRODUTO (para resultados de busca inline)
    # -----------------------------------------------------
    # Migração segura: SQLite não tem "ADD COLUMN IF NOT
    # EXISTS", então tentamos adicionar e ignoramos o erro
    # se a coluna já existir.

    try:
        cursor.execute("""
            ALTER TABLE produtos
            ADD COLUMN imagem_url TEXT
        """)
    except sqlite3.OperationalError:
        pass

    # -----------------------------------------------------
    # XP / NÍVEL (preparado para uso futuro)
    # -----------------------------------------------------

    try:
        cursor.execute("""
            ALTER TABLE usuarios
            ADD COLUMN xp INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE usuarios
            ADD COLUMN nivel INTEGER DEFAULT 1
        """)
    except sqlite3.OperationalError:
        pass

    # -----------------------------------------------------
    # TÓPICOS DE SUPORTE (helpdesk em grupo com tópicos)
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suporte_topicos (
            usuario_id INTEGER PRIMARY KEY,
            topico_id INTEGER NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# CONFIGURAÇÕES (CHAVE / VALOR)
# =========================================================

def definir_configuracao(
    chave,
    valor,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO configuracoes
        (
            chave,
            valor
        )
        VALUES (?, ?)
        ON CONFLICT(chave)
        DO UPDATE SET valor = excluded.valor
    """, (
        chave,
        valor,
    ))

    conn.commit()
    conn.close()


def obter_configuracao(
    chave,
    padrao=None,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT valor
        FROM configuracoes
        WHERE chave = ?
    """, (
        chave,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return resultado[0]

    return padrao


def remover_configuracao(
    chave,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM configuracoes
        WHERE chave = ?
    """, (
        chave,
    ))

    removido = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return removido


# =========================================================
# CARRINHO
# =========================================================

def adicionar_item_carrinho(
    usuario_id,
    produto_id,
    quantidade=1,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                id,
                quantidade
            FROM carrinho_itens
            WHERE usuario_id = ?
            AND produto_id = ?
        """, (
            usuario_id,
            produto_id,
        ))

        existente = cursor.fetchone()

        if existente:

            item_id = existente[0]

            nova_quantidade = (
                int(existente[1])
                + int(quantidade)
            )

            cursor.execute("""
                UPDATE carrinho_itens
                SET quantidade = ?
                WHERE id = ?
            """, (
                nova_quantidade,
                item_id,
            ))

        else:

            cursor.execute("""
                INSERT INTO carrinho_itens
                (
                    usuario_id,
                    produto_id,
                    quantidade
                )
                VALUES (?, ?, ?)
            """, (
                usuario_id,
                produto_id,
                int(quantidade),
            ))

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


def listar_itens_carrinho(
    usuario_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ci.id,
            ci.produto_id,
            p.nome,
            p.preco,
            ci.quantidade
        FROM carrinho_itens ci
        INNER JOIN produtos p
            ON p.id = ci.produto_id
        WHERE ci.usuario_id = ?
        ORDER BY ci.id
    """, (
        usuario_id,
    ))

    itens = cursor.fetchall()

    conn.close()

    return itens


def remover_item_carrinho(
    item_id,
    usuario_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM carrinho_itens
        WHERE id = ?
        AND usuario_id = ?
    """, (
        item_id,
        usuario_id,
    ))

    removido = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return removido


def limpar_carrinho(
    usuario_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM carrinho_itens
        WHERE usuario_id = ?
    """, (
        usuario_id,
    ))

    conn.commit()
    conn.close()


def contar_itens_carrinho(
    usuario_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(quantidade), 0)
        FROM carrinho_itens
        WHERE usuario_id = ?
    """, (
        usuario_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return int(resultado[0])

    return 0


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


def consultar_usuario(user_id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nome,
            username,
            saldo
        FROM usuarios
        WHERE id = ?
    """, (
        user_id,
    ))

    usuario = cursor.fetchone()

    conn.close()

    return usuario


def consultar_saldo(user_id):

    usuario = consultar_usuario(user_id)

    if usuario:
        return float(usuario[3])

    return 0.0


def contar_compras_usuario(
    user_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM pedidos
        WHERE usuario_id = ?
        AND status = 'pago'
    """, (
        user_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return int(resultado[0])

    return 0


def salvar_topico_suporte(
    usuario_id,
    topico_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO suporte_topicos
        (
            usuario_id,
            topico_id
        )
        VALUES (?, ?)
        ON CONFLICT(usuario_id)
        DO UPDATE SET topico_id = excluded.topico_id
    """, (
        usuario_id,
        topico_id,
    ))

    conn.commit()
    conn.close()


def obter_topico_suporte(
    usuario_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT topico_id
        FROM suporte_topicos
        WHERE usuario_id = ?
    """, (
        usuario_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return int(resultado[0])

    return None


def obter_usuario_por_topico(
    topico_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT usuario_id
        FROM suporte_topicos
        WHERE topico_id = ?
    """, (
        topico_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return int(resultado[0])

    return None


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
        float(valor),
        user_id,
    ))

    alterado = cursor.rowcount > 0

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
        float(valor),
        user_id,
        float(valor),
    ))

    alterado = cursor.rowcount > 0

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
    estoque=0,
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
        float(preco),
        int(estoque),
    ))

    produto_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return produto_id


# Compatibilidade com o admin.py
def cadastrar_produto(
    nome,
    descricao,
    preco,
    estoque=0,
):

    return adicionar_produto(
        nome,
        descricao,
        preco,
        estoque,
    )


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


def buscar_produto(produto_id):

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


def alterar_preco(
    produto_id,
    preco,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE produtos
        SET preco = ?
        WHERE id = ?
    """, (
        float(preco),
        produto_id,
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def excluir_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "BEGIN IMMEDIATE"
        )

        cursor.execute("""
            SELECT id
            FROM produtos
            WHERE id = ?
        """, (
            produto_id,
        ))

        produto = cursor.fetchone()

        if not produto:

            conn.rollback()
            conn.close()

            return False

        # Remove relação com categoria
        cursor.execute("""
            DELETE FROM produto_categorias
            WHERE produto_id = ?
        """, (
            produto_id,
        ))

        # Remove logins do produto
        cursor.execute("""
            DELETE FROM logins
            WHERE produto_id = ?
        """, (
            produto_id,
        ))

        # Remove produto
        cursor.execute("""
            DELETE FROM produtos
            WHERE id = ?
        """, (
            produto_id,
        ))

        excluido = cursor.rowcount > 0

        if not excluido:

            conn.rollback()
            conn.close()

            return False

        conn.commit()
        conn.close()

        return True

    except Exception:

        conn.rollback()
        conn.close()

        raise


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
        int(estoque),
        produto_id,
    ))

    alterado = cursor.rowcount > 0

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


def buscar_categoria(categoria_id):

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


def buscar_categoria_por_nome(nome):

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


def buscar_produtos_por_nome(
    termo,
):

    conn = conectar()
    cursor = conn.cursor()

    termo_like = f"%{termo}%"

    cursor.execute("""
        SELECT
            id,
            nome,
            descricao,
            preco,
            estoque
        FROM produtos
        WHERE nome LIKE ?
        COLLATE NOCASE
        AND estoque > 0
        ORDER BY nome
    """, (
        termo_like,
    ))

    produtos = cursor.fetchall()

    conn.close()

    return produtos


def obter_imagem_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT imagem_url
        FROM produtos
        WHERE id = ?
    """, (
        produto_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return resultado[0]

    return None


def definir_imagem_produto(
    produto_id,
    url,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE produtos
        SET imagem_url = ?
        WHERE id = ?
    """, (
        url,
        produto_id,
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


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
            str(dados).strip(),
        ))

        login_id = cursor.lastrowid

        cursor.execute("""
            UPDATE produtos
            SET estoque = estoque + 1
            WHERE id = ?
        """, (
            produto_id,
        ))

        if cursor.rowcount != 1:

            conn.rollback()

            raise ValueError(
                "Produto não encontrado."
            )

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

            if cursor.rowcount != 1:

                raise ValueError(
                    "Produto não encontrado."
                )

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
        return int(resultado[0])

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


def consultar_login(login_id):

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


def excluir_login(login_id):

    conn = conectar()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "BEGIN IMMEDIATE"
        )

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

            conn.rollback()
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

        excluido = cursor.rowcount > 0

        if (
            excluido
            and status == "disponivel"
        ):

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

    except Exception:

        conn.rollback()
        conn.close()

        raise


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
        SELECT COUNT(*)
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
        SELECT COUNT(*)
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
# COMPRA SEGURA DE LOGIN
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

        if estoque <= 0:

            conn.rollback()
            conn.close()

            return {
                "sucesso": False,
                "erro": "estoque_indisponivel",
            }

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

        cursor.execute("""
            UPDATE produtos
            SET estoque = estoque - 1
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

        cursor.execute("""
            SELECT saldo
            FROM usuarios
            WHERE id = ?
        """, (
            usuario_id,
        ))

        novo_saldo_resultado = cursor.fetchone()

        novo_saldo = float(
            novo_saldo_resultado[0]
        )

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
        float(valor),
        pushinpay_id,
    ))

    pagamento_id = cursor.lastrowid

    conn.commit()
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

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


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

    pagamentos = cursor.fetchall()

    conn.close()

    return pagamentos


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

        pagamento = cursor.fetchone()

        if not pagamento:

            conn.rollback()
            conn.close()

            return None

        usuario_id = pagamento[0]
        valor = float(pagamento[1])
        status = pagamento[2]

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

    pagamentos = cursor.fetchall()

    conn.close()

    return pagamentos
