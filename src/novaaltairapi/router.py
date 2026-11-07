from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
import jwt
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from novaaltairapi.config import settings
from novaaltairapi.db import get_session
from novaaltairapi.models import Users
from novaaltairapi.schemas import (UserIn, UserOut, UserInUsername, NewKeyIn, Key, KeyExtend, TokenResponse, KeyRemoveIn, RefreshToken)
from novaaltairapi.security import hash_password, create_tokens, verify_access, verify_password
from novaaltairapi.repository import (found_username, get_or_create_user, set_not_new, get_key, get_keys, register, login, get_by_username)
from novaaltairapi.xui import create_key, delete_key, extend_key

router = APIRouter()


@router.get("/get/username/{username}", response_model=UserOut)
async def get_user_username(username: str, session: AsyncSession = Depends(get_session), _auth_info: dict = Depends(verify_access)):
    user = await found_username(session, username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.post("/user/new", response_model=UserOut, status_code=201)
async def new_user(new_user: UserIn, session: AsyncSession = Depends(get_session), _auth_info: dict = Depends(verify_access)):
    user = await get_or_create_user(session, new_user.username, hash_password(new_user.password), referred_by_user=new_user.referred_by_user)
    if not user:
        raise HTTPException(status_code=409, detail="Пользователь с таким телеграм id уже существует.")
    await session.commit()
    return user

@router.post("/user/register", response_model=UserOut)
async def user_register(new_user: UserIn, session: AsyncSession = Depends(get_session)):
    user = await register(session, new_user.username, hash_password(new_user.password))

    if not user:
        raise HTTPException(status_code=409, detail="Пользовать с эти логином уже существует")

    await session.commit()
    return user


@router.post("/user/login", response_model=TokenResponse)
async def user_login(new_user: UserIn, session: AsyncSession = Depends(get_session)):
    access_token, refresh_token = create_tokens(new_user.username.strip().lower())

    user = await login(session, new_user.username.strip().lower(), new_user.password, refresh_token=hash_password(refresh_token))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, user=user)


@router.post("/user/set/not_new", response_model=UserOut, status_code=201)
async def set_user_not_new(user_: UserInUsername, session: AsyncSession = Depends(get_session), _auth_info: dict = Depends(verify_access)):
    user = await set_not_new(session, user_.username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    await session.commit()
    return user

@router.post("/user/key/add", response_model=Key, status_code=201)
async def user_add_key(new_key: NewKeyIn, session: AsyncSession = Depends(get_session), _auth_info: dict = Depends(verify_access)):
    key = await create_key(session, new_key.username, new_key.email, new_key.day_expiry, payment_id=new_key.payment_id)
    await session.commit()
    return key

@router.post("/user/key/remove", status_code=201)
async def user_remove_key(key: KeyRemoveIn, session: AsyncSession = Depends(get_session), _auth_info: dict = Depends(verify_access)):
    await delete_key(session, key.email.strip().lower())
    await session.commit()
    return

@router.post("/user/key/extend", response_model=Key, status_code=201)
async def user_extend_key(key: KeyExtend, session: AsyncSession = Depends(get_session), _auth_info: dict = Depends(verify_access)):
    new_key = await extend_key(session, key.email.strip().lower(), key.day_expiry, key.payment_id)
    await session.commit()
    return new_key

    
@router.get("/user/key/get/{email}", response_model=Key)
async def get_key_(email: str, session: AsyncSession = Depends(get_session), _auth_info: dict = Depends(verify_access)):
    key = await get_key(session=session, email=email.strip().lower())
    if not key:
        raise HTTPException(status_code=404, detail="Ключ не найден")
    return key

@router.get("/user/keys/{username}", response_model=list[Key])
async def get_user_keys(username: str, session: AsyncSession = Depends(get_session), _auth_info: dict = Depends(verify_access)):
    keys = await get_keys(session, username.strip().lower())
    if not keys:
        raise HTTPException(status_code=404, detail="Ключи не найдены")
    return keys


@router.post("/user/logout", status_code=201)
async def user_logout(session: AsyncSession = Depends(get_session), auth_info: dict = Depends(verify_access)):
    username = auth_info["identity"]
    
    user = await session.scalar(select(Users).where(Users.username == username))
    if user:
        user.refresh_token_hash = None
        session.add(user)
        await session.commit()
        
    return


@router.post("/user/refresh", response_model=TokenResponse)
async def refresh_access_token(refresh_token: RefreshToken, session: AsyncSession = Depends(get_session)):
    try:
        jwt.decode(refresh_token.refresh_token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Срок действия refresh-токена истек")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Недействительный refresh-токен")

    user = await get_by_username(session, refresh_token.username)
    if user is None or not verify_password(user.refresh_token_hash, refresh_token.refresh_token):
        return None

    new_access_token, new_refresh_token = create_tokens(refresh_token.username)

    user.refresh_token_hash = hash_password(new_refresh_token)
    session.add(user)
    await session.commit()

    return TokenResponse(access_token=new_access_token, refresh_token_hash=new_refresh_token, user=user)


def build_deeplink(client: str, sub_url: str, email: str) -> str:
    encoded_sub = quote(sub_url, safe="")

    match client.strip().lower():
        case "happ":
            return f"happ://add/{sub_url}"
        case "v2rayng":
            return f"v2rayng://install-config?url={encoded_sub}"
        case "hiddify":
            return f"hiddify://import/{sub_url}#{email}"
        case "singbox":
            return f"sing-box://import-remote-profile?url={encoded_sub}#{email}"
        case "v2raytun":
            return f"v2raytun://import/{sub_url}"
        case "incy":
            return f"incy://import/{sub_url}"


@router.get("/connect", response_class=HTMLResponse)
async def redirected_to_app(client: str = Query(...), sub: str = Query(...), email: str = Query("VPN")):
    deeplink = build_deeplink(client=client, sub_url=sub, email=email)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Подключение...</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script>
            window.onload = function() {{
                window.location.href = "{deeplink}";
                setTimeout(function() {{
                    window.close();
                }}, 3500);
            }};
        </script>
        <style>
            body {{ background: #121212; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }}
            a {{ color: #7b61ff; text-decoration: none; border: 1px solid #7b61ff; padding: 12px 24px; border-radius: 8px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <h3>Открываем приложение...</h3>
        <p>Если приложение не открылось автоматически, нажмите кнопку ниже:</p>
        <a href="{deeplink}">Подключиться в {client}</a>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)