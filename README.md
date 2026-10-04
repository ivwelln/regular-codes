# Regular Codes
Приложение для автоматической активации промокодов на серверах сообщества по игре Rust.

## Стек
Python FastAPI sqlalchemy pydantic alembic postgresql docker 

## Запуск

Перед первым запуском:
1. Создать файл `secrets/app_db_password` с паролем базы (одна строка).
2. По желанию скопировать `.env.example` в `.env`.

### Dev
```bash
docker compose up --build --watch
```

### Prod
```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build --wait
```