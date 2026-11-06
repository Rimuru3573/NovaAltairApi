from datetime import datetime, timedelta, timezone
import py3xui
import uuid
from fastapi import HTTPException
from novaaltairapi.models import Keys
from sqlalchemy.ext.asyncio import AsyncSession
from novaaltairapi.config import settings
from novaaltairapi.repository import add_key, remove_key, extend_key_db
from sqlalchemy import select

api = py3xui.AsyncApi(settings.xui_path, settings.xui_login, settings.xui_password, use_tls_verify=False)

async def create_key(session: AsyncSession, username: str, email: str, day_expiry: int, payment_id=None) -> Keys:
        await api.login()
        time_datetime = datetime.now(timezone.utc) + timedelta(days=day_expiry)
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
            await api.client._post(api.client._url("panel/api/clients/add"),
                            {"Accept": "application/json"}, data)
        except ValueError:
            raise HTTPException(status_code=409, detail="Неверное имя пользователя и/или такой полльзователь уже существует")
        except Exception:
            raise HTTPException(status_code=500, detail="Ошибка панели")

        sub_link = f"{settings.xui_sub_base}/{sub_id}"
        
        try:
            key = await add_key(session, username.strip().lower(), email, sub_id, sub_link, time_datetime, payment_id)
            return key
        except Exception:
            await delete_key(session, email)
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


async def extend_key(session:AsyncSession, email: str, day_expiry: int, payment_id: str | None) -> Keys:
    await api.login()


    inbound = await api.inbound.get_by_id(settings.inbound_ids[0])
    client = None
    for c in inbound.settings.clients:
        if c.email == email:
            client = c
            break

    client_by_email = await api.client.get_by_email(email)


    expiry_db = await session.scalar(select(Keys.expiry_time).where(Keys.email == email))
    start = max(datetime.fromtimestamp(expiry_db / 1000, tz=timezone.utc), datetime.now(timezone.utc)) if client.expiry_time else datetime.now(timezone.utc)
    new_expiry = start + timedelta(days=day_expiry)
    client_by_email.expiry_time = int(new_expiry.timestamp() * 1000)
        

    client_uuid = client.id
    client_by_email.id = client_uuid
    client_by_email.enable = True


    try:
        await api.client.update(client_by_email.id, client_by_email)
        await api.client.reset_stats(settings.inbound_ids[0], email)
    except Exception:
        raise HTTPException(status_code=409, detail="Ошибка продления конфига в панели")

    try:
        key = await extend_key_db(session, email, new_expiry, payment_id)
        return key
    except Exception:
        raise HTTPException(status_code=409, detail="Ошибка продления конфига в базе данных")