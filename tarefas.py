import asyncio

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)

from telegram.ext import (
    Application,
    ContextTypes,
)

from config import ADMIN_ID, DATABASE_NAME

from database import (
    listar_pagamentos_pendentes,
    consultar_saldo,
    atualizar_status_pagamento,
    processar_pagamento_pago,
    listar_logins_vencendo,
    marcar_aviso_vencimento_enviado,
    listar_logins_vencidos,
    marcar_vencimento_final_notificado,
    listar_mensagens_grupo_para_apagar,
    marcar_mensagem_grupo_apagada,
    relatorio_vendas_periodo,
    obter_configuracao,
    definir_configuracao,
    produto_mais_vendido_periodo,
    listar_todos_produtos,
    listar_boas_vindas_vencidas,
    marcar_boas_vindas_apagada,
)

from pushinpay import consultar_pix
from menu import menu_principal
from log import log_info, log_erro


# =========================================================
# TAREFAS EM SEGUNDO PLANO (VERIFICADORES / RELATÓRIOS)
# =========================================================
# Esse módulo reúne tudo que roda sozinho, em loop, sem
# interação direta do usuário: checar pagamentos PIX
# pendentes, avisar sobre contas vencendo, apagar mensagens
# antigas do grupo de anúncios e mandar o relatório de
# vendas. Antes vivia dentro do main.py — foi separado pra
# deixar o arquivo principal menor e mais fácil de navegar.

INTERVALO_VERIFICACAO = 5

VERIFICADOR_TASK = "verificador_pagamentos_task"
VERIFICADOR_VENCIMENTOS_TASK = "verificador_vencimentos_task"
RELATORIO_VENDAS_TASK = "relatorio_vendas_task"
INTERVALO_VERIFICACAO_VENCIMENTOS = 60 * 60


# =========================================================
# VERIFICAÇÃO AUTOMÁTICA
# =========================================================
# IMPORTANTE:
# Não usamos JobQueue.
# Isso evita crash quando o pacote job-queue não está instalado
# no Railway. O verificador roda em uma task asyncio própria.

async def _verificar_um_pagamento(
    context: ContextTypes.DEFAULT_TYPE,
    pagamento,
):
    try:
        (
            pagamento_id,
            usuario_id,
            valor,
            transacao_id,
            status_banco,
            criado_em,
        ) = pagamento

        transacao = await asyncio.to_thread(
            consultar_pix,
            transacao_id,
        )

        status = str(
            transacao.get("status", "")
        ).lower()

        log_info(
            f"PIX {transacao_id}: {status}"
        )

        if status == "paid":
            resultado = processar_pagamento_pago(
                transacao_id
            )

            if not resultado:
                return

            novo_saldo = consultar_saldo(
                usuario_id
            )

            try:
                await context.bot.send_message(
                    chat_id=usuario_id,
                    text=(
                        "✅ *PAGAMENTO APROVADO!*\n\n"
                        "━━━━━━━━━━━━━━━━━━\n"
                        f"💰 Valor: R$ {float(valor):.2f}\n"
                        f"🆔 ID: `{transacao_id}`\n"
                        "━━━━━━━━━━━━━━━━━━\n\n"
                        f"💳 *Novo saldo:* R$ {float(novo_saldo):.2f}\n\n"
                        "🎉 Seu saldo foi liberado automaticamente!"
                    ),
                    reply_markup=menu_principal(),
                    parse_mode="Markdown",
                )
            except Exception as erro_envio:
                log_erro(
                    "ERRO AO ENVIAR CONFIRMAÇÃO:",
                    repr(erro_envio),
                )

            return

        if status in (
            "canceled",
            "cancelled",
            "expired",
        ):
            atualizado = atualizar_status_pagamento(
                transacao_id,
                "cancelado",
            )

            if atualizado:
                try:
                    await context.bot.send_message(
                        chat_id=usuario_id,
                        text=(
                            "❌ *PAGAMENTO ENCERRADO*\n\n"
                            f"💰 Valor: R$ {float(valor):.2f}\n\n"
                            "A cobrança PIX foi cancelada ou expirou.\n\n"
                            "💳 Nenhum saldo foi adicionado."
                        ),
                        reply_markup=menu_principal(),
                        parse_mode="Markdown",
                    )
                except Exception as erro_envio:
                    log_erro(
                        "ERRO AO ENVIAR CANCELAMENTO:",
                        repr(erro_envio),
                    )

    except Exception as erro:
        try:
            pix_id = pagamento[3]
        except Exception:
            pix_id = "desconhecido"

        log_erro(
            f"ERRO NA VERIFICAÇÃO DO PIX {pix_id}:",
            repr(erro),
        )


