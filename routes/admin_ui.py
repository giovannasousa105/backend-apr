from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from models import User
from auth import require_admin
from request_guards import apply_rate_limit, request_identity

router = APIRouter(tags=["Admin UI"])

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "perigos_defaults.html"


@router.get("/admin/perigos-defaults")
def perigos_defaults_page(
    request: Request,
    _admin: User = Depends(require_admin),
):
    apply_rate_limit("admin_perigos_defaults_page", request_identity(request, str(_admin.id)), limit=20, window_seconds=60)
    return FileResponse(_TEMPLATE_PATH, media_type="text/html")
