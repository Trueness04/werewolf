# قوانین پروژه Onyx

بات تلگرام ورولف — بازنویسی پایتون از PHP.
این فایل **قانون الزامی** برای انسان و ایجنت است.

---

## ۱. ساختار ریشه (سخت — فقط همین)

در ریشهٔ `onyx/` **فقط** این‌ها مجازند:

```
onyx/
├── app/
├── data/
├── AI/
└── launcher.py
```

هیچ فولدر/فایل دیگری در ریشه مجاز نیست
(به‌جز مخفی‌های ابزار مثل `.git` / `.gitignore` / `.cursor`).

| مسیر | نقش |
|------|-----|
| `app/` | کد بات |
| `AI/` | ایجنت مصنوعی لابی |
| `data/` | config، text، env، docs، tests، archive، logs |
| `launcher.py` | تنها `.py` در ریشه |

زیر `data/`:

| مسیر | نقش |
|------|-----|
| `data/config/` | قوانین بازی JSON |
| `data/text/` | i18n |
| `data/env/` | `.env` / requirements |
| `data/gatekeeper/` | محدودیت‌های GK |
| `data/docs/` | مستندات اسپرینت و تصمیم |
| `data/tests/` | pytest |
| `data/archive/` | آرشیو خام (XML قدیمی PHP) |
| `data/AGENTS.md` | همین منشور |

---

## ۲. هویت و مرز محصول

| مورد | قانون |
|------|--------|
| نام | Onyx |
| ریشه | `E:/Project/onyx` |
| ورودی | `python -u launcher.py` |
| هسته | گیم‌پلی ورولف در بات تلگرام |
| خارج از بات | شاپ / شارژ / مجیک فروشگاهی / Hero → **وب‌اپ** |
| کیف در بات | `/mycoin` + `/sendcoin`؛ شاپ فقط «منتقل به وب‌اپ» |

---

## ۳. منبع حقیقت

1. `data/docs/sprint-index-fa.md`
2. `data/docs/remediation-accepted-fixes-fa.md`
3. `data/docs/acceptance-backlog-mirror-fix-fa.md`
4. اسپرینت‌ها و master در `data/docs/`
5. `data/archive/php-lang-xml/` — آرشیو؛ کد اجرایی نیست

تصمیم mirror / fix / remove / product-new فقط از اسناد؛
بدون تأیید کاربر تصمیم جدید ممنوع.

---

## ۴. قفل‌های محصولی

### حذف‌شده

- Bomber / BombCount / مود coin / bet / Achio stub خالی

### نگه

- دینامیت؛ کیف ساده بات؛ چالش MVP

### فقط با درخواست صریح (product-new)

- ارشد رنک، RoleLink، نقش‌های جدید، وب‌اپ

### دزد (`role_dozd`)

- دزدی **نقش** (نه سکه)؛ ماه ۱۴شبی یا گاز آلفا

---

## ۵. Gatekeeper

| محدودیت | مقدار |
|---------|--------|
| خطوط/فایل | ≤ ۳۵۰ |
| طول خط | ≤ ۷۸ |
| لیترال بلند | فقط در `data/` |

- منطق: `app/managers/` + `data/config/*_order.json`
- نقش‌ها: `data/config/roles.json`
- متن: TextManager از `data/text/`
- کال‌بک: `answer_safe`
- راز: فقط `data/env/.env`
- بازیکن: ۶ … ۶۰

---

## ۶. پشته

PTB async · PostgreSQL (+ SQLAlchemy async) · Redis · loguru · TextManager  
**نه Mongo.**

---

## ۷. گردش کار ایجنت

1. docs مربوط را بخوان
2. کد بزن؛ گزارش کوتاه فارسی
3. Gatekeeper + pytest در صورت امکان
4. کامیت فقط با درخواست صریح
5. markdown جدید فقط با درخواست

---

## ۸. ممنوع

- Bomber / coin / bet در ریشه یا محصول
- docs / tests / archive در ریشه
- شاپ کامل داخل بات
- هاردکد راز؛ نادیده گرفتن Gatekeeper؛ کامیت خودسر
