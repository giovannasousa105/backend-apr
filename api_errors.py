from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    field: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
        }


def missing_fields_error(fields: list[str]) -> ApiError:
    if len(fields) == 1:
        field = fields[0]
        return ApiError(
            status_code=400,
            code="missing_field",
            message=f"Campo obrigatorio ausente: {field}",
            field=field,
        )
    joined = ", ".join(fields)
    return ApiError(
        status_code=400,
        code="missing_fields",
        message=f"Campos obrigatorios ausentes: {joined}",
        field=",".join(fields),
    )


def validation_error(message: str, field: Optional[str] = None, status_code: int = 400) -> ApiError:
    return ApiError(status_code=status_code, code="validation_error", message=message, field=field)
