# تحلیل ادغام اسناد قدیمی `werewolf-*` با خانوادهٔ `sprint-*`

**تاریخ تحلیل:** ۲۰۲۶-۰۸-۰۳  
**دامنه:** فقط مستندات در `docs/` — بدون تغییر کد برنامه  
**ورودی:** همهٔ `werewolf-*.md` + همهٔ `sprint-*.md` + `werewolf-python-rewrite-master-fa.md` + `sprint-index-fa.md`  
**خروجی این سند:** ماتریس وضعیت، محتوای یکتا، مرجع کانونیکال، و اقدامات ادغام انجام‌شده

---

## ۱. موجودی فایل‌ها

### ۱.۱ خانوادهٔ قدیمی `werewolf-*`

| فایل | نقش تقریبی |
|------|------------|
| `werewolf-python-rewrite-master-fa.md` | مرجع کلان بازنویسی (معماری، state، وزن، فازها، نقش‌ها، برد، دستورات) |
| `werewolf-logic-documentation-fa.md` | موتور، بالانس، state، کلید پیام، هاردکد |
| `werewolf-day-and-lynch-documentation-fa.md` | فاز روز + سیستم اعدام |
| `werewolf-win-conditions-fa.md` | شرط‌های برد تیم‌به‌تیم |
| `werewolf-village-roles-batch1-fa.md` | عمق نقش‌های روستا (دسته ۱) |
| `werewolf-enemy-special-roles-fa.md` | دشمن/ویژه + روستایی‌های باقی + دزد/خنیاگر/هل‌بوی |
| `werewolf-roles-complete-reference-fa.md` | مرجع فشرده همه نقش‌ها (به‌ویژه گرگ) |
| `werewolf-messages-fa-complete.md` | بانک کامل کلید→متن فارسی |
| `werewolf-user-workflow-fa.md` | جریان کامل از دید کاربر |
| `werewolf-midgame-end-user-journey-fa.md` | میان‌بازی و پایان از دید کاربر |

### ۱.۲ خانوادهٔ جدید `sprint-*` (+ ایندکس)

| فایل | موضوع |
|------|--------|
| `sprint-index-fa.md` | نقشهٔ کار و نقطهٔ ورود |
| `sprint-01` … `sprint-11` | دستورکار اجرایی هم‌ارزی PHP |
| `sprint-05a` … `sprint-05f` | عمق نقش‌ها به‌تفکیک دسته |

---

## ۲. نقشهٔ هم‌پوشانی موضوعی

| موضوع | سند قدیمی | سند(های) کانونیکال اسپرینت/مستر | نوع هم‌پوشانی |
|--------|-----------|----------------------------------|---------------|
| معماری دو مسیر webhook/cron | logic، user-workflow، master | master §۱ + `sprint-11` | تقریباً کامل |
| State / Redis / Mongo | logic، roles-complete، master | master §۲ | تقریباً کامل |
| وزن / بالانس / استخر | logic، master | master §۳ + `sprint-09` | اسپرینت عمیق‌تر (باگ‌ها) |
| پایپ‌لاین شب / CheckNight | logic، enemy، village، roles | `sprint-01` | اسپرینت مرجع مطلق ترتیب |
| گاز / BittanCheck | (پراکنده در قدیمی) | `sprint-02` | قدیمی سطحی‌تر |
| جفت‌نقش | logic، master | `sprint-03` | اسپرینت مرجع |
| برد / CheckEndGame | win-conditions، master | `sprint-04` | اسپرینت مرجع مطلق ترتیب داور |
| فرقه / شکارچی / رویس… | enemy، village(shekar) | `sprint-05a` | اسپرینت عمیق‌تر + QA |
| قاتل / آتش / ومپایر | enemy | `sprint-05bcd` | اسپرینت مرجع |
| سیاه / جوکر / لوسیفر / بمبر / دینامیت / همزاد | enemy | `sprint-05e` | اسپرینت مرجع |
| روستا ویژه | village-batch1، enemy §۸ | `sprint-05f` | اسپرینت مرجع |
| دزد / خنیاگر / هل‌بوی / javidShah / hipo | **عمدتاً فقط enemy** | باید در `sprint-05e` حفظ شود | یکتا / نیمه‌یکتا |
| پیام / Lang | logic §۴، messages | `sprint-06` + **messages (keep)** | بانک کامل فقط در messages |
| روز | day-and-lynch، midgame | `sprint-07` | اسپرینت مرجع |
| رأی / لینچ | day-and-lynch، midgame | `sprint-08` | اسپرینت مرجع |
| جوین / نقش‌دهی | logic، master | `sprint-09` | اسپرینت عمیق‌تر |
| دستورات / کال‌بک | master، user-workflow | `sprint-10` | اسپرینت کاتالوگ |
| تجربهٔ کاربر (سفر UX) | **user-workflow، midgame** | هیچ اسپرینت معادلی ندارد | **keep** |
| خلاصه نقش‌به‌نقش گرگ | **roles-complete §۴.۱** | master §۸ جدول + `sprint-01` WolfTeam | جدول در master؛ روایت لبه در roles |

