from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_activation_status_pending_message_and_progress():
    payload = {
        "seller_id": "seller-123",
        "checklist": [
            {"label": "Documento enviado", "completed": False},
            {"label": "Termo assinado", "completed": False},
        ],
    }

    response = client.post("/api/seller/activation-status", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "pending"
    assert data["progress_percent"] == 0
    assert data["total_items"] == 2
    assert data["completed_items"] == 0
    assert data["pending_items"] == ["Documento enviado", "Termo assinado"]
    assert (
        data["message"]
        == "Checklist ainda não iniciado — revise pendências como sem CEP, sem Stripe e demais dados obrigatórios."
    )


def test_activation_status_ready_message():
    payload = {
        "seller_id": "seller-xyz",
        "checklist": [
            {"label": "Documento enviado", "completed": True},
            {"label": "Termo assinado", "completed": True},
        ],
    }

    response = client.post("/api/seller/activation-status", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ready"
    assert data["progress_percent"] == 100
    assert data["pending_items"] == []
    assert data["message"] == "Checklist completo: todas as etapas foram concluídas."
