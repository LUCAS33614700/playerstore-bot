import sqlite3

from config import DATABASE_NAME


# =========================================================
# CONEXÃO
# =========================================================

def conectar():
    conn = sqlite3.connect(
        DATABASE_NAME,
        timeout=30,
    )

    # WAL permite leituras e escritas concorrentes sem
    # travar o banco inteiro (evita "database is locked"
    # quando várias partes do bot mexem no SQLite ao
    # mesmo tempo).
    conn.execute("PRAGMA journal_mode=WAL")

    # Se duas conexões tentarem escrever ao mesmo tempo,
    # espera até 30s antes de falhar em vez de estourar
    # "database is locked" na hora.
    conn.execute("PRAGMA busy_timeout=30000")

    conn.execute("PRAGMA foreign_keys=ON")

    return conn


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

    try:
        cursor.execute("""
            ALTER TABLE usuarios
            ADD COLUMN lembrete_enviado
            INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass

    # -----------------------------------------------------
    # LIMITE DE CRÉDITO (compra mesmo com saldo insuficiente,
    # até o limite liberado pelo admin para aquele cliente)
    # -----------------------------------------------------

    try:
        cursor.execute("""
            ALTER TABLE usuarios
            ADD COLUMN limite_credito
            REAL DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass

    # -----------------------------------------------------
    # DURAÇÃO DO PRODUTO / AVISO DE VENCIMENTO
    # -----------------------------------------------------

    try:
        cursor.execute("""
            ALTER TABLE produtos
            ADD COLUMN duracao_dias
            INTEGER DEFAULT 30
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE logins
            ADD COLUMN aviso_vencimento_enviado
            INTEGER DEFAULT 0
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

    # -----------------------------------------------------
    # DURAÇÃO DO PRODUTO / ALERTA DE VENCIMENTO
    # -----------------------------------------------------

    try:
        cursor.execute("""
            ALTER TABLE produtos
            ADD COLUMN duracao_dias INTEGER
        """)
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            ALTER TABLE logins
            ADD COLUMN alerta_vencimento_enviado
            INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass

    # -----------------------------------------------------
    # ESTOQUE BAIXO
    # -----------------------------------------------------

    try:
        cursor.execute("""
            ALTER TABLE produtos
            ADD COLUMN alerta_estoque_enviado
            INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass

    # -----------------------------------------------------
    # DATA DO PEDIDO (para relatório de vendas)
    # -----------------------------------------------------

    try:
        cursor.execute("""
            ALTER TABLE pedidos
            ADD COLUMN criado_em
            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)
    except sqlite3.OperationalError:
        pass

    # -----------------------------------------------------
    # AVISOS DE REPOSIÇÃO DE ESTOQUE
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS avisos_reposicao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, produto_id)
        )
    """)

    # -----------------------------------------------------
    # ENCOMENDAS (PRÉ-VENDA)
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            descricao TEXT NOT NULL,
            valor REAL,
            status TEXT NOT NULL DEFAULT 'aguardando_valor',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # GRUPOS/CANAIS OBRIGATÓRIOS (SUPORTA VÁRIOS)
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grupos_obrigatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo_id INTEGER NOT NULL UNIQUE,
            link TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # MENSAGENS DO GRUPO DE ANÚNCIOS (LIMPEZA AUTOMÁTICA)
    # -----------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mensagens_grupo_anuncios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            apagada INTEGER DEFAULT 0
        )
    """)

    # Migração: quem já tinha um único grupo obrigatório
    # configurado (chave/valor antigo) tem ele importado
    # automaticamente pra nova tabela, uma única vez.

    cursor.execute("""
        SELECT COUNT(*) FROM grupos_obrigatorios
    """)

    if cursor.fetchone()[0] == 0:

        cursor.execute("""
            SELECT valor FROM configuracoes
            WHERE chave = 'grupo_obrigatorio_id'
        """)
        antigo_id = cursor.fetchone()

        cursor.execute("""
            SELECT valor FROM configuracoes
            WHERE chave = 'grupo_obrigatorio_link'
        """)
        antigo_link = cursor.fetchone()

        if antigo_id and antigo_link:

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO grupos_obrigatorios
                    (grupo_id, link)
                    VALUES (?, ?)
                """, (
                    int(antigo_id[0]),
                    antigo_link[0],
                ))
            except (ValueError, TypeError):
                pass

    # -----------------------------------------------------
    # ÍNDICES
    # -----------------------------------------------------
    # Colunas usadas com frequência em WHERE/JOIN. Sem
    # índice o SQLite varre a tabela inteira toda vez —
    # não dói com poucas linhas, mas cresce junto com o
    # catálogo, os pedidos e os pagamentos.

    indices = [
        (
            "idx_logins_produto_status",
            "logins",
            "produto_id, status",
        ),
        (
            "idx_logins_usuario",
            "logins",
            "usuario_id",
        ),
        (
            "idx_pedidos_usuario",
            "pedidos",
            "usuario_id",
        ),
        (
            "idx_pedidos_produto",
            "pedidos",
            "produto_id",
        ),
        (
            "idx_pagamentos_usuario",
            "pagamentos",
            "usuario_id",
        ),
        (
            "idx_pagamentos_status",
            "pagamentos",
            "status",
        ),
        (
            "idx_carrinho_usuario",
            "carrinho_itens",
            "usuario_id",
        ),
        (
            "idx_produto_categorias_categoria",
            "produto_categorias",
            "categoria_id",
        ),
        (
            "idx_avisos_reposicao_produto",
            "avisos_reposicao",
            "produto_id",
        ),
        (
            "idx_mensagens_grupo_apagada",
            "mensagens_grupo_anuncios",
            "apagada",
        ),
    ]

    for nome_indice, tabela, colunas in indices:
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {nome_indice}
            ON {tabela} ({colunas})
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


