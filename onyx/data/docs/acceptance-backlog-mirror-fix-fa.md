# بک‌لاگ acceptance — ماتریس تصمیم mirror / fix

**وضعیت:** استخراج از اسناد موجود — ۲۰۲۶-۰۸-۰۳  
**نوع سند:** بک‌لاگ پذیرش هم‌ارزی در برابر مرتفع‌سازی (بدون پیاده‌سازی کد)  
**منابع حقیقت تصمیم:**  
- `docs/php-gaps-and-defects-fa.md`  
- `docs/remediation-accepted-fixes-fa.md` (تأیید کاربر — قفل هسته + §۱۶ Bomber/`BombCount` + §۱۷ مود `coin`)  
- `docs/economy-gaps-and-stubs-fa.md`  
- `docs/economy-shop-challenge-fa.md`  
- `docs/sprint-09-join-roles-fa.md` (§۸ باگ‌های join)  
- `docs/change-spec-meta-rank-role-links-fa.md` (فقط product-new؛ خارج از mirror/fix نقص PHP)  
- `docs/change-spec-webapp-social-economy-fa.md` (product-new: وب‌اپ اقتصاد/پروفایل/فید)  
- `docs/change-spec-role-darneshan-fa.md` (product-new: نقش دارنشان — در PHP نیست)  
- `docs/change-spec-role-bloodmoon-fa.md` (product-new: نقش بلاد مون — ومپایر؛ در PHP نیست)  
**ایندکس:** `docs/sprint-index-fa.md`

---

## ۱. مقدمه — تعاریف تصمیم

| برچسب | معنی برای بازنویسی پایتون |
|--------|---------------------------|
| **mirror** | رفتار PHP فعلی (حتی باگ‌دار) عیناً بازسازی شود؛ تست «باگ‌سازگار» الزامی است |
| **fix** | عمداً از PHP فاصله بگیرید و رفتار درست/محصولی را پیاده کنید؛ تست رگرسیون روی مسیر اصلاح‌شده |
| **remove** | API/فرمان/مسیر را از محصول حذف یا یکدست deprecate کنید؛ وعده UI/Lang نماند |
| **undecided** | سند منبع توصیه دارد ولی کاربر هنوز انتخاب قطعی نکرده — **بلاک‌کنندهٔ QA دوگانه** تا تصمیم |
| **product-new** | تغییر محصول نسبت به PHP (change-spec)؛ **نقص PHP نیست** → خارج از دامنهٔ این ماتریس برای پذیرش هم‌ارزی؛ پس از شیپ لایهٔ تست جدا («Delta») |

| وضعیت پذیرش | معنی |
|--------------|------|
| **accepted** | کاربر در `remediation-accepted-fixes-fa.md` تأیید کرده |
| **locked** | زیر‌سیاست صریح قفل‌شده داخل یک fix پذیرفته (مثلاً لوسیفر سیاست الف) |
| **pending** | توصیه در gaps/sprint هست؛ هنوز در remediation قفل نشده |
| **n/a** | برای product-new یا توضیحی بدون کار اجرایی |

**قانون استخراج:** تصمیم‌های جدید ساخته نمی‌شوند. فقط آنچه در اسناد آمده نقل می‌شود. اگر فقط «توصیه مهندسی» باشد → `pending` / `undecided`.

---

## ۲. تحلیل کوتاه (قبل از ماتریس)

