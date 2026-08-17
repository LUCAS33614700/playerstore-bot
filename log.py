import logging

# =========================================================
# LOG CENTRAL DO BOT
# =========================================================
# Antes o projeto usava print() espalhado pelo código pra
# registrar erros e eventos. Isso funciona, mas não tem
# nível (info/erro), não tem horário e não dá pra mandar
# pra um arquivo de log em produção sem perder tudo no
# terminal.
#
# As funções abaixo têm a mesma "cara" do print() (aceitam
# vários argumentos e juntam com espaço), então substituem
# print() nos outros arquivos sem precisar reescrever cada
# chamada — só trocam o nível certo (info ou erro).

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_logger = logging.getLogger("playerstore_bot")


def _juntar(args):
    return " ".join(str(item) for item in args)


def log_info(*args):
    _logger.info(_juntar(args))


def log_erro(*args):
    _logger.error(_juntar(args))


def log_aviso(*args):
    _logger.warning(_juntar(args))
