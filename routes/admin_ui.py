from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from api_errors import ApiError
from database import SessionLocal
from models import User
from rbac import is_admin

router = APIRouter(tags=["Admin UI"])

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "perigos_defaults.html"


def _get_user_by_token(token: str) -> User | None:
    db = SessionLocal()
    try:
        return db.execute(select(User).where(User.api_token == token)).scalar_one_or_none()
    finally:
        db.close()


@router.get("/admin/perigos-defaults")
def perigos_defaults_page(token: str | None = Query(default=None)):
    if not token or not token.strip():
        raise ApiError(status_code=401, code="auth_required", message="Token nao informado", field="token")

    user = _get_user_by_token(token.strip())
    if not user or not user.is_active:
        raise ApiError(status_code=401, code="invalid_token", message="Token invalido", field="token")
    if not is_admin(user.role):
        raise ApiError(status_code=403, code="forbidden", message="Acesso restrito a admin", field="token")
    return FileResponse(_TEMPLATE_PATH, media_type="text/html")