1. **هستهٔ گیم‌پلی/دستور** در remediation قفل‌اند: ده **fix**، removeهای پذیرفته (`/bet` + Achio stub؛ بستهٔ Bomber/`BombCount`؛ مود `coin`)، و بخش لوسیفر داخل §۱۲ با **سیاست الف locked**.  
2. **اقتصاد/متا** عمدتاً هنوز `undecided` است (پرداخت، Sear، Hero، FreeCoin، قیمت لقب، …) — gaps صریحاً می‌گوید بدون تصمیم «پیاده/حذف» parity مبهم می‌ماند. **استثنا قفل‌شده:** مود بازی `coin` = **remove** (کیف پول/شاپ جدا می‌مانند — MF-60).  
3. **اسپرینت ۹** چند باگ join (Foolish `min/max`، Halrly، …) را برای «باگ‌سازگار یا اصلاح» باز گذاشته → اینجا `undecided`. **MF-16/`BombCount` دیگر undecided نیست** → **remove accepted** همراه نقش/مود Bomber (MF-58/59).  
4. **change-spec** (ارشد رنک، RoleLink، شاهزاده←شوالیه، دلبر←خنیاگر؛ وب‌اپ اقتصاد/پروفایل/فید؛ نقش دارنشان؛ نقش بلاد مون) = `product-new`؛ در acceptance هم‌ارزی PHP شمرده نمی‌شوند.  
5. چند مورد gaps (کلید API، answer کال‌بک، `GetRoleUserId`) توصیهٔ **fix** قوی دارند ولی در جدول ۱۲تایی remediation نیستند → `pending`.

---

## ۳. ماتریس / بک‌لاگ acceptance

### ۳.۱ هسته گیم‌پلی (رأی / برد / گاز / سیاه)

| ID | موضوع / نقص | منبع سند | تصمیم فعلی | وضعیت پذیرش | معیار acceptance (پایتون) | یادداشت |
|----|-------------|----------|------------|--------------|---------------------------|---------|
| MF-01 | منافق: پس از `GamedEnd` بدون return → اعدام/مرگ دوبل | gaps §۱؛ remediation §۲ | **fix** | accepted | اعدام منافق → دقیقاً یک `killed_user`، یک برد `monafeq`، بدون fallthrough، بدون شب بعد؛ `GameIsEnd` قبل از اثر ثانویه | اولویت ۱ ترتیب remediation |
| MF-02 | فرمول برد black عملاً غیرممکن (سیاه در دو طرف نابرابری) | gaps §۲؛ remediation §۴ | **fix** | accepted | overpower: سیاه > (روستا+آتش+منافق) با wolf/vamp/ferqe=۰؛ رگرسیون دو نفره و دیان حفظ | هم‌تراز الگوی Firefighter |
| MF-03 | StopBlack / CheckBlack مرده (فلگ هرگز set نمی‌شود) | gaps §۳؛ remediation §۳؛ sprint-11 | **fix** | accepted | قرارداد وقفه مثل کلانتر: set → تمدید تایمر → resolve در CheckBlack → پاک فلگ؛ بدون set، مسیر سپر+قتل روز نشکند | انتقام مرگ شوالیه سیاه — محصولی داخل fix |
| MF-04 | فلگ گاز یتیم اگر بازیکن نباشد → بازی هرگز تمام نمی‌شود | gaps §۷؛ remediation §۶ | **fix** | accepted | سه فلگ bite: اگر player نیست → Del؛ تست حذف سند وسط گاز → پایان ممکن | اختیاری TTL |
| MF-05 | `CheckPlayerEnchanter` لیست Redis persist نمی‌شود | gaps §۶؛ remediation §۷ | **fix** | accepted | طلسم→گاز→تبدیل → شناسه از لیست Enchanter رفته؛ شب بعد از مسیر لیست هدف نمی‌شود | |
| MF-06 | `GamedEnd` خودش سالم؛ مشکل فراخوان ناقص | gaps §۲۲ | **fix** (الگو) | accepted (همراه MF-01) | پایان بازی idempotent یک‌بارمصرف برای همهٔ بردهای مستقیم | نه نقص جدا؛ الگوی معماری |

### ۳.۲ اقتصاد / متا / جوین / بالانس نقش

