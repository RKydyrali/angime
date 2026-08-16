# Angime — мультитенантный WhatsApp-бот для записи и FAQ

SaaS: клиенты (бизнесы) подключают свой WhatsApp (Meta Cloud API), получают
ИИ-бота (запись на услуги, FAQ, напоминания), Telegram-уведомления по
6-значному коду и двуязычный (RU/KZ) shadcn-дашборд.

## Состав

- `backend/` — FastAPI: webhook-шлюз Meta (мультитенантный), AI (OpenRouter),
  поток записи, планировщик напоминаний, Telegram-бот уведомлений, админ-API
- `frontend/` — Next.js 14 + shadcn/ui + Phosphor icons + next-intl (ru/kz)

## Запуск (локально)

```bash
# backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # заполнить ключи
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev
```

## Production (VPS)

```bash
docker compose up -d --build
```

nginx: `danyshpan.xyz` → frontend; `/api` и `/webhook` → backend.

## Мультитенантность

- Один эндпоинт `/webhook`: verify-токен и подпись проверяются по каждому тенанту,
  маршрутизация по `phone_number_id`.
- Тенанты создаются в админ-панели `/admin` (креды WABA, подписка 20 000 ₸/мес).
- AI-контекст собирается из данных тенанта: знания (текст из настроек), услуги,
  текущие и будущие записи, часы работы.

## Production (VPS 185.113.132.186)

- `https://danyshpan.xyz` — дашборд; `server.danyshpan.xyz` — алиас (webhook WABA).
- Развёртывание: `cd /opt/angime && git pull && docker compose up -d --build`.
- Секреты: `/opt/angime/.env` (НЕ в git).
- nginx: `/etc/nginx/sites-available/angime` (frontend 3001, backend 8001, SSL letsencrypt).
- Бэкап БД: `docker exec angime-db pg_dump -U angime angime | gzip > /root/angime_$(date +%F).sql.gz`.

### Первый вход

- Админ: `https://danyshpan.xyz/login` (admin / пароль из .env `ADMIN_PASSWORD`).
- Клиент (пример): aikerim@danyshpan.xyz / Aikerim2026!

