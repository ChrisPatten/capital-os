from __future__ import annotations

from capital_os.domain.accounts.service import update_account_profile
from capital_os.schemas.tools import UpdateAccountProfileIn, UpdateAccountProfileOut


def handle(payload: dict) -> UpdateAccountProfileOut:
    req = UpdateAccountProfileIn.model_validate(payload)
    out = update_account_profile(req.model_dump(exclude_unset=True))
    return UpdateAccountProfileOut.model_validate(out)