| ID | موضوع / نقص | منبع سند | تصمیم فعلی | وضعیت پذیرش | معیار acceptance (پایتون) | یادداشت |
|----|-------------|----------|------------|--------------|---------------------------|---------|
| MF-07 | مود Mafia: `while($balance)` وارونه + بدون تخصیص نقش + GameStarted زود return | gaps §۴+§۱۹؛ remediation §۱ | **fix** | accepted | ≥۵ نفر، start مافیا → همه PV نقش، `game_state=night` (یا فاز اول مود)، بالانس معتبر | جایگزین remove مود رد شده؛ تصمیم = fix کامل |
| MF-08 | `GetRandomvgKey` شکسته — تزریق Vg تصادفی نیست | gaps §۵؛ remediation §۵؛ sprint-09 §۸.۲ | **fix** | accepted | توزیع آماری اندیس‌های مجاز؛ هرگز nonVg؛ خالی → fail بالانس | پایهٔ جفت Blood/کلانتر/شکار |
| MF-09 | iceWolf وزن ۰ و سطل روستا | gaps §۹؛ remediation §۹ | **fix** | accepted | وزن غیرصفر در سطل wolf؛ رگرسیون `Rosta > Wolf` با/بدون iceWolf | پیشنهاد اولیه وزن ~۱۰ |
| MF-10 | Bloodthirsty: جمع وزن روی متغیر Vampire | gaps §۱۰؛ remediation §۱۰ | **fix** | accepted | `blod += weight` مستقل؛ ترتیب آرایه بی‌اثر؛ جفت Blood↔Vamp↔کلانتر | |
| MF-11 | lucifer: `_W=17` ولی به سطل اضافه نمی‌شود | gaps §۱۱؛ remediation §۱۲ | **fix** (سیاست الف) | **locked** | افزودن lucifer سطل‌های وزن را عوض نکند؛ ۱۷ خارج از accept/reject؛ متادیتای نمایشی جدا | **قفل کاربر** — بالانس شروع بی‌اثر |
| MF-12 | کامنت/نام `forestQueen_Convert` به‌اشتباه «افسونگر» | gaps §۸؛ remediation §۱۲ | **fix** | accepted | ثابت‌های واضح ۱۰٪ ملکه / ۳۰٪ افسونگر؛ تست اولویت گاز با نام درست | همراه §۱۲ |
| MF-13 | Achio stub خالی (`AddPlayerAchio` / `CheckPlayerAchio`) | gaps §۱۲؛ remediation §۱۱؛ economy G-ACH1 | **remove** | accepted | فقط مسیر `SavePlayerAchivment`؛ stub صدا زده نشود | |
| MF-14 | `/bet` خاموش ولی کال‌بک بت زنده | gaps §۱۶؛ remediation §۱۱؛ economy G-BET1/2 | **remove** | accepted | فرمان+کال‌بک+مسیر مرده یکدست حذف/غیرفعال؛ spinner نماند | bomb بت هم زیر همین چتر |
| MF-15 | Foolish: `min(max(x,3),1)` همیشه ۱ گرگینه | sprint-09 §۸.۱، QA | **undecided** | pending | تا تصمیم: یا assert «همیشه ۱ از آن حلقه» (mirror) یا `min(max(x,1),3)` (fix) + تست تعداد | صریحاً در sprint-09 باز |
| MF-16 | سقف/کلید `BombCount` (+ کاشت `BombPlanted` وابسته) | sprint-09 §۸.۹؛ sprint-05e §۶؛ remediation §۱۶ | **remove** | accepted | هیچ `BombCount`/`BombPlanted`/`CheckBomber` در پایتون؛ QA کاشت بمبر حذف | همراه MF-58/59؛ **نه** `FindBombCount` دینامیت |
| MF-58 | نقش بمب‌گذار: `role_Bomber` / تیم `Bomber` | sprint-05e §۶؛ master تیم‌ها؛ remediation §۱۶ | **remove** | accepted | نقش در استخر/توزیع/شب/برد نباشد؛ دستور/کلید Lang نقش وعده ندهد | بستهٔ حذف Bomber |
| MF-59 | مود بازی `Bomber` (`gameModePlayer=Bomber`؛ `/StartBomber` → `CM_StartGame('Bomber')`) | sprint-09 §۳.۲؛ sprint-04 شاخه مود؛ sprint-10 | **remove** | accepted | مود و استارت از UI/registry حذف؛ شاخه برد مود Bomber پیاده نشود | بستهٔ حذف Bomber |
| MF-60 | مود بازی `coin` (`gameModePlayer=coin`؛ `/startcoin` → `CM_StartGame('coin')`) | economy-shop §۱۰.۳؛ sprint-10؛ remediation §۱۷ | **remove** | accepted | مود سکه از لابی/استارت/جوین/برد-pot پیاده نشود | **فقط مود**؛ `Players.credit`/شاپ/`/coin` شارژ جدا (مانده undecided) |
| MF-17 | تایپو `role_Halrly` در حلقه BookIn | sprint-09 §۸.۱۰ | **undecided** | pending | mirror: Harly ممکن است Book بگیرد؛ fix: املا درست و استثنا | |
| MF-18 | `GetKeyRoleByN` وقتی نقش در ایندکس ۰ | sprint-09 §۸.۱۱ | **undecided** | pending | mirror یا اصلاح جستجوی کلید ۰ | |
| MF-19 | تقدم `\|\|` / `and` در شرط جادوگر/خائن | sprint-09 §۸.۴ | **undecided** | pending | رفتار فعلی ثبت‌شده یا یکنواخت‌سازی با `&&` | |
| MF-20 | `role_Lucifer` در nonVg (L بزرگ) ≠ `role_lucifer` | sprint-09 §۸.۱۷ | **undecided** | pending | فیلتر Vg کامل برای lucifer یا parity سوراخ PHP | جدا از سیاست وزن الف |
| MF-21 | آپدیت Mongo `timer` در `ChangeGameStatus` مشکوک | sprint-09 §۸.۱۵ | **undecided** | pending | ساختار `$set` معتبر در پایتون؛ رفتار تایمر با اسپرینت ۱۱ | |
| MF-22 | حلقه وزن دوبل + Monafer بلااستفاده | sprint-09 §۸.۵ | **undecided** | pending | حذف هزینهٔ دوبل (fix DX) در برابر mirror بی‌ضرر | شدت پایین |

