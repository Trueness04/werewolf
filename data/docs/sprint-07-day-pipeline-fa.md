# اسپرینت ۷ — پایپ‌لاین کامل روز (اجرایی)

**وضعیت:** آماده برای مرجع بازنویسی پایتون  
**هدف اسپرینت:** رفتار روز هم‌ارز PHP — ورود از شب، پخش کیبورد، اکشن فوری، resolve پایان‌روز، انتقال به رأی  
**خروجی قابل قبول:** تایمر روز ست می‌شود؛ نقش‌های روزبازمانه با گیت‌های درست کیبورد می‌گیرند؛ فلگ‌های فوری دقیق ست می‌شوند؛ `CheckDay` با ترتیب ثابت حل می‌شود؛ وقفه تیر کلانتر روز را نگه می‌دارد؛ انتقال day→vote با شمارنده و cleanup درست  
**مرجع سورس:** `DY.php`, `HL.php` (`ChangeGameStatus` day / `CheckTimer` day), `CM.php` (`DaySelectedCheck` / `DaySelectedDodge`), `Handler.php`  
**مرجع کلان:** `docs/werewolf-python-rewrite-master-fa.md`  
**محدودیت سند:** بدون قطعه کد؛ متن فارسی؛ کلید Lang؛ بدون `Notes_Mode` / `Game_Mode`

---

# ۱. تحلیل و استدلال

روز فضای بحث اجتماعی است، نه لایهٔ resolve شب. PHP اثر بیشتر نقش‌های روز را **در لحظهٔ کلیک** می‌زند (صلح، کدخدا، حاکم، خواب‌گذار، آهنگر، داوینا، دردسرساز، زنجیرهٔ گیاه‌شناس) تا فضای بحث یا فاز بعدی عوض شود؛ بقیه را فقط در `Selected` نگه می‌دارد و در `CheckDay` با ترتیب ثابت حل می‌کند (تفنگدار، شوالیه سیاه، دینامیت، کارآگاه، جاسوس، شاهدخت، دیان، کنت).

سه لایه را قاطی نکنید:

1. **ورود و تیک روز** — `ChangeGameStatus('day')`، خلاصهٔ گروهی، `DY::Handel` → عاشق‌ها + `SendDayRole`.  
2. **طول روز** — کال‌بک‌های `DaySelect_*` / `DySlDodge_*`؛ فوری یا ذخیره.  
3. **پایان تایمر** — `CheckDay`؛ اگر `HunterKill` باشد توقف؛ وگرنه `vote` و `Day_no + 1`.

برخلاف شب و رأی، **early-end روز وجود ندارد**: حتی اگر همه انتخاب کرده باشند، تایمر تا سررسید می‌ماند مگر وقفهٔ تیر مرگ (+۴۵ث) آن را تمدید کند. دلیل طراحی: روز برای حرف زدن است.

شمارندهٔ روز هنگام خود فاز روز زیاد نمی‌شود؛ افزایش در خروج روز→رأی است. بنابراین «روز اول» با `Day_no == 1` است و رأی بلافاصله بعد از آن قبلاً `Day_no == 2` می‌بیند.

---

# ۲. محدوده اسپرینت (In / Out)

## داخل محدوده

- جریان کامل night→day و تیک Handler در `day`
- `SendDayRole` + همهٔ گیت‌های skip + لوسیفر داج روز
- اکشن‌های فوری با فلگ دقیق
- ترتیب کامل `CheckDay`
- وقفه `HunterKill` از شلیک به کلانتر
- cleanup و انتقال day→vote (از جمله موعد دیان)
- فهرست کلیدهای Lang مرتبط

## خارج از محدوده

- شمارش و اعدام رأی (`VT`) — فقط قرارداد ورود به رأی اینجا ثبت می‌شود
- resolve شب / گاز (`BittanCheck`) — فقط نقطهٔ تماس گیاه‌شناس
- عمق کامل زندان شاهدخت در شب‌های بعد
- polish پیام / مدال / GIF مگر کلید Lang لازم باشد

---

# ۳. جریان ورود روز (بعد از شب)

