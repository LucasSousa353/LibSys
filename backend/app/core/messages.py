"""
Mensagens centralizadas do sistema.

Facilita manutenção, internacionalização e consistência de mensagens.
"""


class ErrorMessages:
    """Mensagens de erro do sistema."""

    # Books
    BOOK_NOT_FOUND = "Livro não encontrado"
    BOOK_ISBN_ALREADY_EXISTS = "ISBN já registrado"
    BOOK_NOT_AVAILABLE = "Livro não disponível no estoque"

    # Users
    USER_NOT_FOUND = "Usuário não localizado"
    USER_EMAIL_ALREADY_EXISTS = "Email já registrado"
    USER_ACCOUNT_LOCKED = "Conta temporariamente bloqueada por excesso de tentativas. Tente novamente em {seconds} segundos"
    USER_CURRENT_PASSWORD_WRONG = "Senha atual incorreta"
    USER_NEW_PASSWORD_SAME_AS_CURRENT = "A nova senha não pode ser igual à senha atual"

    # Loans
    LOAN_NOT_FOUND = "Empréstimo não encontrado"
    LOAN_ALREADY_RETURNED = "Empréstimo já devolvido"
    LOAN_USER_INACTIVE = "Não é possível criar empréstimo para usuário inativo"
    LOAN_MAX_ACTIVE_LIMIT = "Usuário atingiu o limite de {limit} empréstimos ativos"
    LOAN_USER_HAS_OVERDUE = "Usuário possui empréstimos atrasados pendentes"
    LOAN_PERMISSION_DENIED = "Você só pode devolver seus próprios empréstimos"
    LOAN_RENEW_PERMISSION_DENIED = "Você só pode renovar seus próprios empréstimos"
    LOAN_RENEW_OVERDUE = "Empréstimo atrasado não pode ser renovado"
    LOAN_RENEW_INVALID_STATUS = "Empréstimo não pode ser renovado"

    # Health
    HEALTH_POSTGRES_ERROR = "Health check failed for Postgres"
    HEALTH_REDIS_ERROR = "Health check failed for Redis"


class SuccessMessages:
    """Mensagens de sucesso do sistema."""

    # Loans
    LOAN_RETURNED = "Livro retornado."