### ۳.۳ پیام / Lang / DX فرمان

| ID | موضوع / نقص | منبع سند | تصمیم فعلی | وضعیت پذیرش | معیار acceptance (پایتون) | یادداشت |
|----|-------------|----------|------------|--------------|---------------------------|---------|
| MF-23 | کلید API / توکن هاردکد در Lang | gaps §۲۰ | **fix** | pending (اجباری امنیتی در gaps) | فقط env/secret؛ هیچ راز در ریپو؛ چرخش توکن | **هرگز mirror راز** |
| MF-24 | `$name` اشتباه در بسیاری از Commands | gaps §۱۷ | **fix** | pending | registry: command → handler → permission → phase | sprint-10 |
| MF-25 | `RemoveRoleCommand` usage = `/addrole` | gaps §۱۶؛ sprint-10 | **fix** | pending | usage یکتا و درست برای حذف نقش | DX |
| MF-26 | Callbackquery بدون answer انتهای زنجیره | gaps §۱۸ | **fix** | pending | همیشه answer؛ حتی no-op؛ spinner نماند | middleware |
| MF-27 | دوبار `CheckVoteMessage` در تایمر رأی | gaps §۲۱ | **fix** | pending | یک فراخوانی در مسیر vote timer | |
| MF-28 | `GetRoleUserId`: `false;` بدون return → null | gaps §۱۳ | **fix** | pending | همیشه `return None` در مسیر یافت‌نشد | |
| MF-29 | CheckKalantar: fallthrough case vote | gaps §۱۴ | **mirror** (رفتار) + ساختار واضح | pending | رفتار فعلی با تابع مشترک+reason؛ بدون fallthrough تصادفی جدید | توصیه gaps: mirror رفتاری |
| MF-30 | مود nightclub / NSFW فقط پیام | gaps §و.۱۱؛ sprint-06 | **mirror** (منطق) | pending | تعویض mode = تعویض فایل متن؛ منطق فاز یکسان | رگرسیون متن جدا |
| MF-31 | عنوان Lang Xp500 («۵۰۰» در برابر متن ۱٬۰۰۰) | economy G-XP1 | **undecided** | pending | یکسان‌سازی برچسب با مقدار واقعی XP یا اصلاح مقدار | |
| MF-32 | واحد تومان در برابر ریال (×۱۰) | economy G-COIN1 | **undecided** | pending | واحد صریح در UI/مستند پایتون؛ رفتار درگاه مشخص | |

