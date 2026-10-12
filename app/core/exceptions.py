class RegraDeNegocioError(Exception):
    """Violação de regra de negócio (vira HTTP 422 no handler do main)."""