1. تایمر شب تمام → `NG::CheckNight`.  
2. اگر وقفه (`HunterKill` / `StopBlack` / `SendWolfCubeDead` / `RoyceSelectd2`) → **بدون** ورود به روز.  
3. اگر `Day_no == 1` → `CheckDontSelectRole` (همزاد / الهه / وحشی / لوسیفر شب‌اول).  
4. `ChangeGameStatus('day')`:
   - `game_state = day`
   - تایمر = `day_timer` گروه یا پیش‌فرض **۹۰**؛ گزینه‌های تنظیم: ۶۰ / ۹۰ / ۱۲۰ / ۱۸۰ / ۳۰۰
   - اگر `GamePl:DavinaOk` موجود → تایمر اجباری **۳۰** و `LockPlayer` (میوت حدود ۳۰ث برای همهٔ زنده‌ها)
5. پاک‌سازی‌های night→day: `SendVote`؛ در صورت وجود `role_Solh:GroupInSolh` و `role_Ruler:RulerOk` حذف؛ `SendNightAll` / `CheckNight` / `playerDeadName`.  
6. بعد از `CheckTimer`: بستن کیبوردهای باز، پاک `Selected:*`، `CheckEndGame`، سپس `GetGameStatusLang` برای روز:
   - اگر داوینا فعال: فقط `MessageDayWhenDavina`
   - وگرنه: اگر نه `Kill` و نه `KhabgozarOk` → صف `NoAttakInDay`؛ سپس `MassgeFortypeSummery_day` + `Day_nos`
7. هر تیک Handler وقتی `game_state == day`: چک پایان بازی (مگر HunterKill)، `checkTime` (روی روز no-op)، `CheckTimer`، سپس `DY::Handel`.

### تیک روز (`DY::Handel`)

1. `LoverMessage` — فقط اگر `Day_no <= 2`؛ برای هر جفت عشق یک‌بار (`SendLoverMessage:{uid}`)؛ کلید `CupidChosen` / `CupidChosen2` یا در مود Romantic همان `RomanticModeMessage`.  
2. `SendDayRole` — پخش کیبورد نقش‌های روزبازمانه.

---

# ۴. SendDayRole — کیبوردها و گیت‌های skip

### لیست نقش‌های گیرنده‌کیبورد

فقط زنده‌های `user_state=1` و `user_status=on` با نقش در این مجموعه:

`role_Solh`, `role_dian`, `role_BlackKnight`, `role_Princess`, `role_kentvampire`, `role_dinamit`, `role_davina`, `role_tofangdar`, `role_Kadkhoda`, `role_Ruler`, `role_karagah`, `role_Spy`, `role_trouble`, `role_Ahangar`, `role_KhabGozar`

**گیاه‌شناس در این لیست نیست.** زنجیرهٔ گاز فقط از `UserInConvert` هنگام پیمایش همین لیست صدا زده می‌شود (اگر خودِ نقش‌روز گازگرفته باشد).

### خروج زودرس تابع

اگر تعداد اعضای لیست Redis `GamePl:SendDayRole` برابر تعداد بازیکنان واجد نقش بالا باشد → کل تابع return (همه «علامت خورده»اند).

### گیت‌های مشترک (به ترتیب، برای هر ردیف)

| # | شرط | اثر |
|---|------|-----|
| ۱ | `PrincessPrisoner:{uid}` | continue — بدون کیبورد |
| ۲ | `PlayerIced:{uid} == Night_no` (مقایسهٔ عدد صحیح) | continue |
| ۳ | `NotSendDay == Day_no` | **break** کل حلقه (روز داوینا: هیچ نقش روزی بعد از این نقطه ارسال نمی‌شود) |
| ۴ | uid قبلاً در `SendDayRole` | continue |
| ۵ | سپس `UserInConvert(uid)` (گیاه‌شناس؛ مستقل از کیبورد نقش) | — |
| ۶ | `NotSend_{role}` یا `{role}:notSend` | continue (ولی uid قبلاً push شده؟ خیر — push بعد از این است) |
| ۷ | `rpush` به `SendDayRole` | علامت «ارسال‌شده» حتی اگر بعداً کیبورد نرود |
| ۸ | `CheckDodge` اگر true | continue — کیبورد به لوسیفر رفته |