### ۳.۴ Handler / Cron / دستورات محصول جانبی

| ID | موضوع / نقص | منبع سند | تصمیم فعلی | وضعیت پذیرش | معیار acceptance (پایتون) | یادداشت |
|----|-------------|----------|------------|--------------|---------------------------|---------|
| MF-33 | `/startchallenge` بدون `CM_StartChallenge` | gaps §۱۵؛ remediation §۸؛ economy G-CH1 | **fix** | accepted | بدون throw؛ MVP چالش (ایجاد/عضویت/پایان/پاداش) یا حداقل state قابل مشاهده طبق §۸ | smoke registry همه Command |
| MF-34 | کالکشن `challenge_game` هرگز insert نمی‌شود | economy G-CH2 | **fix** (وابسته MF-33) | pending (جزئیات زیر §۸) | سشن چالش واقعاً ساخته شود یا UI چالش حذف شود — یک حقیقت | gaps: همراه MVP |
| MF-35 | `/challengeforce` و deep-link `ChallengeJoin_` بدون handler | economy G-CH3 | **undecided** | pending | پیاده با چالش یا پاک کردن Lang/URL از مسیر کاربر | |
| MF-36 | StopBlack در حلقه تایمر Handler | sprint-11 | **fix** | accepted (همراه MF-03) | پس از fix، وقفه سیاه در همان حلقه resolve شود | |

### ۳.۵ اقتصاد / شاپ / پرداخت / مجیک (عمدتاً باز)

