class RegraDeNegocioError(Exception):
    """Violação de regra de negócio (vira HTTP 422 no handler do main)."""


class RecursoNaoEncontradoError(RegraDeNegocioError):
    """Recurso inexistente ou de outro cliente (vira HTTP 404 no handler do main)."""