نکتهٔ یخ: در شب گیت `(PlayerIced + 1) == Night_no` است؛ در روز `PlayerIced == Night_no`. چون `Night_no` فقط در رأی→شب زیاد می‌شود، هر دو همان «روز و شب بلافاصله بعد از شب یخ» را می‌پوشانند.

### گیت نقش‌محور داخل switch

| نقش | skip کیبورد اگر | کال‌بک / متن |
|-----|-----------------|--------------|
| صلح | — (یک‌بار با `NotSend_role_Solh` بعد از ارسال موفق) | `DaySelect_Solh` / `solh_L` + `solh_btn`؛ markup در `EditMarkupEnd` |
| شاهدخت | `Night_no <= 2` → `continue 2` | `DaySelect_Princess` / `AskPrincess` |
| کنت | نبود `KentVampireConvert` → `continue 2` | `DaySelect_KentVampire` / `AskDayKentVampire` |
| تفنگدار | `GunnerBult <= 0` → `continue 2` | `DaySelect_Tofangdar` / `AskShoot` با `{0}=گلوله` |
| دیان | —؛ سیاه‌ها از لیست هدف حذف می‌شوند | `DaySelect_Dian` / روز۲: `AskDianTowDay` وگرنه `AskDianDay` |
| کدخدا | بعد از ارسال: `NotSend_role_Kadkhoda` | `DaySelect_Kadkhoda` / `Kadkhoda_l` + `Kadkhoda_btn`؛ `EditMarkupEnd` |
| حاکم | — | `DaySelect_Ruler` / `RulerAsk` + `RulerButton` |
| کارآگاه | — | `DaySelect_Karagah` / `howEstelamIs` |
| دینامیت | — | `DaySelect_dinamit` / `AskDinamit_day` با `{0}=FindedBombCount` |
| جاسوس | — | `DaySelect_Spy` / `SpyAsk` |
| شوالیه سیاه | — | `DaySelect_BlackKnight` / `BlackKnightAsk` |
| دردسرساز | — | yes/no: `DaySelect_trouble_yes|no` / `Asktrouble` |
| آهنگر | — | no/yes: `DaySelect_Ahangar_no|Yes` / `ahangar_L` |
| خواب‌گذار | — | yes/no: `DaySelect_Khabgozar_Yes|No` / `KHABGOZAR_l` |
| داوینا | — | yes/no: `DaySelect_davina_Yes|No` / `AskDavina` |

پس از `rpush` به `SendDayRole`، `continue 2` (شاهدخت/کنت/تفنگدار) باعث می‌شود همان روز دوباره تلاش نشود؛ چون `SendDayRole` در رأی→شب پاک می‌شود، روز بعد با گیت تازه دوباره فرصت هست.

### لوسیفر داج روز (`CheckDodge`)

اگر `role_lucifer:DodgeDay:{uid}` و لوسیفر زنده باشد: به قربانی `DodgeYou`؛ کیبورد نقش به لوسیفر با پیشوند `DySlDodge_*` (Gunner / Princess / Karagah / KentVampire / Spy). نقش‌های دیگر در switch داج → false (قربانی کیبورد عادی می‌گیرد مگر گیت دیگر).  
انتخاب داج در `DaySelectedDodge` روی `Selected:{قربانی}` ذخیره می‌شود؛ کلید سراسری قربانی: `role_lucifer:DodgeDay`.

---

# ۵. اکشن‌های فوری روز — فلگ‌های دقیق

مسیر: کال‌بک `DaySelect_{Selected}/...` → `CM::DaySelectedCheck`.  
قبل از switch: اگر قبلاً `Selected:{actor}:user` و نقش ≠ صلح → نادیده؛ صلح اگر `GroupInSolh` دارد → نادیده؛ برای غیرصلح `Selected:{actor}:user = true`.

### صلح (`Solh`)

