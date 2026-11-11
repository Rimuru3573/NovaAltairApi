from datetime import datetime, timedelta, timezone
import py3xui
import uuid
from fastapi import HTTPException
from novaaltairapi.models import Keys
from sqlalchemy.ext.asyncio import AsyncSession
from novaaltairapi.config import settings
from novaaltairapi.repository import add_key, remove_key, extend_key_db
from sqlalchemy import select

from novaaltairapi.schemas import KeyExtend, NewKeyIn

api = py3xui.AsyncApi(settings.xui_path, settings.xui_login, settings.xui_password, use_tls_verify=False)



async def add_hwid(api: py3xui.AsyncApi, email: str, limit_hwid: int):
    try:
        await api.client._post(
            api.client._url("panel/api/clients/bulkAdjust"),
                {"Accept": "application/json"},
                {"emails": [email], "limitHwid": limit_hwid},
            )
    except Exception:
        raise HTTPException(status_code=500, detail="Не удалось выставить лимит устройств")

async def create_key(session: AsyncSession, new_key: NewKeyIn) -> Keys:
        await api.login()
        time_datetime = datetime.now(timezone.utc) + timedelta(days=new_key.day_expiry)
        sub_id = uuid.uuid4().hex
        client_uuid = str(uuid.uuid4())

        client = py3xui.Client(
            id=client_uuid,
            email=new_key.email,
            enable=True,
            expiry_time=int(time_datetime.timestamp() * 1000),
            sub_id=sub_id,
        )
        data = {
            "client": client.model_dump(by_alias=True, exclude_defaults=True),
            "inboundIds": settings.inbound_ids,
        }
        try:
            await api.client._post(api.client._url("panel/api/clients/add"),
                            {"Accept": "application/json"}, data)
        except ValueError:
            raise HTTPException(status_code=409, detail="Неверное имя пользователя и/или такой полльзователь уже существует")
        except Exception:
            raise HTTPException(status_code=500, detail="Ошибка панели")
        
        await add_hwid(api=api, email=new_key.email, limit_hwid=new_key.limit_hwid)
                
        sub_link = f"{settings.xui_sub_base}/{sub_id}"
        
        try:
            key = await add_key(session, new_key.username.strip().lower(), new_key.email, sub_id, sub_link, time_datetime, new_key.payment_id)
            return key
        except Exception:
            await delete_key(session, new_key.email)
            raise HTTPException(status_code=400, detail="Ошибка добавления ползователя в базу данных")


async def delete_key(session: AsyncSession, email: str):
    await api.login()
    inbound = await api.inbound.get_by_id(settings.inbound_ids[0])
    client = None
    for c in inbound.settings.clients:
        if c.email == email:
            client = c
            break
    client_uuid = client.id
    try:
        await api.client.delete(settings.inbound_ids[0], client_uuid)
    except Exception:
        raise HTTPException(status_code=409, detail="Ошибка удаления конфига в панели")

    try: 
        await remove_key(session, email.strip().lower())
    except Exception:
        raise HTTPException(status_code=409, detail="Ошибка удаления конфига в базе данных")


async def reload_key(session: AsyncSession, email: str, username: str) -> Keys:
    await api.login()

    time_datetime = await session.scalar(select(Keys.expiry_time).where(Keys.email == email))
    old_sub_id = await session.scalar(select(Keys.sub_id).where(Keys.email == email))
    hwid_status = await api.client._get(
        f"{settings.xui_sub_base}/{old_sub_id}/hwid-status",
        {"Accept": "application/json"},
        skip_check=True,
    )
    limit_hwid: int = hwid_status.json().get("limit", 0)
    await delete_key(session, email)
    await session.commit()


    sub_id = uuid.uuid4().hex
    client_uuid = str(uuid.uuid4())

    client = py3xui.Client(
        id=client_uuid,
        email=email,
        enable=True,
        expiry_time=int(time_datetime.timestamp() * 1000),
        sub_id=sub_id,
    )
    data = {
        "client": client.model_dump(by_alias=True, exclude_defaults=True),
        "inboundIds": settings.inbound_ids,
    }
    try:
        await api.client._post(api.client._url("panel/api/clients/add"), {"Accept": "application/json"}, data)
    except ValueError:
        raise HTTPException(status_code=409, detail="Неверное имя пользователя и/или такой полльзователь уже существует")
    except Exception:
        raise HTTPException(status_code=500, detail="Ошибка панели")


    await add_hwid(api=api, email=email, limit_hwid=limit_hwid)

    sub_link = f"{settings.xui_sub_base}/{sub_id}"
    try:
        key = await add_key(session, username, email, sub_id, sub_link, time_datetime, None)
        return key
    except Exception:
        await delete_key(session, email)
        raise HTTPException(status_code=400, detail="Ошибка добавления ползователя в базу данных")    



async def extend_key(session:AsyncSession, key: KeyExtend) -> Keys:
    await api.login()


    inbound = await api.inbound.get_by_id(settings.inbound_ids[0])
    client = None
    for c in inbound.settings.clients:
        if c.email == key.email:
            client = c
            break

    client_by_email = await api.client.get_by_email(key.email)


    expiry_db = await session.scalar(select(Keys.expiry_time).where(Keys.email == key.email))
    now = datetime.now(timezone.utc)
    if expiry_db.tzinfo is None:
        expiry_db = expiry_db.replace(tzinfo=timezone.utc)
    start = max(expiry_db, now)
    new_expiry = start + timedelta(days=key.day_expiry)
    client_by_email.expiry_time = int(new_expiry.timestamp() * 1000)
        

    client_uuid = client.id
    client_by_email.id = client_uuid
    client_by_email.enable = True


    try:
        await api.client.update(client_by_email.id, client_by_email)
        await api.client.reset_stats(settings.inbound_ids[0], key.email)
    except Exception:
        raise HTTPException(status_code=409, detail="Ошибка продления конфига в панели")
    await add_hwid(api=api, email=key.email, limit_hwid=key.limit_hwid)


    try:
        key = await extend_key_db(session, key.email, new_expiry, key.payment_id)
        return key
    except Exception:
        raise HTTPException(status_code=409, detail="Ошибка продления конфига в базе данных")



# TODO: написать функцию для получения устройств и покупки дополнительных

async def get_hwids(email: str) -> list[str]:
    await api.login()

    response = await api.client._post(
        api.client._url(f"panel/api/clients/hwids/{email}"),
        {"Accept": "application/json"},
        {},
    )
    devices = response.json().get("obj") or []

    result = []
    for i, device in enumerate(devices, start=1):
        model = device.get("deviceModel") or "Unknown"
        user_agent = device.get("userAgent") or "Unknown"
        result.append(f"{i}. {model} — {user_agent}")

    return result

async def get_limithwid(session: AsyncSession, email: str) -> int:
    old_sub_id = await session.scalar(select(Keys.sub_id).where(Keys.email == email))
    hwid_status = await api.client._get(
            f"{settings.xui_sub_base}/{old_sub_id}/hwid-status",
            {"Accept": "application/json"},
            skip_check=True,
        )
    return hwid_status.json().get("limit", 0)


# TODO: починит и протестировать 
# async def delete_hwid(email: str, id: int):
#     await api.login()
#     url = f"{settings.xui_path}panel/api/clients/hwids/{email}/{id}"
#     async with aiohttp.ClientSession() as session:
#         async with session.delete(url) as response:
#             response.raise_for_status()
#             data = await response.json(content_type=None)
#     if not data.get("success"):
#         raise ValueError(data.get("msg"))
 