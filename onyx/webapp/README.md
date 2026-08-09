# وب‌اپ اونیکس (Telegram Mini App)

پیاده‌سازی `change-spec-webapp-social-economy-fa.md` §۷.۰.

## اجرا — همه از لانچر

از ریشهٔ پروژه (`e:\Project\onyx`):

```bash
pip install -r data/env/requirements.txt
python launcher.py
```

لانچر به‌ترتیب: Gatekeeper → اسکیمای DB → وب‌اپ (uvicorn) → بات تلگرام را بالا می‌آورد.

تنظیمات `.env`:

| کلید | معنی |
|------|------|
| `WEBAPP_HOST` | پیش‌فرض `0.0.0.0` |
| `WEBAPP_PORT` | پیش‌فرض `8080` |
| `WEBAPP_URL` | آدرس عمومی مینی‌اپ برای تلگرام |
| `SUDO_IDS` | آیدی‌های سودو |

BotFather → Menu Button / Web App را به `WEBAPP_URL` وصل کنید. `DEBUG_MODE=false` تا initData اجباری شود.

Seed تستی اختیاری:

```bash
python -m app.database.bootstrap <TELEGRAM_USER_ID>
```

## قابلیت‌ها

- فید، پروفایل، شاپ، شارژ، هیرو، دستاورد، تورنمنت، آنلاین، چالش
- پنل مدیریت سودو (`/sudo`)
- لیست رنک + خاندان سلطنتی

## بات

- `/mycoin` `/sendcoin` می‌مانند
- `/myhero` `/achievement` `/onlinegame` `/shop` `/coin` / چالش → وب‌اپ
- مجیک: خرید وب → پنل بعد از نقش
- `/sudo` + ارشد رنک «پنل کنترل بازی»