| کلید | مقدار |
|------|--------|
| گارد تکرار | `solhIsSolh` (اگر بود فقط کیبورد خالی) |
| `role_Solh:GroupInSolh` | `Day_no + 1` |
| `solhIsSolh` | true |
| `Selected:{uid}:user:vote` | true |
| پیام گروه | `PacifistNoLynch` فوری |
| اگر `game_state == vote` | `timer = now` (پایان فوری رأی) |
| پاک‌سازی | night→day حذف `GroupInSolh`؛ ورود رأی با این فلگ: تایمر رأی ۰ و بدون متن خلاصه رأی |

### کدخدا (`Kadkhoda`)

| کلید | مقدار |
|------|--------|
| گارد | `role_Kadkhoda:MayorReveal` |
| `role_Kadkhoda:MayorReveal` | true |
| پیام | `MayorReveal` (+ GIF کدخدا) |
| اثر بعدی | در رأی وزن دو رکورد (خارج از این اسپرینت؛ فقط قرارداد) |

### حاکم (`Ruler`)

| کلید | مقدار |
|------|--------|
| گارد | `RulerOkAndUse` |
| `RulerOkAndUse` | true |
| `role_Ruler:RulerOk` | `Day_no + 1` |
| `role_Ruler:notSend` | true |
| پیام | `RulerNowRul` |
| اثر رأی بعدی | فقط حاکم رأی؛ تایمر = `SE RulerSecendVote` (۴۰ث در SE)؛ متن `RulerMessageVoteNow` |
| پاک‌سازی | night→day حذف `RulerOk`؛ مرگ حاکم قبل از مصرف: حذف `RulerOk` + `RulerIsDead` |

### خواب‌گذار (`Khabgozar_Yes`)

| کلید | مقدار |
|------|--------|
| گارد | `KhabgozarOkUse`؛ فقط وقتی `game_state == day` |
| `KhabgozarOkUse` | true |
| `KhabgozarOk_in` | `Night_no` فعلی |
| `NotSendNight` | `Night_no + 1` |
| `KhabgozarOk` | `Night_no + 1` |
| `role_KhabGozar:notSend` | true |
| پیام | `SandmanSleepAll` |
| اثر شب بعد | تایمر شب ۰؛ `NG::Handel` کامل exit؛ خلاصه شب `SandmanNight` |
| پاک‌سازی | در پایان روز وقتی `KhabgozarOk <= Night_no` (معمولاً روز بعد از شب خواب) |

`Khabgozar_No` فقط تأیید UI (`SelectOk_no`).

### داوینا (`davina_Yes`)

| کلید | مقدار |
|------|--------|
| گارد | `DavinaOkUse`؛ فقط `game_state == day` |
| `DavinaOkUse` | true |
| `DavinaOk_in` | `Day_no` فعلی |
| `NotSendDay` | `Day_no + 1` |
| `DavinaOk` | `Day_no + 1` |
| `role_davina:notSend` | true |
| پیام | `DavinaGroupMessage` |
| اثر روز بعد | تایمر ۳۰ + mute؛ خلاصه `MessageDayWhenDavina`؛ `NotSendDay` کل پخش نقش روز را break می‌کند |
| پاک‌سازی | پایان همان روز داوینا: اگر `DavinaOk <= Day_no` (قبل از +۱ شمارنده) حذف |

### آهنگر (`Ahangar_Yes`)

| کلید | مقدار |
|------|--------|
| گارد | `AhangarOkUse`؛ فقط day |
| `AhangarOkUse` | true |
| اگر `KhabgozarOk_in == Night_no` | دستاورد `Wasted_Silver` |
| `AhangarOk` | `Night_no + 1` |
| `role_Ahangar:notSend` | true |
| پیام | `BlacksmithSpreadSilver` |
| اثر | شب با `AhangarOk` گرگ‌های خورنده / یخی / ملکه (پس از آلفا) کیبورد شب نمی‌گیرند |
| پاک‌سازی | در رأی→شب وقتی `AhangarOk <= Night_no` |

### دردسرساز (`trouble_yes`)

