# وب‌اپ اونیکس (Telegram Mini App · React)

پیاده‌سازی `change-spec-webapp-social-economy-fa.md` §۵ / §۷.۰.

UI: React + Vite در `webapp/ui` → بیلد به `webapp/dist`.

## بیلد فرانت

```bash
cd webapp/ui
npm install
npm run build
```

حالت توسعه (پروکسی API به پورت ۸۰۸۰):

```bash
cd webapp/ui
npm run dev
```

## اجرا — همه از لانچر

از ریشهٔ پروژه:

```bash
pip install -r data/env/requirements.txt
python launcher.py
```

لانچر: Gatekeeper → اسکیمای DB → وب‌اپ (uvicorn) → بات.

| کلید | معنی |
|------|------|
| `WEBAPP_HOST` | پیش‌فرض `0.0.0.0` |
| `WEBAPP_PORT` | پیش‌فرض `8080` |
| `WEBAPP_URL` | آدرس عمومی مینی‌اپ |
| `SUDO_IDS` | آیدی‌های سودو |

## UX (قفل سند)

- خانه = فید
- شاپ / رنک / پروفایل مسیر جدا
- بقیه از «بیشتر»
