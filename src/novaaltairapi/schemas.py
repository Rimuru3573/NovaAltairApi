from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserIn(BaseModel):
    username: str
    password: str
    referred_by_user: int | None = None
    is_referral_rewarded: bool = False


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_new: bool = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class UserInUsername(BaseModel):
    username: str

class NewKeyIn(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    email: str
    day_expiry: int = Field(gt=0, le=365)
    payment_id: str | None = None

class KeyExtend(BaseModel):
    email: str
    day_expiry: int = Field(gt=0, le=365)
    payment_id: str | None


class Key(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_username: str
    email: str
    sub_id: str
    sub_link: str
    expiry_time: datetime
    payment_id: str | None = None


class KeyRemoveIn(BaseModel):
    email: str



class RefreshToken(BaseModel):
    refresh_token: str
    username: str