| کلید | مقدار |
|------|--------|
| گارد | `troubleOkUse`؛ فقط day |
| `troubleOkUse` | true |
| `trouble` | true |
| `role_trouble:notSend` | true |
| پیام | `troubleGroupMessage` |
| اثر | پس از حل رأی اول، اگر `trouble` باشد `TroubleVote` + `trouble:ok` و **return** (نمی‌رود شب) |

### گیاه‌شناس (زنجیره؛ نه کیبورد مستقیم نقش)

1. در `SendDayRole` برای هر نقش‌روز: `UserInConvert(uid)`  
2. اگر uid == `BittanPlayer` یا `EnchanterBittanPlayer` → فلگ‌ها: `role_Botanist:bittaned=uid`, `bittaned:for=wolf`؛ PV با `UserBittenByWolf` + `DaySelect_SendBittenYes|No`  
3. اگر uid == `VampireBitten` → `for=vampire`؛ `UserBittenVampire`  
4. Yes → پیام به گیاه‌شناس `BotanistMessage` + دکمه‌های `BotanistOk|No`؛ ذخیره `role_Botanist:link`  
5. Ok → پاک گاز مربوطه؛ پیام به تیم گرگ/ومپایر `BotanistMessageOk`؛ به گیاه‌شناس `BotanistM`؛ به گازگرفته `OkMessagePlayer`؛ `DelKey role_Botanist:*`  
6. No → به گازگرفته `BotanistNo`؛ پاک کلیدها  

**نقص PHP:** فقط اگر گازگرفته خودش در لیست نقش‌روز باشد `UserInConvert` صدا می‌خورد؛ روستایی سادهٔ گازگرفته معمولاً پرامپت نمی‌گیرد.

### انتخاب‌های معوق (فقط ذخیره `Selected:{actor}`)

کارآگاه، شاهدخت، دینامیت، شوالیه سیاه، دیان، کنت، جاسوس، تفنگدار — اثر در `CheckDay`.

---

# ۶. CheckDay — ترتیب دقیق resolve

قفل: اگر `GamePl:CheckDay` باشد return؛ وگرنه ست true.

| ترتیب | تابع | خلاصه اثر | قطع ادامه؟ |
|-------|------|-----------|------------|
| ۱ | `CheckTofangdar` | شلیک؛ گلوله −۱؛ ریش‌سفید→تفنگدار روستایی؛ کلانتر→`HunterKill`+مرگ+حذف Selected تفنگدار | بعد از کل تابع: اگر `HunterKill` → **return کل CheckDay** |
| ۲ | `CheckBlackKnight` | مرگ علنی هدف + نقش در گروه | خیر |
| ۳ | `GetDinamit` | جستجوی بمب / پیام پیدا یا شکست / تکرار خانه | خیر |
| ۴ | `CheckKaragah` | استعلام نقش (ماسک عسل→نام گرگ)؛ اگر تیم گرگ: `KaragahS` با شانس &lt;۴۰ یک‌بار هشدار به گرگ‌ها | خیر |
| ۵ | `CheckSpy` | بله/خیر «خطرناک» بر اساس جدول نقش (+ ملکه فقط اگر آلفا مرده) | خیر |
| ۶ | `CheckPrincess` | فقط اگر `Night_no > 2`؛ زندان / فرار / مصونیت طبق نقش هدف | خیر |
| ۷ | `CheckDian` | روز۲: علامت + `DianSelectedPlayerDayNo = Day_no+4`؛ وگرنه ۵۰٪ دیدن نقش | خیر |
| ۸ | `CheckKent` | فقط با `KentVampireConvert`؛ قتل علنی | خیر |

صلح / کدخدا / حاکم / آهنگر / خواب‌گذار / داوینا / دردسر / گیاه‌شناس در `CheckDay` نیستند.

### جزئیات مهم resolve