async def verificar_pagamentos_automaticamente(
    context: ContextTypes.DEFAULT_TYPE,
):
    pagamentos = listar_pagamentos_pendentes()

    if not pagamentos:
        return

    log_info(
        f"🔎 Verificando {len(pagamentos)} pagamento(s)..."
    )

    # Consulta todos os PIX pendentes em paralelo em vez de
    # um por um em fila — com muitos pagamentos pendentes ao
    # mesmo tempo (loja com muitos clientes ativos), isso
    # reduz bastante o tempo total do ciclo de verificação.
    await asyncio.gather(
        *(
            _verificar_um_pagamento(context, pagamento)
            for pagamento in pagamentos
        ),
        return_exceptions=True,
    )


# =========================================================
# AVISO DE VENCIMENTO (1 DIA ANTES) PRO ADMIN
# =========================================================

async def verificar_vencimentos_proximos(
    bot,
):

    contas = listar_logins_vencendo()

    if not contas:
        return

    log_info(
        f"⏳ {len(contas)} conta(s) vencendo em "
        "até 24h."
    )

    for conta in contas:

        try:
            (
                login_id,
                usuario_id,
                nome_cliente,
                username_cliente,
                produto_id,
                nome_produto,
                vendido_em,
                duracao_dias,
            ) = conta

            username_texto = (
                f"@{username_cliente}"
                if username_cliente
                else "Não informado"
            )

            texto = (
                "⏳ *CONTA VENCENDO EM ATÉ 24H*\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"📦 *Produto:* {nome_produto}\n"
                f"👤 *Cliente:* {nome_cliente or 'Não informado'}\n"
                f"🔗 *Username:* {username_texto}\n"
                f"🆔 *ID do cliente:* `{usuario_id}`\n"
                f"📅 *Vendido em:* {vendido_em}\n"
                f"⏳ *Duração:* {duracao_dias} dias\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "Considere entrar em contato pra "
                "oferecer renovação."
            )

            await bot.send_message(
                chat_id=ADMIN_ID,
                text=texto,
                parse_mode="Markdown",
            )

            marcar_aviso_vencimento_enviado(
                login_id
            )

        except Exception as erro:
            log_erro(
                "ERRO AO AVISAR VENCIMENTO:",
                repr(erro),
            )


# =========================================================
# CONTA VENCIDA (PRAZO JÁ ATINGIDO) — AVISA CLIENTE E ADMIN
# =========================================================