---

## ۳. ماتریس وضعیت فایل قدیمی

| فایل قدیمی | وضعیت | اقدام | مرجع کانونیکال |
|------------|--------|--------|----------------|
| `werewolf-python-rewrite-master-fa.md` | **keep** | زنده بماند؛ لینک‌ها به اسپرینت/ایندکس به‌روز | خود سند + `sprint-index-fa.md` |
| `werewolf-messages-fa-complete.md` | **keep** | بانک متن؛ اسپرینت ۶ به آن ارجاع می‌دهد | خود سند + `sprint-06` |
| `werewolf-user-workflow-fa.md` | **keep** | مکمل UX؛ در ایندکس به‌عنوان پیوست | خود سند |
| `werewolf-midgame-end-user-journey-fa.md` | **keep** | مکمل UX میان‌بازی؛ ارجاع از اسپرینت ۸ حفظ | خود سند |
| `werewolf-logic-documentation-fa.md` | **deprecate → stub** | بدنه → ارجاع کوتاه | master + s01/s09/s11/s06 |
| `werewolf-day-and-lynch-documentation-fa.md` | **deprecate → stub** | بدنه → ارجاع کوتاه | `sprint-07` + `sprint-08` |
| `werewolf-win-conditions-fa.md` | **deprecate → stub** | بدنه → ارجاع کوتاه | `sprint-04` |
| `werewolf-village-roles-batch1-fa.md` | **deprecate → stub** | بدنه → ارجاع کوتاه | `sprint-05f` (+ `sprint-05a` برای shekar) |
| `werewolf-enemy-special-roles-fa.md` | **merge-into → stub** | یکتاها به `sprint-05e`؛ سپس stub | `sprint-05a/bcd/e/f` |
| `werewolf-roles-complete-reference-fa.md` | **merge-into → stub** | روایت فشرده گرگ به `sprint-01`؛ سپس stub | master §۸ + `sprint-05*` + `sprint-01` |

الگوی archive جداگانه در `docs/` وجود نداشت؛ بنابراین **stub ارجاعی** (نه حذف خاموش) انتخاب شد تا لینک‌های قدیمی نمیرند.

---

## ۴. محتوای یکتا که باید حفظ شود

### ۴.۱ منتقل‌شده در این ادغام

| محتوا | مبدأ | مقصد |
|--------|------|------|
| Workflow/State/پیام/لبهٔ `role_dozd` | enemy §۷.۸ | `sprint-05e` — بخش «محتوای یکتا منتقل‌شده» |
| Workflow/State/پیام/لبهٔ `role_khenyager` | enemy §۷.۹ | همان |
| وضعیت وجود `role_hellboy` (غیرفعال/ناقص) | enemy §۷.۱۰ | همان |
| وضعیت `role_javidShah` / `role_hipo` | enemy §۸.۱۶ | همان |
| روایت فشرده تیم گرگ (خورنده/غیرخورنده، لبه نقش‌ها) | roles-complete §۴.۱ | `sprint-01` — بخش «محتوای یکتا منتقل‌شده» |

