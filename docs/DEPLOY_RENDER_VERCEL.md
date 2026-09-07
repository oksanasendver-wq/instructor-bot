# Deploy without Docker

## Render API

Use the `backend` directory as the service root.

- Build command: `pip install -r requirements.txt`
- Start command: `alembic upgrade head && python scripts/seed_data.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Set `DATABASE_URL` to the **unchanged Internal Database URL** copied from Render Postgres. The application converts Render's standard `postgresql://...` address to its async driver itself; do not manually rewrite it.

For an external uptime monitor or cron ping, use `https://YOUR-API.onrender.com/health`. The legacy `/health` and API-scoped `/api/health` URLs both return HTTP 200, so existing monitors can keep using `/health`.

Also set `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `AI_PROVIDER`, `GROQ_API_KEY`, `FRONTEND_MINI_APP_URL`, `FRONTEND_ADMIN_URL`, `TIMEZONE=Asia/Almaty`, and `ENABLE_DEBUG=false`.

`seed_data.py` now creates only system catalogues and the score formula. It does not create instructors, clients, or bookings.

## Vercel

Create two Vercel projects from the repository:

- Mini App root: `frontend-miniapp`
- Admin root: `frontend-admin`

For each, set `VITE_API_URL=https://YOUR-API.onrender.com` and redeploy. The value is compiled into the Vite bundle, so changing it requires a new Vercel deployment.

## Telegram

After Render is live, register the webhook (replace the placeholders locally; never commit the token):

```text
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://<YOUR-API>.onrender.com/api/telegram/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>
```

Then send `/start` to the bot. The backend replies with an **Open app** button pointing to the Vercel Mini App. This is why the Mini App has its own Vercel deployment: Telegram embeds that HTTPS web page; it does not host the React application itself.

For a permanent button, in BotFather use `/setmenubutton` and supply the same Mini App Vercel URL. On first open, the instructor confirms their Telegram contact. The webhook matches that phone number to the active instructor created in the admin panel and links the Telegram account.