async def verificar_contas_vencidas(
    bot,
):

    contas = listar_logins_vencidos()

    if not contas:
        return

    log_info(
        f"⌛ {len(contas)} conta(s) com o prazo "
        "encerrado."
    )

    for conta in contas:

        try:
            (
                login_id,
                usuario_id,
                nome_cliente,
                username_cliente,
                produto_id,
                nome_produto,
                vendido_em,
                duracao_dias,
            ) = conta

            username_texto = (
                f"@{username_cliente}"
                if username_cliente
                else "Não informado"
            )

            # -----------------------------------------
            # AVISO PARA O CLIENTE
            # -----------------------------------------

            try:
                await bot.send_message(
                    chat_id=usuario_id,
                    text=(
                        "⌛ *SEU PRAZO DE ACESSO "
                        "ACABOU*\n\n"
                        "━━━━━━━━━━━━━━━━━━\n"
                        f"📦 *Produto:* {nome_produto}\n"
                        f"📅 *Duração:* {duracao_dias} "
                        "dias\n"
                        "━━━━━━━━━━━━━━━━━━\n\n"
                        "O período da sua conta chegou "
                        "ao fim.\n\n"
                        "⚠️ Se não for renovada, a "
                        "senha poderá ser trocada e "
                        "o acesso será encerrado.\n\n"
                        "Clique abaixo para renovar "
                        "agora e continuar com acesso."
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "🔄 Renovar agora",
                                    callback_data=(
                                        "renovar_login_"
                                        f"{login_id}"
                                    ),
                                )
                            ]
                        ]
                    ),
                    parse_mode="Markdown",
                )
            except Exception as erro_cliente:
                log_erro(
                    "ERRO AO AVISAR CLIENTE "
                    "(VENCIMENTO):",
                    repr(erro_cliente),
                )

            # -----------------------------------------
            # AVISO PARA O ADMIN
            # -----------------------------------------

            await bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "⌛ *PRAZO ENCERRADO — AÇÃO "
                    "NECESSÁRIA*\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"📦 *Produto:* {nome_produto}\n"
                    f"👤 *Cliente:* "
                    f"{nome_cliente or 'Não informado'}\n"
                    f"🔗 *Username:* {username_texto}\n"
                    f"🆔 *ID do cliente:* `{usuario_id}`\n"
                    f"🔐 *ID da conta:* `{login_id}`\n"
                    f"📅 *Vendido em:* {vendido_em}\n"
                    f"⏳ *Duração:* {duracao_dias} dias\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    "O cliente já foi avisado. Se ele "
                    "não renovar, considere trocar a "
                    "senha dessa conta."
                ),
                parse_mode="Markdown",
            )

            marcar_vencimento_final_notificado(
                login_id
            )

        except Exception as erro:
            log_erro(
                "ERRO AO PROCESSAR VENCIMENTO "
                "FINAL:",
                repr(erro),
            )


async def apagar_mensagens_antigas_grupo(
    bot,
):

    dias_configurado = obter_configuracao(
        "limpeza_grupo_dias"
    )

    try:
        dias = max(1, min(int(dias_configurado), 3))
    except (TypeError, ValueError):
        dias = 3

    mensagens = listar_mensagens_grupo_para_apagar(
        dias=dias
    )

    if not mensagens:
        return

    log_info(
        f"🧹 Apagando {len(mensagens)} "
        "mensagem(ns) antiga(s) do grupo."
    )

    for registro_id, chat_id, message_id in mensagens:

        try:
            await bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )
        except Exception as erro:
            log_erro(
                "ERRO AO APAGAR MENSAGEM DO "
                "GRUPO:",
                repr(erro),
            )

        marcar_mensagem_grupo_apagada(
            registro_id
        )


# =========================================================
# BOAS-VINDAS PENDENTES DE APAGAR
# =========================================================
# Verificador rápido (a cada minuto) que confere no banco
# quais boas-vindas já venceram o prazo de 30 minutos e
# apaga a mensagem — sobrevive a reinícios do bot, já que o
# horário fica salvo no banco e não só na memória.

INTERVALO_VERIFICACAO_BOAS_VINDAS = 60  # 1 minuto

BOAS_VINDAS_TASK = "boas_vindas_task"


async def apagar_boas_vindas_vencidas(
    bot,
):

    pendentes = listar_boas_vindas_vencidas()

    if not pendentes:
        return

    for registro_id, chat_id, message_id in pendentes:

        try:
            await bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )
        except Exception as erro:
            log_erro(
                "ERRO AO APAGAR BOAS-VINDAS "
                "VENCIDA:",
                repr(erro),
            )

        marcar_boas_vindas_apagada(
            registro_id
        )


async def loop_boas_vindas(
    application: Application,
):
    log_info(
        "👋 Verificador de boas-vindas iniciado."
    )

    while True:
        try:
            await apagar_boas_vindas_vencidas(
                application.bot
            )

        except asyncio.CancelledError:
            log_info(
                "👋 Verificador de boas-vindas "
                "encerrado."
            )
            raise

        except Exception as erro:
            log_erro(
                "ERRO NO LOOP DE BOAS-VINDAS:",
                repr(erro),
            )

        await asyncio.sleep(
            INTERVALO_VERIFICACAO_BOAS_VINDAS
        )


