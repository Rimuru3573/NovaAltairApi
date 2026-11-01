# NovaAltairApi


**NovaAltairApi** — приложение на FastAPI для продуктов NovaAltair. Является прослойкой между Telegram-ботом/Desktop-приложением и панелью 3x-ui: хранит пользователей, выдаёт JWT, создаёт и продлевает подписки с конфигами.

## Стек
---


| | |

|---|---|

| Язык | Python 3.14 |

| Веб | FastAPI + Uvicorn |

| БД | SQLAlchemy 2.1 (async) + SQLite / aiosqlite |

| Панель | py3xui 0.7 |

| Авторизация | PyJWT (HS256) + argon2 |

| Конфиг | pydantic-settings |

| Пакеты | uv |

| Деплой | Docker + Docker Compose |

  
## Структура проекта
---

```

NovaAltairApi/

├── src/novaaltairapi/

│   ├── main.py          # точка входа, lifespan, создание таблиц

│   ├── config.py        # Settings, чтение .env

│   ├── db.py            # async engine, SessionLocal, Base

│   ├── models.py        # таблицы Users и Keys

│   ├── schemas.py       # Pydantic-схемы запросов и ответов

│   ├── security.py      # argon2, JWT, проверка доступа

│   ├── repository.py    # запросы к БД

│   ├── xui.py           # работа с панелью 3x-ui и подписками

│   ├── router.py        # эндпоинты API

│   └── __init__.py

├── data/                # database.db (создаётся автоматически)

├── Dockerfile

├── docker-compose.yml

├── pyproject.toml

├── uv.lock

├── .env

├── .env.example

└── .dockerignore

```

  

## Переменные окружения
---
  
| Переменная | Обязательна | Описание |

|---|---|---|

| `XUI_PATH` | да | Адрес панели 3x-ui |

| `XUI_LOGIN` | да | Логин панели |

| `XUI_PASSWORD` | да | Пароль панели |

| `INBOUND_IDS` | да | JSON-массив ID inbound'ов, напр. `[9, 10, 11]` |

| `XUI_SUB_BASE` | да | База ссылки подписки, напр. `https://panel:2096/sub` |

| `SECRET_KEY` | да | Ключ подписи JWT, от 32 байт |

| `ALGORITHM` | да | Алгоритм JWT, `HS256` |

| `BOT_API_KEY` | да | Токен бота для заголовка `X-API-Key` |

| `DB_URL` | нет | По умолчанию `sqlite+aiosqlite:///./database.db` |

## Запуск
---
  
```bash

docker compose up -d --build

```

  

База лежит на хосте в `data/database.db`, контейнер её не теряет. Swagger — `http://127.0.0.1:8000/docs`.
  
## Эндпоинты
---
  
Доступ: `🔑` — заголовок `X-API-Key`, `👤` — `Bearer`-токен, `🌐` — без авторизации.

  

| Метод | Путь | Доступ | Описание |

|---|---|---|---|

| `GET` | `/get/telegram_id/{telegram_id}` | 🔑 👤 | Пользователь по Telegram ID |

| `GET` | `/get/username/{username}` | 🔑 👤 | Пользователь по логину |

| `POST` | `/user/new` | 🔑 | Создать пользователя |

| `POST` | `/user/register` | 🌐 | Регистрация |

| `POST` | `/user/login` | 🌐 | Логин, выдаёт пару токенов |

| `POST` | `/user/refresh` | 🌐 | Обновить access-токен |

| `POST` | `/user/logout` | 🔑 👤 | Отозвать refresh-токен |

| `POST` | `/user/set/not_new` | 🔑 👤| Снять флаг «новый пользователь» |

| `POST` | `/user/key/add` | 🔑 |👤 Создать подписку |

| `POST` | `/user/key/extend` | 🔑👤 | Продлить подписку |

| `POST` | `/user/key/remove` | 🔑👤 | Удалить подписку |

| `GET` | `/user/key/get/{email}` | 🔑 👤 | Подписка по email |

| `GET` | `/user/keys/{username}` | 🔑 👤 | Все подписки пользователя |