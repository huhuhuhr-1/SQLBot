import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from apps.system.crud.user import get_user_by_account
from apps.system.models.system_model import AuthenticationModel, UserWsModel, WorkspaceModel
from apps.system.models.user import UserModel, UserPlatformModel
from common.core.config import settings
from common.core.deps import SessionDep, Trans
from common.core.security import create_access_token, default_md5_pwd
from common.utils.time import get_timestamp
from common.utils.utils import SQLBotLogUtil

router = APIRouter(tags=["system_authentication"], prefix="/system/authentication")


AUTH_NAME_TYPE = {
    "cas": 1,
    "oidc": 2,
    "ldap": 3,
    "oauth2": 4,
    "saml2": 5,
}
AUTH_TYPE_NAME = {v: k for k, v in AUTH_NAME_TYPE.items()}


class AuthenticationSaveDTO(BaseModel):
    id: int
    type: int
    name: str
    config: str


class AuthenticationEnableDTO(BaseModel):
    id: int
    enable: bool


class AuthenticationStatusDTO(BaseModel):
    type: int
    name: str = ""
    config: str = ""


class OidcSsoDTO(BaseModel):
    code: str | None = None
    state: str | None = None
    redirect_uri: str | None = None


def _safe_json_loads(config: str | None) -> dict[str, Any]:
    if not config:
        return {}
    try:
        return json.loads(config)
    except Exception:
        return {}


def _find_by_type(session: SessionDep, auth_type: int) -> AuthenticationModel | None:
    return session.exec(select(AuthenticationModel).where(AuthenticationModel.type == auth_type)).first()


def _upsert_auth(session: SessionDep, dto: AuthenticationSaveDTO) -> AuthenticationModel:
    model = _find_by_type(session, dto.type)
    if not model:
        model = AuthenticationModel(
            id=dto.type,
            type=dto.type,
            name=dto.name,
            config=dto.config,
            enable=False,
            valid=False,
            create_time=get_timestamp(),
        )
        session.add(model)
    else:
        model.name = dto.name
        model.config = dto.config
    session.commit()
    session.refresh(model)
    return model