def listar_todos_usuarios():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM usuarios
    """)

    resultados = cursor.fetchall()

    conn.close()

    return [int(linha[0]) for linha in resultados]


def usuario_ja_recebeu_lembrete(
    usuario_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT lembrete_enviado
        FROM usuarios
        WHERE id = ?
    """, (
        usuario_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return bool(resultado[0])

    return False


def marcar_lembrete_enviado(
    usuario_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET lembrete_enviado = 1
        WHERE id = ?
    """, (
        usuario_id,
    ))

    conn.commit()
    conn.close()


def definir_duracao_produto(
    produto_id,
    dias,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE produtos
        SET duracao_dias = ?
        WHERE id = ?
    """, (
        int(dias),
        produto_id,
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def obter_duracao_produto(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT duracao_dias
        FROM produtos
        WHERE id = ?
    """, (
        produto_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado and resultado[0] is not None:
        return int(resultado[0])

    return None


def listar_logins_vencendo():
    """
    Retorna as contas vendidas cujo vencimento
    (data da venda + duração do produto) cai
    dentro das próximas 24h, e que ainda não
    geraram alerta.
    """

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            l.id,
            l.usuario_id,
            u.nome,
            u.username,
            l.produto_id,
            p.nome,
            l.vendido_em,
            p.duracao_dias
        FROM logins l
        INNER JOIN produtos p
            ON p.id = l.produto_id
        LEFT JOIN usuarios u
            ON u.id = l.usuario_id
        WHERE l.status = 'vendido'
        AND l.alerta_vencimento_enviado = 0
        AND p.duracao_dias IS NOT NULL
        AND date(
            l.vendido_em,
            '+' || p.duracao_dias || ' days'
        ) <= date('now', '+1 day')
        AND date(
            l.vendido_em,
            '+' || p.duracao_dias || ' days'
        ) >= date('now')
    """)

    resultados = cursor.fetchall()

    conn.close()

    return resultados


def marcar_aviso_vencimento_enviado(
    login_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE logins
        SET alerta_vencimento_enviado = 1
        WHERE id = ?
    """, (
        login_id,
    ))

    conn.commit()
    conn.close()


# =========================================================
# VENCIMENTO COMPLETO (CONTA JÁ ATINGIU A DURAÇÃO)
# =========================================================
# Diferente do aviso de "vencendo em até 24h" acima, esta
# checagem dispara quando o prazo já foi atingido/ultrapassado
# (vendido_em + duracao_dias <= hoje), para avisar cliente e
# admin que o prazo acabou.

def listar_logins_vencidos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            l.id,
            l.usuario_id,
            u.nome,
            u.username,
            l.produto_id,
            p.nome,
            l.vendido_em,
            p.duracao_dias
        FROM logins l
        INNER JOIN produtos p
            ON p.id = l.produto_id
        LEFT JOIN usuarios u
            ON u.id = l.usuario_id
        WHERE l.status = 'vendido'
        AND l.aviso_vencimento_enviado = 0
        AND p.duracao_dias IS NOT NULL
        AND date(
            l.vendido_em,
            '+' || p.duracao_dias || ' days'
        ) <= date('now')
    """)

    resultados = cursor.fetchall()

    conn.close()

    return resultados


def marcar_vencimento_final_notificado(
    login_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE logins
        SET aviso_vencimento_enviado = 1
        WHERE id = ?
    """, (
        login_id,
    ))

    conn.commit()
    conn.close()


# =========================================================
# ESTOQUE BAIXO
# =========================================================

def produto_ja_alertou_estoque_baixo(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT alerta_estoque_enviado
        FROM produtos
        WHERE id = ?
    """, (
        produto_id,
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return bool(resultado[0])

    return False


def marcar_alerta_estoque_enviado(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE produtos
        SET alerta_estoque_enviado = 1
        WHERE id = ?
    """, (
        produto_id,
    ))

    conn.commit()
    conn.close()


def resetar_alerta_estoque(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE produtos
        SET alerta_estoque_enviado = 0
        WHERE id = ?
    """, (
        produto_id,
    ))

    conn.commit()
    conn.close()


# =========================================================
# RELATÓRIO DE VENDAS
# =========================================================

def relatorio_vendas_periodo(
    horas=24,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*),
            COALESCE(SUM(valor), 0)
        FROM pedidos
        WHERE status = 'pago'
        AND criado_em >= datetime(
            'now',
            ?
        )
    """, (
        f"-{int(horas)} hours",
    ))

    resultado = cursor.fetchone()

    conn.close()

    if resultado:
        return (
            int(resultado[0]),
            float(resultado[1]),
        )

    return 0, 0.0


def produto_mais_vendido_periodo(
    horas=24 * 7,
):
    """Retorna (produto_id, nome, quantidade_vendida) do
    produto que mais vendeu no período, usando pedidos
    reais com status 'pago'. Retorna None se não houve
    nenhuma venda no período."""

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.produto_id,
            pr.nome,
            SUM(p.quantidade) AS total_vendido
        FROM pedidos p
        JOIN produtos pr ON pr.id = p.produto_id
        WHERE p.status = 'pago'
        AND p.criado_em >= datetime(
            'now',
            ?
        )
        GROUP BY p.produto_id
        ORDER BY total_vendido DESC
        LIMIT 1
    """, (
        f"-{int(horas)} hours",
    ))

    resultado = cursor.fetchone()

    conn.close()

    if not resultado:
        return None

    return (
        int(resultado[0]),
        resultado[1],
        int(resultado[2]),
    )


# =========================================================
# AVISOS DE REPOSIÇÃO DE ESTOQUE
# =========================================================

def registrar_aviso_reposicao(
    usuario_id,
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO avisos_reposicao
        (
            usuario_id,
            produto_id
        )
        VALUES (?, ?)
    """, (
        usuario_id,
        produto_id,
    ))

    conn.commit()
    conn.close()


def listar_interessados_reposicao(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT usuario_id
        FROM avisos_reposicao
        WHERE produto_id = ?
    """, (
        produto_id,
    ))

    resultados = cursor.fetchall()

    conn.close()

    return [
        int(linha[0])
        for linha in resultados
    ]


def remover_avisos_reposicao(
    produto_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM avisos_reposicao
        WHERE produto_id = ?
    """, (
        produto_id,
    ))

    conn.commit()
    conn.close()


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
        SET saldo = ROUND(saldo + ?, 2)
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

    # Permite o saldo ficar negativo até o limite de
    # crédito liberado pro cliente (0 por padrão, ou seja,
    # sem crédito o comportamento continua o mesmo de antes).

    cursor.execute("""
        UPDATE usuarios
        SET saldo = ROUND(saldo - ?, 2)
        WHERE id = ?
        AND (saldo + COALESCE(limite_credito, 0)) >= ?
    """, (
        float(valor),
        user_id,
        float(valor),
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def definir_limite_credito(
    user_id,
    limite,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET limite_credito = ?
        WHERE id = ?
    """, (
        float(limite),
        user_id,
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def obter_limite_credito(
    user_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(limite_credito, 0)
        FROM usuarios
        WHERE id = ?
    """, (
        user_id,
    ))

    linha = cursor.fetchone()

    conn.close()

    return float(linha[0]) if linha else 0.0


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


def listar_contas_usuario(
    usuario_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            l.id,
            l.produto_id,
            p.nome,
            l.vendido_em,
            p.duracao_dias
        FROM logins l
        INNER JOIN produtos p
            ON p.id = l.produto_id
        WHERE l.usuario_id = ?
        AND l.status = 'vendido'
        ORDER BY l.vendido_em DESC
    """, (
        usuario_id,
    ))

    resultados = cursor.fetchall()

    conn.close()

    return resultados


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
            SET saldo = ROUND(saldo - ?, 2)
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
            SET saldo = ROUND(saldo + ?, 2)
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


# =========================================================
# GRUPOS/CANAIS OBRIGATÓRIOS
# =========================================================

def adicionar_grupo_obrigatorio(
    grupo_id,
    link,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO grupos_obrigatorios
        (
            grupo_id,
            link
        )
        VALUES (?, ?)
        ON CONFLICT(grupo_id)
        DO UPDATE SET link = excluded.link
    """, (
        int(grupo_id),
        link,
    ))

    conn.commit()
    conn.close()


def listar_grupos_obrigatorios():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            grupo_id,
            link
        FROM grupos_obrigatorios
        ORDER BY id
    """)

    grupos = cursor.fetchall()

    conn.close()

    return grupos


def remover_grupo_obrigatorio(
    registro_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM grupos_obrigatorios
        WHERE id = ?
    """, (
        registro_id,
    ))

    removido = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return removido


# =========================================================
# MENSAGENS DO GRUPO DE ANÚNCIOS (LIMPEZA AUTOMÁTICA)
# =========================================================

def registrar_mensagem_grupo_anuncios(
    chat_id,
    message_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO mensagens_grupo_anuncios
        (
            chat_id,
            message_id
        )
        VALUES (?, ?)
    """, (
        chat_id,
        message_id,
    ))

    conn.commit()
    conn.close()


def listar_mensagens_grupo_para_apagar(
    dias=3,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            chat_id,
            message_id
        FROM mensagens_grupo_anuncios
        WHERE apagada = 0
        AND datetime(
            criado_em,
            '+' || ? || ' days'
        ) <= datetime('now')
    """, (
        dias,
    ))

    mensagens = cursor.fetchall()

    conn.close()

    return mensagens


def marcar_mensagem_grupo_apagada(
    registro_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE mensagens_grupo_anuncios
        SET apagada = 1
        WHERE id = ?
    """, (
        registro_id,
    ))

    conn.commit()
    conn.close()


# =========================================================
# ENCOMENDAS (PRÉ-VENDA — CLIENTE PEDE ALGO FORA DO CATÁLOGO)
# =========================================================

def criar_encomenda(
    usuario_id,
    descricao,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO encomendas
        (
            usuario_id,
            descricao,
            status
        )
        VALUES (?, ?, 'aguardando_valor')
    """, (
        usuario_id,
        descricao,
    ))

    encomenda_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return encomenda_id


def obter_encomenda(
    encomenda_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            usuario_id,
            descricao,
            valor,
            status,
            criado_em
        FROM encomendas
        WHERE id = ?
    """, (
        encomenda_id,
    ))

    encomenda = cursor.fetchone()

    conn.close()

    return encomenda


def definir_valor_encomenda(
    encomenda_id,
    valor,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE encomendas
        SET valor = ?,
            status = 'aguardando_pagamento'
        WHERE id = ?
        AND status = 'aguardando_valor'
    """, (
        float(valor),
        encomenda_id,
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def marcar_encomenda_paga(
    encomenda_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE encomendas
        SET status = 'pago'
        WHERE id = ?
        AND status = 'aguardando_pagamento'
    """, (
        encomenda_id,
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def marcar_encomenda_entregue(
    encomenda_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE encomendas
        SET status = 'entregue'
        WHERE id = ?
        AND status = 'pago'
    """, (
        encomenda_id,
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def cancelar_encomenda(
    encomenda_id,
):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE encomendas
        SET status = 'cancelado'
        WHERE id = ?
        AND status IN (
            'aguardando_valor',
            'aguardando_pagamento'
        )
    """, (
        encomenda_id,
    ))

    alterado = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return alterado


def listar_encomendas_pagas_nao_entregues():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            usuario_id,
            descricao,
            valor,
            criado_em
        FROM encomendas
        WHERE status = 'pago'
        ORDER BY id
    """)

    encomendas = cursor.fetchall()

    conn.close()

    return encomendas
