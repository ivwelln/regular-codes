from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import SessionCipherDep, SessionDep, StoreDep, require_admin
from app.clients.gamestores import StoreUnavailableError
from app.crud.accounts import list_accounts
from app.services.accounts import InvalidShopSessionError, save_account

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)], include_in_schema=False)

ERRORS = {
    "invalid_session": "Магазин не принял сессию: войдите на сайт заново и скопируйте свежую.",
    "store_unavailable": "Магазин сейчас недоступен, попробуйте позже.",
}


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_page(
    request: Request, session: SessionDep, saved: str | None = None, error: str | None = None
):
    accounts = await list_accounts(session)
    context = {"accounts": accounts, "saved": saved, "error": ERRORS.get(error or "")}
    return templates.TemplateResponse(request, "accounts.html", context)


@router.post("/accounts")
async def add_account(
    session: SessionDep,
    store: StoreDep,
    cipher: SessionCipherDep,
    shop_session: Annotated[str, Form()],
) -> RedirectResponse:
    try:
        account = await save_account(session, store, cipher, shop_session.strip())
    except InvalidShopSessionError:
        return _back_to_accounts(error="invalid_session")
    except StoreUnavailableError:
        return _back_to_accounts(error="store_unavailable")
    return _back_to_accounts(saved=account.username)


def _back_to_accounts(**params: str) -> RedirectResponse:
    return RedirectResponse(f"/admin/accounts?{urlencode(params)}", status_code=303)