| ID | موضوع / نقص | منبع سند | تصمیم فعلی | وضعیت پذیرش | معیار acceptance (پایتون) | یادداشت |
|----|-------------|----------|------------|--------------|---------------------------|---------|
| MF-37 | `TokenPayment=""`؛ شارژ بدون کلید | economy G-PAY1؛ webapp §۷.۰ | **fix** (UI+قیمت اول) | **accepted ۲۰۲۶-۰۸-۰۵** | UI شارژ + بسته‌های قیمت‌دار در وب؛ کلید/verify واقعی پس از تأیید بانک | بدون محصول کامل بانک درگاه نمی‌دهد |
| MF-38 | `GetChargeItem` لینک نمی‌دهد | economy G-PAY2؛ webapp §۷.۰ | **fix** | accepted (همراه MF-37) | مسیر ایجاد لینک/سفارش شارژ از UI وب | — |
| MF-39 | endpoint verify در repo نیست | economy G-PAY3؛ webapp §۷.۰ | **fix** | accepted (همراه MF-37) | endpoint verify در پایتون؛ تا کلید بانک sandbox/mock مجاز | — |
| MF-40 | `CM_FreeCoin` / `CM_GetCoin` عمداً `return false` | economy G-FREE1/2؛ webapp §۷.۰ | **remove** | accepted | حذف فرمان+منو+کلیدهای Lang مرده | ≠ مود `coin` (MF-60)؛ ≠ دزد |
| MF-41 | جادوی Sear: خرید ممکن، مصرف/Handler مرده | economy G-MAG1/2؛ shop §۶.۴ | **fix** | **accepted ۲۰۲۶-۰۸-۰۵** | خرید در وب؛ مصرف در پنل مجیک بازی؛ اثر اعلام نقش کامل | حذف نشود |
| MF-42 | پنل reply مجیک (Hook کامنت؛ Genericmessage بدون مسیر) | economy G-MAG3 | **fix** | accepted (سیاست تکمیل) | پنل مجیک اینلاین کامل (همه جادوها از جمله Sear) | مسیر زنده = اینلاین پس از نقش |
| MF-43 | خرید Hero با سکه — دکمه‌ها بدون case | economy G-HERO1 | **fix** | accepted (سیاست تکمیل) | خرید Hero با سکه کامل کار کند | حذف نشود |
| MF-44 | `CM_Achievement` بدون ارسال پیام | economy G-ACH2 | **fix** | accepted (سیاست تکمیل) | نمایش لیست دستاورد (وب منبع حقیقت؛ بات در صورت دستور) | حذف نشود |
| MF-45 | قیمت لقب: شاپ ۴۰ / کسر SetLaqab ۳۰ | economy G-LAQ1 | **fix** | accepted (runtime: ۴۰) | یک قیمت **۴۰** + یک نقطه کسر | |
| MF-46 | همگام نام با `set_laqab` (ارجاع به فلگ به‌جای نام) | economy G-LAQ2 | **fix** | accepted (سیاست تکمیل) | نام از `Players.fullname` حفظ شود وقتی لقب فعال است | |
| MF-47 | سقف ۵ ارسال روزانه sendcoin کامنت؛ شمارنده بی‌اثر | economy G-SEND1؛ webapp §۷.۰ | **fix** | accepted (انتقال سکه می‌ماند) | سقف واقعی اعمال شود؛ مسیر وب هم انتقال دارد | |
| MF-48 | آیتم‌های فقط-Lang (`sponser100`, `dozd_coin`, …) | economy G-SHOP1 | **fix** | accepted (سیاست تکمیل) | دکمه+تحویل در کاتالوگ وب/شاپ | `dozd_coin` اگر به دزد وابسته → با PN-12 حذف نقش؛ بقیه کامل |
| MF-49 | `CM_OnlineGame` صریحاً «راه‌اندازی نشده» | economy G-ONLINE | **fix** | accepted (سیاست تکمیل) | محصول OnlineGame کامل شود | حذف نشود |
| MF-50 | کسر سکه per-mode در join کامنت؛ فقط مود coin=۱۰ | economy G-JOIN-COST | **remove** (زیر MF-60) / n/a | accepted (همراه MF-60) | با حذف مود `coin` مسیر −۱۰ جوین بی‌معنی | فقط مود؛ نه کل اقتصاد |
| MF-51 | نبود ledger سکه (set مطلق) | economy G-TX؛ shop §۱۳ | **fix** | accepted (runtime: ledger) | ledger قابل audit (`web_coin_ledger`) | |
| MF-52 | برگشت جادو هنگام مرگ کامنت | economy G-MAG4 | **fix** | accepted (سیاست تکمیل) | refund جادو هنگام مرگ پیاده شود | |
| MF-53 | تورنمنت بدون جریان پرداخت کامل | economy G-TORN | **fix** | accepted (سیاست تکمیل) | جریان پرداخت/ثبت‌نام تورنمنت کامل | حذف نشود |
| MF-54 | Bet bomb در منو بدون CreateBet (`bet_bomb` / `BetGame/bomb`) | economy G-BET3 | **remove** | accepted (زیر MF-14) | با remove بت یکدست | شرط‌بندی ≠ Bomber گیم‌پلی |
| MF-55 | `des_hero_*` غیر all — `$Img` ممکن است تعریف‌نشده | economy G-HERO2 | **fix** | accepted (سیاست تکمیل) | تصویر برای همهٔ شاخه‌های Hero | |
| MF-56 | regex اموجی قدیمی `has_emojis_old` | economy G-EMOJI | **fix** | accepted (سیاست تکمیل) | اعتبارسنجی اموجی مدرن | |
| MF-57 | `CM_AddCoin` شاخه‌های username → smite | economy G-ADDCOIN | **fix** | accepted (سیاست تکمیل) | API ادمین تمیز بدون لغزش به smite | |

### ۳.۶ خارج از دامنه mirror/fix نقص PHP — product-new

