from datetime import datetime
from novaaltairapi.models import Users, Keys
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from novaaltairapi.security import verify_password


async def get_by_username(session: AsyncSession, username: str) -> Users | None:
    user = await session.scalar(select(Users).where(Users.username == username.strip().lower()))
    if user: return user
    else: return None


async def get_or_create_user(session: AsyncSession, username: str, password_hash: str, referred_by_user: str) -> Users | None:
    user = await get_by_username(session, username)

    if user:
        return user

    user = Users(username=username.strip().lower(), password_hash=password_hash, referred_by_user=referred_by_user)
    session.add(user)
    await session.flush()
    return user
        
        

async def login(session: AsyncSession, username: str, password: str, refresh_token_hash: str) -> Users | None:
    user = await get_by_username(session, username)

    if user is None or not verify_password(user.password_hash, password):
        return None

    user.refresh_token_hash = refresh_token_hash
    await session.flush()
    return user

async def register(session: AsyncSession, username: str, password_hash: str) -> Users | None:
    user = await get_by_username(session, username)
    if user is not None:
        return None
    
    user = Users(username=username.strip().lower(), password_hash=password_hash)
    session.add(user)
    await session.flush()
    return user


async def found_username(session: AsyncSession, username: str) -> Users | None:
    user = await get_by_username(session, username)
    if user is None:
        return None
        
    return user


async def set_not_new(session: AsyncSession, username: str) -> Users | None:
    user = await get_by_username(session, username)
    if not user:
        return None
    
    user.is_new = False
    await session.flush()
    
    return user


async def add_key(session: AsyncSession, username: str, email: str, sub_id: str, sub_link: str, expiry_time: datetime, payment_id: str | None ) -> Keys:

    key = Keys(email=email.strip().lower(),
               sub_id=sub_id,
               expiry_time=expiry_time,
               payment_id=payment_id,
               user_username=username, 
               sub_link=sub_link)
    
    session.add(key)
    await session.flush()
    return key

async def remove_key(session: AsyncSession, email: str):
    key = await session.scalar(select(Keys).where(Keys.email == email.strip().lower()))
    await session.delete(key)
    await session.flush()

async def extend_key_db(session: AsyncSession, email: str, new_expiry: datetime, payment_id: str | None) -> Keys:
    key = await session.scalar(select(Keys).where(Keys.email == email.strip().lower()))
    key.expiry_time = new_expiry
    key.payment_id = payment_id

    await session.flush()
    return key

async def get_key(session: AsyncSession, email: str) -> Keys | None:
    key = await session.scalar(select(Keys).where(Keys.email == email.strip().lower()))
    if not key:
        return None
    return key

async def get_keys(session: AsyncSession, username: str) -> list[Keys]:
    keys = await session.scalars(
        select(Keys).where(Keys.user_username == username.strip().lower())
    )
    return list(keys)

async def get_count_referrals(session: AsyncSession, username: str) -> int:
    count = await session.scalar(
        select(func.count()).where(
            Users.referred_by_user == username,
            Users.is_referral_rewarded == False
        )
    )

    return count

async def get_count_referrals_all(session: AsyncSession, username: str) -> int:
    count = await session.scalar(select(func.count()).where(Users.referred_by_user == username))
    return count


async def referral_rewarded(session: AsyncSession, username: str):
    await session.execute(update(Users).where(
        Users.referred_by_user == username,
        Users.is_referral_rewarded.is_(False)
    ).values(is_referral_rewarded=True))

    await session.flush()






# Admin Functional:
# async def set_new(session: AsyncSession, username: str) -> Users:
#     user = await get_by_username(session, username)
    
#     user.is_new = True
#     await session.flush()
    
#     return user