from __future__ import annotations

from capital_os.domain.accounts.service import create_account_entry
from capital_os.schemas.tools import CreateAccountIn, CreateAccountOut


def handle(payload: dict) -> CreateAccountOut:
    req = CreateAccountIn.model_validate(payload)
    out = create_account_entry(req.model_dump())
    return CreateAccountOut.model_validate(out)