| ID | موضوع | منبع | تصمیم | وضعیت | معیار | یادداشت |
|----|--------|------|--------|--------|--------|---------|
| PN-01 | ارشد رنک + «پنل کنترل بازی» | change-spec §۱ | **product-new** | n/a (پیشنهادی) | چک‌لیست §۷ change-spec پس از شیپ | تا شیپ مرجع = PHP/اسپرینت ۱–۱۱ |
| PN-02 | چارچوب RoleLink عمومی | change-spec §۲ | **product-new** | n/a | جدول پیوند + رویدادهای استاندارد | |
| PN-03 | سینک شاهزاده ← شوالیه | change-spec §۳ | **product-new** | n/a | محافظت واکنش‌گر + متن وارث تاج | |
| PN-04 | سینک دلبر ← خنیاگر (+ آواز) | change-spec §۴ | **product-new** | n/a | انتخاب تیم خنیاگر؛ آشوب فاز؛ مرگ معشوقه | |
| PN-05 | کپی هیجانی دستاورد/آمار پایان | achievements-endstats-copy-* | **product-new** | n/a | اعمال به Lang جدا | ایندکس: پیشنهادی — به Lang اعمال نشده؛ منبع آیندهٔ نمایش وب‌اپ هم هست |
| PN-06 | انتقال اقتصاد/شاپ/سکه/چالش به وب‌اپ | change-spec-webapp §۲ | **product-new** | جزئیات §۷.۰ قفل (+ شارژ UI ۲۰۲۶-۰۸-۰۵) | چک‌لیست §۸؛ UI شارژ+قیمت ساخته می‌شود؛ بت خارج | چالش فقط وب |
| PN-07 | پروفایل سوشال (پست/آیکون بازی/دنبال‌کردن) | change-spec-webapp §۳ | **product-new** | قفل‌شده | §۸.۲؛ بدون DM؛ سکه/آمار عمومی؛ آیکون per رنک+مدال | — |
| PN-08 | فید خبری لندینگ + لایک/کامنت | change-spec-webapp §۴ | **product-new** | قفل‌شده | §۸.۳؛ فید سراسری + Follow | — |
| PN-11 | لیست رنک + خاندان سلطنتی + اعلان حکمران | change-spec-webapp §۴ب | **product-new** | accepted | نفر ۱=حکمران؛ ۱–۳ سلطنتی **بدون لقب جدا برای ۲ و ۳**؛ NewLevel با نام واقعی | نقص PHP: HL هاردکد |
| PN-12 | حذف نقش دزد (`role_Dozd` / خرید دزد) | تصمیم کاربر ۲۰۲۶-۰۸-۰۳ | **remove** | accepted | نقش+خرید شاپ دزد+مصرف شب در پایتون نباشد | جدا از مود coin و FreeCoin |
| PN-09 | نقش جدید دارنشان🕯️ (`role_DarNeshan`) — فرقه | change-spec-role-darneshan | **product-new** | proposed / pending تصمیم‌های G1–G20 | چک‌لیست §۱۰ change-spec؛ **در PHP نیست** | علامت شب → اعدام → تبدیل قطعی PV؛ خارج parity؛ جنس ≠ بلاد مون |
| PN-10 | نقش جدید بلاد مون🌕 (`role_BeladMoon`) — ومپایر | change-spec-role-bloodmoon | **product-new** | proposed / pending تصمیم‌های G1–G20 | چک‌لیست §۱۰ change-spec؛ **در PHP نیست** | روز→خون‌ماه شب بعد؛ قفل سراسری رقبا؛ فقط شکار ومپ؛ جنس شب‌قفل ≠ دارنشان |

---

## ۴. موارد **undecided** که نیاز به تصمیم کاربر دارند

**به‌روزرسانی ۲۰۲۶-۰۸-۰۵:** سیاست کاربر برای اقتصاد/متای وعده‌داده‌شده = **تکمیل نه حذف**.  
شارژ ریالی = **ساخته می‌شود** (برای گرفتن درگاه). Sear = کامل (خرید وب / مصرف پنل مجیک).

### بسته شده در این دور

1. ~~MF-37…39 پرداخت~~ → **fix accepted** — UI+قیمت اول؛ کلید بانک بعد از تأیید  
2. ~~MF-41 Sear~~ → **fix accepted**  
3. ~~MF-42…44، ۴۸…۴۹، ۵۱…۵۳، ۵۵…۵۷~~ → **fix accepted** (سیاست تکمیل)  
4. ~~MF-45~~ → قیمت لقب **۴۰** (قبلاً runtime)  
5. ~~MF-40 / MF-47 / MF-14 / MF-16/58/59 / MF-60~~ → از قبل قفل  

### هنوز باز (غیر از سیاست بالا)

