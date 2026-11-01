from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    xui_path: str
    xui_login: str
    xui_password: str
    inbound_ids: list[int]
    secret_key: str
    algorithm: str
    bot_api_key: str
    xui_sub_base: str

    db_url: str = "sqlite+aiosqlite:///./database.db"

settings = Settings()