from fastapi import APIRouter

import schemas

router = APIRouter(prefix="/api/seller", tags=["Seller Activation"])


def _calculate_progress(completed: int, total: int) -> int:
    if total <= 0:
        return 0
    percent = round((completed / total) * 100)
    return max(0, min(100, int(percent)))


def _build_status_message(completed: int, total: int, pending: list[str]) -> str:
    if total == completed:
        return "Checklist completo: todas as etapas foram concluídas."
    if completed == 0:
        return "Checklist ainda não iniciado — revise pendências como sem CEP, sem Stripe e demais dados obrigatórios."
    joined = ", ".join(pending)
    return f"Pendências detectadas: {joined}."


@router.post("/activation-status", response_model=schemas.SellerActivationStatusOut)
def activation_status(payload: schemas.SellerActivationStatusPayload):
    total_items = len(payload.checklist)
    completed_items = sum(1 for item in payload.checklist if item.completed)
    pending_items = [item.label for item in payload.checklist if not item.completed]

    progress_percent = _calculate_progress(completed_items, total_items)
    status_flag = "ready" if completed_items == total_items else "pending"
    message = _build_status_message(completed_items, total_items, pending_items)

    return {
        "seller_id": payload.seller_id,
        "status": status_flag,
        "total_items": total_items,
        "completed_items": completed_items,
        "progress_percent": progress_percent,
        "pending_items": pending_items,
        "checklist": payload.checklist,
        "message": message,
    }
