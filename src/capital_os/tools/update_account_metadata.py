from __future__ import annotations

from capital_os.domain.accounts.service import update_account_metadata
from capital_os.schemas.tools import UpdateAccountMetadataIn, UpdateAccountMetadataOut


def handle(payload: dict) -> UpdateAccountMetadataOut:
    req = UpdateAccountMetadataIn.model_validate(payload)
    out = update_account_metadata(req.model_dump())
    return UpdateAccountMetadataOut.model_validate(out)