- **تفنگدار→کلانتر:** پیام گروه از مسیر `HunterKill` می‌رود؛ `PlusTime(45)`؛ کیبورد `HunterShotChoice` برای کلانتر؛ بقیهٔ CheckDay اجرا نمی‌شود.  
- **جاسوس بله:** گرگ‌های پایه، قاتل، کماندار، شکار، کلانتر، تفنگدار، آتش‌نشان، ملکه یخ، ومپایر، خون‌آشام، شوالیه؛ ملکه جنگل فقط با `role_forestQueen:AlphaDead`.  
- **شاهدخت:** قاتل/شوالیه با شانس فرار `EscapeKillerKnight`؛ شکار و حاکم پیام مصونیت بدون زندان؛ خون‌آشام فرار تیمی بدون `PrincessPrisoner`؛ آتش/یخ «پیدا نشد»؛ پیش‌فرض `SendPrincessMessage` → `PrincessPrisoner:{uid}=true`.  
- **دیان روز۲:** اگر هدف مرده → فقط PV `DianSelectedTowDayIsDie`.  
- **کارآگاه:** متغیر ماسک عسل ممکن است unset بماند اگر Honey نباشد (در PHP Notice؛ در عمل نقش واقعی نشان داده می‌شود).

---

# ۷. Early-end روز

**وجود ندارد.**

`HL::checkTime` فقط برای `night` و `vote` شاخه دارد؛ برای `day` هیچ کاری نمی‌کند. روز فقط با سررسید `timer` یا تمدید `HunterKill` (+۴۵) تمام می‌شود / کش می‌آید.

---

# ۸. انتقال day → vote

وقتی `LeftTime <= 0` و `game_state == day`:

1. `DY::CheckDay()`  
2. اگر `HunterKill` → **return** (وضعیت هنوز day؛ تایمر تمدیدشده؛ تیک‌های بعد `CheckKalantar` را در ابتدای CheckTimer می‌زنند)  
3. `ChangeGameStatus('vote')`:
   - تایمر رأی عادی / مخفی از تنظیمات  
   - اگر `role_Ruler:RulerOk` → تایمر = `RulerSecendVote`  
   - اگر `role_Solh:GroupInSolh` → تایمر = ۰  
4. پاک‌سازی خواب‌گذار اگر `KhabgozarOk <= Night_no`  
5. پاک‌سازی داوینا اگر `DavinaOk <= Day_no` (**قبل از** افزایش Day_no)  
6. `Del CheckDay`, `Del SendNight`  
7. `Day_no = Day_no + 1`  
8. موعد دیان: اگر `DianSelectedPlayerDayNo == Day_no جدید` و هدف زنده → پیام `DianAfterFourDay` + `GamedEnd('black')`  
9. بعد از switch: `EditMarkupKeyboard`؛ پاک `Selected:*`؛ `CheckEndGame`؛ `GetGameStatusLang` برای رأی + ارسال صف گروه  

پاک `SendDayRole` در این انتقال نیست؛ در **رأی→شب** پاک می‌شود تا روز بعد دوباره پخش شود.

---

# ۹. کلیدهای Lang (روز)

### خلاصه / فاز

`MassgeFortypeSummery_day`, `Day_nos`, `NoAttakInDay`, `MessageDayWhenDavina`, `SandmanNight` (شب مرتبط), `RulerMessageVoteNow`, `MassgeFortypeSummery_vote`, `MassgeFortypeSummery_Secretvote`

### عاشق

`CupidChosen`, `CupidChosen2`, `RomanticModeMessage`

### کیبورد / تأیید

`SelectOk`, `SelectOk_no`, `ErrorSelect`, `NotFoundPlayer`, `Error_NotInGame`, `DodgeYou`

### صلح

`solh_L`, `solh_btn`, `PacifistNoLynch` (+ `PacifistNoLynchNow` در بانک؛ مسیر روز عمدتاً اولی)

### کدخدا / حاکم

`Kadkhoda_l`, `Kadkhoda_btn`, `MayorReveal`, `RulerAsk`, `RulerButton`, `RulerNowRul`, `RulerIsDead`

### خواب / آهن / داوینا / دردسر