### ۴.۲ نگه داشته‌شده در فایل keep (بدون کپی دیوار متن)

| محتوا | فایل |
|--------|------|
| بانک کامل کلید→متن | `werewolf-messages-fa-complete.md` |
| سفر کاربر از لابی تا پایان | `werewolf-user-workflow-fa.md` |
| جزئیات لمس UI میان‌بازی/وقفه‌ها/پایان | `werewolf-midgame-end-user-journey-fa.md` |
| جداول state/وزن/خلاصه نقش در مرجع کلان | `werewolf-python-rewrite-master-fa.md` |

### ۴.۳ نیاز به بازبینی (حذف نشده؛ در stub علامت خورده)

این موارد در اسناد قدیمی با جزئیات بیشتری آمده‌اند ولی اطمینان کامل از «یکتایی نسبت به اسپرینت» نیست؛ stub به آن‌ها اشاره می‌کند و حذف خام نشده:

1. فهرست تفصیلی رشته‌های هاردکد بن/ادمین در `werewolf-logic` §۴.۴ در برابر master §۱۱ و economy docs  
2. جدول تعامل فشرده enemy §۹ در برابر جداول پراکندهٔ اسپرینت ۵*  
3. مقادیر `_s` در enemy §۱۰ در برابر master / sprint-05bcd  
4. هر edge case نقش روستایی که فقط در narrative قدیمی باشد و در `sprint-05f` کوتاه‌تر شده — **نیاز به بازبینی** قبل از اتکا به نسخهٔ کوتاه‌تر در اختلاف جزئی

---

## ۵. مرجع کانونیکال پیشنهادی به‌ازای موضوع

| موضوع | سند کانونیکال |
|--------|----------------|
| نقطهٔ ورود همهٔ کار | `sprint-index-fa.md` |
| مرجع کلان یک‌جا | `werewolf-python-rewrite-master-fa.md` |
| شب | `sprint-01-night-pipeline-fa.md` |
| گاز | `sprint-02-gas-conversion-fa.md` |
| جفت‌نقش | `sprint-03-role-pairs-fa.md` |
| برد | `sprint-04-win-conditions-fa.md` |
| نقش‌ها | `sprint-05a` … `sprint-05f` |
| پیام‌ها | `sprint-06` + `werewolf-messages-fa-complete.md` |
| روز | `sprint-07-day-pipeline-fa.md` |
| رأی | `sprint-08-vote-lynch-fa.md` |
| جوین | `sprint-09-join-roles-fa.md` |
| دستورات | `sprint-10-commands-callbacks-fa.md` |
| Handler/Cron | `sprint-11-handler-cron-fa.md` |
| UX کاربر | `werewolf-user-workflow-fa.md` + `werewolf-midgame-end-user-journey-fa.md` |

قانون تعارض: در اختلاف رفتاری گیم‌پلی بین اسناد، **سورس PHP حاکم** است؛ بین اسناد، اسپرینت اجرایی بر روایت قدیمی اولویت دارد مگر مورد «نیاز به بازبینی».

---

## ۶. اقدامات ادغام انجام‌شده

1. ایجاد همین سند تحلیل.  
2. انتقال محتوای یکتای §۴.۱ به `sprint-05e` و `sprint-01`.  
3. جایگزینی بدنهٔ شش فایل deprecate/merge با stub فارسی ارجاعی.  
4. به‌روزرسانی `sprint-index-fa.md` به‌عنوان نقطهٔ ورود واحد (+ ردیف ادغام و پیوست‌های keep).  
5. به‌روزرسانی پیوست‌ها/ارجاعات در master و اسپرینت‌هایی که به فایل‌های stub اشاره می‌کردند.

---

## ۷. تأیید محدوده

- هیچ فایل PHP / Python / Lang / `.ini` تغییر نکرد.  
- هیچ اسکریپت کمکی اضافه نشد.  
- فقط Markdown در `docs/`.
