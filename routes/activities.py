from fastapi import APIRouter, HTTPException, Depends

import schemas
from apr_flow import list_activities, get_activity_suggestions
from auth import get_current_user


router = APIRouter(prefix="/v1/activities", tags=["Activities"])


@router.get("", response_model=list[schemas.ActivityOut])
def listar_atividades(_user=Depends(get_current_user)):
    try:
        return list_activities()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{activity_id}/suggestions", response_model=schemas.ActivitySuggestions)
def sugerir_por_atividade(activity_id: str, _user=Depends(get_current_user)):
    try:
        data = get_activity_suggestions(activity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not data:
        raise HTTPException(status_code=404, detail="Atividade nao encontrada")
    return data