`KHABGOZAR_l`, `KHABGOZAR_BTN`, `KHABGOZAR_BTN_N`, `SandmanSleepAll`, `ahangar_L`, `ahangar_btn`, `ahangar_btnY`, `BlacksmithSpreadSilver`, `AskDavina`, `DavinaYes`, `DavinaNo`, `DavinaGroupMessage`, `Asktrouble`, `troubleBtnYes`, `troubleBtnNo`, `troubleGroupMessage`, `troubleGroupMessageS`

### گیاه‌شناس

`UserBittenByWolf`, `UserBittenVampire`, `Btn_okSend`, `Btn_NotOk`, `BotanistMessage`, `btnOkUser`, `btnNoUser`, `OkSendToBotanist`, `BotanistMessageOk`, `BotanistM`, `OkMessagePlayer`, `BotanistNo`

### معوق / CheckDay

`AskShoot`, `DefaultShot`, `GunnerShotWiseElder`, `HunterShotChoice`, `HunterKilledFinalShot`, `HunterSkipChoiceShot`, `HunterNoChoiceShot`, `howEstelamIs`, `DetectiveSnoop`, `KaragahSForWolf`, `SpyAsk`, `SpySeeMessage`, `SpySeeMessageNo`, `AskPrincess`, `PrincessPrisoner*`, `BlackKnightAsk`, `BlackKnightDeadPlayerGroup`, `BlackKnightDeadPlayerMessage`, `AskDinamit_day`, `DinamitSuccessFind`, `DinamitFiledFind`, `DinamitLastFind`, `DinamitFind_*`, `AskDianDay`, `AskDianTowDay`, `DianSee`, `DianNotSee`, `DianSelectedPlayerGroupMessage`, `DianSelectedTowDayIsDie`, `DianAfterFourDay`, `AskDayKentVampire`, `KentVampireKillPlayer`, `user_role`, `role_*_n`

---

# ۱۰. چک‌لیست QA

- [ ] شب بدون وقفه → روز با `Day_no` بدون تغییر و تایمر از `day_timer`  
- [ ] شب اول (`Day_no==1`) قبل از روز `CheckDontSelectRole` اجرا شود  
- [ ] داوینا از روز قبل: روز بعد ۳۰ث + mute + بدون کیبورد نقش روز + متن `MessageDayWhenDavina`  
- [ ] بدون Kill و بدون خواب‌گذار فعال: `NoAttakInDay` در صف گروه  
- [ ] عاشق فقط در `Day_no <= 2` و فقط یک‌بار per uid  
- [ ] زندان شاهدخت / یخ با `Night_no` / `NotSendDay` گیت‌ها  
- [ ] شاهدخت قبل از `Night_no > 2` کیبورد نگیرد  
- [ ] تفنگدار با گلوله ۰ کیبورد نگیرد؛ بعد از شلیک گلوله −۱  
- [ ] شلیک به کلانتر: بقیه CheckDay نرود؛ +۴۵ث؛ هنوز day  
- [ ] شلیک به ریش‌سفید: تبدیل تفنگدار به روستایی  
- [ ] صلح: فلگ `GroupInSolh=Day_no+1`؛ رأی بعدی تایمر ۰ / بدون لینچ  
- [ ] کدخدا یک‌بار افشا؛ دوبار کلیک بی‌اثر  
- [ ] حاکم: رأی بعدی فقط او و ۴۰ث  
- [ ] خواب‌گذار: شب بعد تایمر ۰ و بدون اکشن شب  
- [ ] آهنگر: شب بعد گرگ‌ها skip؛ همزمانی با اعلام خواب → دستاورد نقره  
- [ ] دردسر: بعد از رأی اول دور دوم رأی بدون شب  
- [ ] کنت بدون `KentVampireConvert` نه کیبورد نه resolve  
- [ ] دیان روز۲ علامت چهارروزه؛ در موعد اگر زنده → برد black  
- [ ] ترتیب CheckDay دقیقاً مطابق جدول بخش ۶  
- [ ] روز early-end نداشته باشد حتی اگر همه Selected پر باشد  
- [ ] بعد از day→vote: `Day_no+1` و پاکی Selected؛ `SendDayRole` تا رأی→شب بماند  
- [ ] داج لوسیفر: قربانی `DodgeYou`، انتخاب روی Selected قربانی  
- [ ] گیاه‌شناس: مسیر گاز گرگ و ومپایر جدا؛ Ok گاز را پاک کند  

