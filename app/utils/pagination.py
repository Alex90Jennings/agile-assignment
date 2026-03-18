"""
Pagination helpers shared across admin list views.

Eliminates the boilerplate request-arg extraction and .paginate() call
that was repeated in every list route.
"""

from flask import request


def get_page(param: str = 'page') -> int:
    """Return the current page number from the query string, clamped to ≥ 1."""
    return max(request.args.get(param, 1, type=int), 1)


def get_search_term(param: str = 'q') -> str:
    """Return a stripped search string from the query string."""
    return request.args.get(param, '').strip()


def paginate_query(query, page: int, per_page: int = 5):
    """Paginate *query* and return a Flask-SQLAlchemy Pagination object."""
    return query.paginate(page=page, per_page=per_page, error_out=False)