- MF-31 Xp500 عنوان متن در برابر مقدار  
- MF-32 واحد تومان/ریال در UI شارژ (حالا که UI ساخته می‌شود باید صریح شود)  
- MF-35 challengeforce — با چالش فقط‌وب: deep-link به وب یا پاک‌سازی Lang بات  

جوین MF-15…22 قبلاً در `decisions-runtime` قفل شده‌اند.
---

## شمارش وضعیت (این سند)

| دسته تصمیم | تعداد ردیف (تقریبی) | توضیح |
|------------|---------------------|--------|
| **fix accepted** | **۱۱ هسته + بستهٔ اقتصاد ۲۰۲۶-۰۸-۰۵** | MF-01…10، MF-12، MF-33 (+ وابسته) + MF-37…39، ۴۱…۴۶، ۴۸…۴۹، ۵۱…۵۳، ۵۵…۵۷ |
| **fix locked** | **۱** | MF-11 لوسیفر سیاست الف |
| **remove accepted** | **۶** (+وابسته) | MF-13 Achio؛ MF-14 `/bet`؛ **MF-16/58/59** بسته Bomber؛ **MF-60** مود `coin` (+ MF-50 همراه)؛ MF-40 FreeCoin؛ MF-54 زیر بت |
| **mirror (توصیه، pending)** | **۲** | MF-29 Kalantar رفتار؛ MF-30 nightclub منطق |
| **fix pending** (توصیه gaps، نه در ۱۲تایی) | **۶** | MF-23…28 (چندتایش در runtime قفل DX) |
| **undecided باقی** | **≈۳** | MF-31 Xp500 عنوان؛ MF-32 تومان/ریال برچسب؛ MF-35 challengeforce→وب |
| **product-new (out of scope)** | **۱۰** | PN-01…05؛ PN-06…08 وب‌اپ؛ **PN-09** دارنشان؛ **PN-10** بلاد مون |

**جمع پذیرفته‌شدهٔ صریح کاربر (remediation + ۲۰۲۶-۰۸-۰۵):** ۱۰ fix عادی + ۱ fix locked (lucifer) + removeهای §۱۱/۱۶/۱۷ + StartChallenge + **سیاست تکمیل اقتصاد** + **UI شارژ برای درگاه**.

---

## ۶. پیوند اسپرینت / ترتیب کار

| حوزه پذیرش | اسپرینت مرتبط |
|------------|----------------|
| MF-01 رأی منافق | ۸ |
| MF-02 برد black | ۴ |
| MF-03/36 StopBlack | ۵ه، ۸، ۱۱ |
| MF-04/05 گاز | ۲ |
| MF-07…12، ۱۵، ۱۷…۲۲ جوین/وزن | ۳، ۹ |
| MF-16/58/59 حذف Bomber؛ MF-60 حذف مود coin | ۴، ۵ه، ۹، ۱۰؛ economy |
| MF-13/14/33 دستورات | ۱۰ |
| MF-23…30 پیام/DX | ۶، ۱۰ |
| MF-37…57 اقتصاد | خارج هسته؛ `economy-*` |
| PN-* | change-spec (متا رنک + وب‌اپ سوشال + نقش دارنشان + نقش بلاد مون) — پس از parity هسته؛ وب‌اپ مستقل از mirror اقتصاد |

ترتیب اعمال fixهای پذیرفته: `remediation-accepted-fixes-fa.md` §۱۴.

---

## ۷. قانون نگهداری این بک‌لاگ

1. هر تصمیم جدید کاربر → فقط همین فایل + یک خط در remediation (اگر fix/remove هسته است).  
2. اسپرینت‌ها رفتار هدف پس از fix را توصیف می‌کنند؛ این فایل **وضعیت پذیرش** را.  
3. `product-new` را با `fix` قاطی نکنید — اول parity/مرتفع‌سازی، بعد Delta.  
4. تا `undecided`های P0/P1 بسته نشوند، تست اقتصاد/چالش را «هم‌ارز PHP» اعلام نکنید.

---

*پایان. بدون تغییر کد PHP/Python/Lang؛ فقط مستندسازی تصمیم.*
