from rbac import (
    ROLE_ADMIN,
    ROLE_TECNICO,
    ROLE_VISUALIZADOR,
    can_write,
    normalize_role,
)


def test_normalize_role_aliases():
    assert normalize_role("user") == ROLE_TECNICO
    assert normalize_role("técnico") == ROLE_TECNICO
    assert normalize_role("viewer") == ROLE_VISUALIZADOR
    assert normalize_role("admin") == ROLE_ADMIN


def test_can_write_for_supported_roles():
    assert can_write(ROLE_ADMIN) is True
    assert can_write(ROLE_TECNICO) is True
    assert can_write(ROLE_VISUALIZADOR) is False


def test_can_write_rejects_invalid_role():
    assert can_write("invalid-role") is False