async def loop_verificador_vencimentos(
    application: Application,
):
    log_info(
        "⏳ Verificador de vencimentos iniciado."
    )

    while True:
        try:
            await verificar_vencimentos_proximos(
                application.bot
            )

            await verificar_contas_vencidas(
                application.bot
            )

            await apagar_mensagens_antigas_grupo(
                application.bot
            )

        except asyncio.CancelledError:
            log_info(
                "⏳ Verificador de vencimentos "
                "encerrado."
            )
            raise

        except Exception as erro:
            log_erro(
                "ERRO NO LOOP DE VENCIMENTOS:",
                repr(erro),
            )

        await asyncio.sleep(
            INTERVALO_VERIFICACAO_VENCIMENTOS
        )


INTERVALO_RELATORIO_VENDAS = 24 * 60 * 60


async def enviar_relatorio_vendas(
    bot,
):

    try:

        qtd_dia, total_dia = relatorio_vendas_periodo(24)
        qtd_semana, total_semana = relatorio_vendas_periodo(
            24 * 7
        )

        destino = (
            obter_configuracao("suporte_chat_id")
            or ADMIN_ID
        )

        await bot.send_message(
            chat_id=destino,
            text=(
                "📊 *RELATÓRIO DE VENDAS*\n\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "🗓️ *Últimas 24h*\n"
                f"🛍️ Vendas: {qtd_dia}\n"
                f"💰 Faturamento: R$ {total_dia:.2f}\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "🗓️ *Últimos 7 dias*\n"
                f"🛍️ Vendas: {qtd_semana}\n"
                f"💰 Faturamento: R$ {total_semana:.2f}\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            parse_mode="Markdown",
        )

    except Exception as erro:
        log_erro(
            "ERRO NO RELATÓRIO DE VENDAS:",
            repr(erro),
        )


async def enviar_backup_automatico(
    bot,
):
    import os

    if not os.path.exists(DATABASE_NAME):
        return

    try:
        with open(DATABASE_NAME, "rb") as arquivo:
            await bot.send_document(
                chat_id=ADMIN_ID,
                document=arquivo,
                filename="bot.db",
                caption=(
                    "💾 Backup automático diário do "
                    "banco de dados."
                ),
            )
    except Exception as erro:
        log_erro(
            "ERRO NO BACKUP AUTOMÁTICO:",
            repr(erro),
        )


# =========================================================
# POSTS PROMOCIONAIS AUTOMÁTICOS (DIVULGAÇÃO NO GRUPO)
# =========================================================
# Manda de tempos em tempos um post real (nunca inventado)
# no grupo de anúncios, alternando entre "mais vendido da
# semana" e destaque de um produto do catálogo com estoque
# disponível — só pra dar visibilidade ao que já existe na
# loja, sem fingir vendas que não aconteceram.

CONFIG_DIVULGACAO_ATIVA = "divulgacao_automatica_ativa"
CONFIG_DIVULGACAO_QTD_DIA = "divulgacao_automatica_qtd_dia"

QTD_DIVULGACOES_PADRAO = 4  # dentro da faixa de 3-5 pedida


def divulgacao_automatica_esta_ativa():
    valor = obter_configuracao(
        CONFIG_DIVULGACAO_ATIVA
    )
    return valor == "1"


def ativar_divulgacao_automatica():
    definir_configuracao(
        CONFIG_DIVULGACAO_ATIVA, "1"
    )


def desativar_divulgacao_automatica():
    definir_configuracao(
        CONFIG_DIVULGACAO_ATIVA, "0"
    )


def definir_qtd_divulgacoes_dia(quantidade):
    quantidade = max(1, min(int(quantidade), 12))
    definir_configuracao(
        CONFIG_DIVULGACAO_QTD_DIA,
        str(quantidade),
    )
    return quantidade


def obter_qtd_divulgacoes_dia():
    valor = obter_configuracao(
        CONFIG_DIVULGACAO_QTD_DIA
    )
    try:
        return max(1, min(int(valor), 12))
    except (TypeError, ValueError):
        return QTD_DIVULGACOES_PADRAO


async def enviar_post_divulgacao(bot):
    """Manda UM post de divulgação real pro grupo de
    anúncios: mais vendido da semana (se houve venda) ou,
    na falta disso, um produto do catálogo com estoque > 0
    escolhido de forma rotativa."""

    grupo_id = obter_configuracao("grupo_anuncios_id")

    if not grupo_id:
        return

    try:
        grupo_id_int = int(grupo_id)
    except ValueError:
        return

    try:
        me = await bot.get_me()

        botao = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🛒 Acessar o bot",
                        url=f"https://t.me/{me.username}",
                    )
                ]
            ]
        )

        mais_vendido = produto_mais_vendido_periodo(
            24 * 7
        )

        if mais_vendido:
            _, nome, qtd_vendida = mais_vendido

            await bot.send_message(
                chat_id=grupo_id_int,
                text=(
                    "🔥 *MAIS VENDIDO DA SEMANA!*\n\n"
                    f"🏆 {nome}\n"
                    f"📦 {qtd_vendida} unidade(s) "
                    "vendida(s) nos últimos 7 dias\n\n"
                    "⚡ Garanta o seu antes que acabe!"
                ),
                reply_markup=botao,
                parse_mode="Markdown",
            )
            return

        # Sem vendas no período: destaca um produto com
        # estoque disponível, escolhido de forma rotativa
        # (baseado no horário) pra não repetir sempre o
        # mesmo.
        produtos = [
            produto
            for produto in listar_todos_produtos()
            if int(produto[4]) > 0
        ]

        if not produtos:
            return

        import time

        indice = int(time.time() // 3600) % len(produtos)
        _, nome, descricao, preco, estoque = produtos[
            indice
        ]

        await bot.send_message(
            chat_id=grupo_id_int,
            text=(
                "✨ *DESTAQUE DA LOJA!*\n\n"
                f"🛒 {nome}\n"
                f"💰 R$ {float(preco):.2f}\n"
                f"📦 {int(estoque)} disponível(is) "
                "em estoque\n\n"
                "⚡ Peça já o seu!"
            ),
            reply_markup=botao,
            parse_mode="Markdown",
        )

    except Exception as erro:
        log_erro(
            "ERRO NO POST DE DIVULGAÇÃO:",
            repr(erro),
        )


DIVULGACAO_TASK = "divulgacao_automatica_task"


async def loop_divulgacao_automatica(
    application: Application,
):
    log_info(
        "📣 Divulgação automática iniciada "
        "(aguardando ativação no /admin)."
    )

    while True:

        if not divulgacao_automatica_esta_ativa():
            # Checa a cada 5 minutos se foi ligada.
            await asyncio.sleep(5 * 60)
            continue

        qtd_dia = obter_qtd_divulgacoes_dia()

        # Distribui os posts ao longo de um dia útil de
        # divulgação (09h-23h, 14 horas), com uma variação
        # aleatória pequena pra não parecer um robô batendo
        # sempre no mesmo minuto exato.
        import random

        janela_segundos = 14 * 60 * 60
        intervalo_base = janela_segundos / qtd_dia
        variacao = intervalo_base * 0.2

        espera = intervalo_base + random.uniform(
            -variacao, variacao
        )

        await asyncio.sleep(max(60, espera))

        if not divulgacao_automatica_esta_ativa():
            continue

        try:
            await enviar_post_divulgacao(
                application.bot
            )
        except asyncio.CancelledError:
            raise
        except Exception as erro:
            log_erro(
                "ERRO NO LOOP DE DIVULGAÇÃO:",
                repr(erro),
            )


async def loop_relatorio_vendas(
    application: Application,
):
    log_info(
        "📊 Relatório automático de vendas iniciado."
    )

    while True:

        await asyncio.sleep(
            INTERVALO_RELATORIO_VENDAS
        )

        try:
            await enviar_relatorio_vendas(
                application.bot
            )

            await enviar_backup_automatico(
                application.bot
            )

        except asyncio.CancelledError:
            log_info(
                "📊 Relatório automático de "
                "vendas encerrado."
            )
            raise

        except Exception as erro:
            log_erro(
                "ERRO NO LOOP DE RELATÓRIO:",
                repr(erro),
            )


async def loop_verificador_pagamentos(
    application: Application,
):
    log_info("💳 Verificador automático de PIX iniciado.")

    while True:
        try:
            context = ContextTypes.DEFAULT_TYPE

            # Cria um objeto de contexto simples através da própria
            # aplicação para manter acesso ao bot.
            class VerificadorContext:
                bot = application.bot

            await verificar_pagamentos_automaticamente(
                VerificadorContext()
            )

        except asyncio.CancelledError:
            log_info("💳 Verificador automático encerrado.")
            raise

        except Exception as erro:
            log_erro(
                "ERRO NO LOOP DO VERIFICADOR:",
                repr(erro),
            )

        await asyncio.sleep(
            INTERVALO_VERIFICACAO
        )


async def iniciar_verificador(
    application: Application,
):
    try:
        await application.bot.set_my_commands(
            [
                BotCommand(
                    "start",
                    "Iniciar Bot",
                ),
                BotCommand(
                    "pix",
                    "Adicionar saldo",
                ),
                BotCommand(
                    "admin",
                    "Menu adm",
                ),
                BotCommand(
                    "id",
                    "Mostrar seu ID do Telegram",
                ),
                BotCommand(
                    "backup",
                    "Baixar backup do banco (admin)",
                ),
            ]
        )
    except Exception as erro:
        log_erro(
            "ERRO AO REGISTRAR COMANDOS:",
            repr(erro),
        )

    task = asyncio.create_task(
        loop_verificador_pagamentos(application),
        name=VERIFICADOR_TASK,
    )

    application.bot_data[
        VERIFICADOR_TASK
    ] = task

    task_vencimentos = asyncio.create_task(
        loop_verificador_vencimentos(application),
        name=VERIFICADOR_VENCIMENTOS_TASK,
    )

    application.bot_data[
        VERIFICADOR_VENCIMENTOS_TASK
    ] = task_vencimentos

    task_relatorio = asyncio.create_task(
        loop_relatorio_vendas(application),
        name=RELATORIO_VENDAS_TASK,
    )

    application.bot_data[
        RELATORIO_VENDAS_TASK
    ] = task_relatorio

    task_divulgacao = asyncio.create_task(
        loop_divulgacao_automatica(application),
        name=DIVULGACAO_TASK,
    )

    application.bot_data[
        DIVULGACAO_TASK
    ] = task_divulgacao

    task_boas_vindas = asyncio.create_task(
        loop_boas_vindas(application),
        name=BOAS_VINDAS_TASK,
    )

    application.bot_data[
        BOAS_VINDAS_TASK
    ] = task_boas_vindas


async def parar_verificador(
    application: Application,
):
    task = application.bot_data.get(
        VERIFICADOR_TASK
    )

    if task:
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

    task_vencimentos = application.bot_data.get(
        VERIFICADOR_VENCIMENTOS_TASK
    )

    if task_vencimentos:
        task_vencimentos.cancel()

        try:
            await task_vencimentos
        except asyncio.CancelledError:
            pass

    task_relatorio = application.bot_data.get(
        RELATORIO_VENDAS_TASK
    )

    if task_relatorio:
        task_relatorio.cancel()

        try:
            await task_relatorio
        except asyncio.CancelledError:
            pass

    task_divulgacao = application.bot_data.get(
        DIVULGACAO_TASK
    )

    if task_divulgacao:
        task_divulgacao.cancel()

        try:
            await task_divulgacao
        except asyncio.CancelledError:
            pass

    task_boas_vindas = application.bot_data.get(
        BOAS_VINDAS_TASK
    )

    if task_boas_vindas:
        task_boas_vindas.cancel()

        try:
            await task_boas_vindas
        except asyncio.CancelledError:
            pass