---

# ۱۱. نقایص / باگ / ناقصی PHP یافت‌شده

1. **`GamedEnd` دیان بدون return:** در شاخهٔ day از `CheckTimer`، پس از `GamedEnd('black')` اجرا ادامه می‌یابد (`EditMarkupKeyboard`، `CheckEndGame`، ساخت پیام وضعیت رأی، `SendGroupMessage`). وضعیت قبلاً به `vote` رفته. باید بعد از پایان بازی قطع قطعی شود.  

2. **`DianAfterFourDay` بدون جایگذاری نام:** `SaveMessage` فقط یک آرگومان می‌گیرد؛ آرایهٔ `{0}=>$U_name` نادیده گرفته می‌شود و متن احتمالاً بدون نام می‌ماند.  

3. **`CheckBlack` خالی:** تابع بدنه ندارد؛ اگر `StopBlack` ست شود تایمر آن را صدا می‌زند ولی اثری نیست (از قبل در اسپرینت ۵ه ثبت شده؛ برای روز هم وقفهٔ بی‌اثر می‌سازد).  

4. **گیاه‌شناس فقط روی نقش‌روز:** `UserInConvert` فقط داخل حلقهٔ `SendDayRole` است؛ گازگرفتهٔ بدون نقش‌روز پرامپت نمی‌گیرد. خود `role_Botanist` در لیست ارسال نیست.  

5. **`case 'SendBittenNo'` تکراری** در `DaySelectedCheck` (دو بار) — دومین مورد unreachable در PHP.  

6. **`ChangeGameStatus` آپدیت Mongo:** فیلد `$set` شامل عنصر بی‌کلید `'timer'` است (آرایهٔ PHP با کلید عددی) — احتمال نوشتن فیلد اشتباه در سند بازی.  

7. **کارآگاه / `$HoneyChangeRole`:** اگر Honey نباشد متغیر ممکن است تعریف‌نشده بماند (Notice در نسخه‌های سخت‌گیر).  

8. **شمارندهٔ کامل SendDayRole:** بعد از `rpush`، `continue 2` بدون ارسال کیبورد همان uid را «ارسال‌شده» می‌کند تا پایان لیست روز؛ برای شاهدخت/کنت/گلوله معمولاً با پاک‌سازی شب بعد جبران می‌شود، ولی داخل همان روز retry نیست.  

9. **`NotSendDay` با `break`:** اولین برخورد کل حلقه را می‌بندد — بازیکنانی که قبل از برخورد در لیست نبوده‌اند/بعداً می‌آیند در همان تیک از دست می‌روند (معمولاً مطلوب روز داوینا است).  

10. **داج فقط برای زیرمجموعهٔ نقش‌ها:** BlackKnight / دینامیت / دیان / فوری‌ها در `CheckDodge` نیستند؛ اگر داج روی آن‌ها ست شود رفتار ناقص/ناهمگون است.  

11. **کامنت غلط در CheckTofangdar/Karagah:** کامنت «اگر قاتل نبود» کپی‌پیست از قاتل شب است؛ منطق درست نقش روز است.  

این‌ها را در پورت پایتون یا عیناً هم‌رفتار کنید یا با تصمیم محصول صریح اصلاح و در QA علامت بزنید — پیش‌فرض اسپرینت: **هم‌ارزی PHP** مگر خلافش نوشته شود.

---

# ۱۲. قرارداد stub / پورت

- ترتیب اسلات‌های `CheckDay` جابه‌جا نشود.  
- فلگ‌های فوری باید همان نام کلید Redis را داشته باشند (مقادیر عددی `Day_no+1` / `Night_no+1` مهم‌اند، نه فقط boolean).  
- Early-end روز اضافه نکنید.  
- بعد از `GamedEnd` در موعد دیان در پایتون بهتر است return اجباری بگذارید حتی اگر PHP ادامه می‌دهد — یا صریحاً باگ را replicate کنید و در تست ثبت کنید.