async def _get_oidc_metadata(metadata_url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(metadata_url)
        resp.raise_for_status()
        return resp.json()


def _build_oidc_state(origin_type: int) -> str:
    exp = int(time.time()) + 300
    payload = {
        "origin": origin_type,
        "nonce": secrets.token_urlsafe(16),
        "exp": exp,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def _build_oidc_login_url(auth: AuthenticationModel) -> str:
    cfg = _safe_json_loads(auth.config)
    metadata_url = cfg.get("metadata_url")
    client_id = cfg.get("client_id")
    redirect_uri = cfg.get("redirect_uri")
    scope = cfg.get("scope", "openid profile email")
    if not metadata_url or not client_id or not redirect_uri:
        raise HTTPException(status_code=400, detail="oidc config incomplete")
    metadata = await _get_oidc_metadata(metadata_url)
    auth_endpoint = metadata.get("authorization_endpoint")
    if not auth_endpoint:
        raise HTTPException(status_code=400, detail="oidc metadata missing authorization_endpoint")
    state = _build_oidc_state(2)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
    }
    return f"{auth_endpoint}?{urlencode(params)}"


def _parse_user_claims(cfg: dict[str, Any], claims: dict[str, Any]) -> dict[str, str]:
    mapping = _safe_json_loads(cfg.get("mapping")) if isinstance(cfg.get("mapping"), str) else {}
    account_key = mapping.get("account", "preferred_username")
    email_key = mapping.get("email", "email")
    name_key = mapping.get("name", "name")
    account = (
        claims.get(account_key)
        or claims.get("preferred_username")
        or claims.get("email")
        or claims.get("sub")
    )
    email = claims.get(email_key) or claims.get("email") or f"{account}@oidc.local"
    name = claims.get(name_key) or claims.get("name") or str(account)
    if not account:
        raise HTTPException(status_code=400, detail="oidc user account claim missing")
    return {"account": str(account), "email": str(email), "name": str(name)}


def _ensure_ws_binding(session: SessionDep, uid: int, oid: int) -> None:
    model = session.exec(select(UserWsModel).where(UserWsModel.uid == uid, UserWsModel.oid == oid)).first()
    if model:
        return
    ws_model = session.exec(select(WorkspaceModel).where(WorkspaceModel.id == oid)).first()
    if not ws_model:
        any_ws = session.exec(select(WorkspaceModel).order_by(WorkspaceModel.id)).first()
        oid = any_ws.id if any_ws else 1
    session.add(UserWsModel(uid=uid, oid=oid, weight=0))
    session.commit()


def _resolve_target_oid(session: SessionDep) -> int:
    ws = session.exec(select(WorkspaceModel).order_by(WorkspaceModel.id)).first()
    return ws.id if ws else 1


def _upsert_platform_user(
    session: SessionDep,
    account: str,
    email: str,
    name: str,
    platform_uid: str,
    origin: int = 2,
) -> UserModel:
    user = get_user_by_account(session=session, account=account)
    if user:
        db_user = session.get(UserModel, user.id)
        if not db_user:
            raise HTTPException(status_code=400, detail="user not found")
        if db_user.status != 1:
            raise HTTPException(status_code=400, detail="user disabled")
        if db_user.oid == 0:
            db_user.oid = _resolve_target_oid(session)
            session.commit()
            session.refresh(db_user)
        _ensure_ws_binding(session, db_user.id, db_user.oid)
        return db_user

    oid = _resolve_target_oid(session)
    db_user = UserModel(
        account=account,
        oid=oid,
        name=name[:100],
        password=default_md5_pwd(),
        email=email[:255],
        status=1,
        origin=origin,
        language="zh-CN",
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    _ensure_ws_binding(session, db_user.id, db_user.oid)
    platform = UserPlatformModel(uid=db_user.id, origin=origin, platform_uid=platform_uid)
    session.add(platform)
    session.commit()
    return db_user


async def _exchange_oidc_code(cfg: dict[str, Any], code: str, redirect_uri: str | None) -> dict[str, Any]:
    metadata = await _get_oidc_metadata(cfg["metadata_url"])
    token_endpoint = metadata.get("token_endpoint")
    userinfo_endpoint = metadata.get("userinfo_endpoint")
    issuer = metadata.get("issuer")
    jwks_uri = metadata.get("jwks_uri")
    if not token_endpoint:
        raise HTTPException(status_code=400, detail="oidc metadata missing token_endpoint")
    post_data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": redirect_uri or cfg["redirect_uri"],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        token_resp = await client.post(token_endpoint, data=post_data)
        token_resp.raise_for_status()
        token_json = token_resp.json()

        id_token = token_json.get("id_token")
        access_token = token_json.get("access_token")
        claims: dict[str, Any] = {}
        if id_token and jwks_uri:
            signing_key = jwt.PyJWKClient(jwks_uri).get_signing_key_from_jwt(id_token).key
            claims = jwt.decode(
                id_token,
                signing_key,
                algorithms=["RS256", "ES256", "HS256"],
                audience=cfg["client_id"],
                issuer=issuer,
            )
        elif id_token:
            claims = jwt.decode(id_token, options={"verify_signature": False, "verify_exp": True})

        if (not claims) and userinfo_endpoint and access_token:
            info_resp = await client.get(
                userinfo_endpoint, headers={"Authorization": f"Bearer {access_token}"}
            )
            info_resp.raise_for_status()
            claims = info_resp.json()
        if not claims:
            raise HTTPException(status_code=400, detail="oidc user claims unavailable")
        return claims


@router.get("")
async def get_authentication_list(session: SessionDep):
    rows = session.exec(select(AuthenticationModel)).all()
    row_map = {row.type: row for row in rows}
    result: list[dict[str, Any]] = []
    for name, auth_type in AUTH_NAME_TYPE.items():
        row = row_map.get(auth_type)
        result.append(
            {
                "id": auth_type,
                "name": name,
                "type": auth_type,
                "valid": bool(row.valid) if row else False,
                "enable": bool(row.enable) if row else False,
            }
        )
    return result


@router.get("/{auth_type}")
async def get_authentication_detail(session: SessionDep, auth_type: int):
    row = _find_by_type(session, auth_type)
    if not row:
        return {"id": auth_type, "type": auth_type, "name": AUTH_TYPE_NAME.get(auth_type, ""), "config": ""}
    return row


@router.post("")
async def save_authentication(session: SessionDep, dto: AuthenticationSaveDTO):
    return _upsert_auth(session, dto)


@router.put("")
async def update_authentication(session: SessionDep, dto: AuthenticationSaveDTO):
    return _upsert_auth(session, dto)


@router.patch("/enable")
async def set_authentication_enable(session: SessionDep, dto: AuthenticationEnableDTO):
    row = _find_by_type(session, dto.id)
    if not row:
        raise HTTPException(status_code=404, detail="authentication not found")
    row.enable = dto.enable
    session.commit()
    return True


@router.patch("/status")
async def validate_authentication(session: SessionDep, dto: AuthenticationStatusDTO):
    row = _find_by_type(session, dto.type)
    if dto.config:
        config = dto.config
    elif row:
        config = row.config
    else:
        config = ""
    if not config:
        return False
    cfg = _safe_json_loads(config)
    valid = False
    try:
        if dto.type == 2:
            await _get_oidc_metadata(cfg["metadata_url"])
            valid = True
        else:
            valid = True
    except Exception as e:
        SQLBotLogUtil.error(f"authentication validation failed: {e}")
        valid = False
    if row:
        row.valid = valid
        session.commit()
    return valid


@router.get("/platform/status")
async def get_platform_status(session: SessionDep):
    rows = session.exec(select(AuthenticationModel)).all()
    row_map = {row.type: row for row in rows}
    result: list[dict[str, Any]] = []
    for auth_type in sorted(AUTH_TYPE_NAME.keys()):
        row = row_map.get(auth_type)
        result.append(
            {
                "id": auth_type,
                "name": AUTH_TYPE_NAME[auth_type],
                "enable": bool(row.enable) if row else False,
                "valid": bool(row.valid) if row else False,
            }
        )
    return result


@router.get("/login/{auth_type}")
async def start_platform_login(session: SessionDep, auth_type: int):
    row = _find_by_type(session, auth_type)
    if not row or not row.enable:
        raise HTTPException(status_code=400, detail="authentication is disabled")
    if auth_type == 2:
        return await _build_oidc_login_url(row)
    raise HTTPException(status_code=400, detail="authentication type not supported in community edition")


@router.post("/sso/{auth_type}")
async def platform_sso_callback(session: SessionDep, trans: Trans, auth_type: int, dto: OidcSsoDTO):
    if auth_type != 2:
        raise HTTPException(status_code=400, detail="authentication type not supported")
    row = _find_by_type(session, 2)
    if not row or not row.enable:
        raise HTTPException(status_code=400, detail=trans("i18n_authentication.not_enabled"))
    if not dto.code:
        raise HTTPException(status_code=400, detail="missing code")
    cfg = _safe_json_loads(row.config)
    required_keys = ["metadata_url", "client_id", "client_secret", "redirect_uri"]
    for key in required_keys:
        if not cfg.get(key):
            raise HTTPException(status_code=400, detail=f"oidc config missing {key}")
    claims = await _exchange_oidc_code(cfg, dto.code, dto.redirect_uri)
    profile = _parse_user_claims(cfg, claims)
    platform_uid = str(claims.get("sub") or profile["account"])
    user = _upsert_platform_user(
        session,
        account=profile["account"],
        email=profile["email"],
        name=profile["name"],
        platform_uid=platform_uid,
        origin=2,
    )
    if not user.oid or user.oid == 0:
        raise HTTPException(status_code=400, detail=trans("i18n_login.no_associated_ws", msg=trans("i18n_concat_admin")))
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"id": user.id, "account": user.account, "oid": user.oid}, access_token_expires)
    exp_ts = int((datetime.now(timezone.utc) + access_token_expires).timestamp())
    return {
        "access_token": token,
        "token_type": "bearer",
        "exp": exp_ts,
        "time": int(time.time()),
        "platform_info": {"account": user.account},
    }
