# اسپرینت ۵الف — تیم فرقه + شکارچی فرقه (shekar) + رویس / مومیایی / فرانک

**پیش‌نیاز:** اسپرینت ۱–۴ (شب، گاز، جفت‌نقش، برد)  
**هدف:** اکشن شب و سایدافکت مرگ برای دستهٔ فرقه، هم‌ارز PHP  
**مرجع:** `NG::SendNightRole` / `CheckCult` / `CultAttemp` / `GetCultHunter` / `GetFranc` / `GetMummy`، `HL::UserDead` / `CheckFranc` / `CheckMummy` / `RoyceDeadSelect`، `CM` انتخاب شب  

> **نقش جدید (نه PHP):** دارنشان🕯️ — مشخصات کامل در [`change-spec-role-darneshan-fa.md`](change-spec-role-darneshan-fa.md) (`product-new`؛ در این اسپرینت هم‌ارزی پیاده نشود).

---

# ۱. تحلیل و استدلال

دو لایهٔ تیم را قاطی نکنید:

1. **Mongo `ferqeTeem`** — `role_ferqe`, `role_Royce`, `role_Mummy`, `role_franc` (برد، پیام تیمی، `_GetByTeam`).  
2. **سطل عملیاتی `PlayerByTeam()['ferqe']`** — فقط `role_ferqe` + `role_Royce` + `role_Mummy` (رأی تبدیل و شرط `CheckFranc`). **فرانک داخل این سطل نیست.**

تبدیل موفق همیشه فوری به `role_ferqe` است (`ConvertPlayer` + `SendNight`). شانس‌های `CultAttemp` داخل `NG` هاردکدند؛ ثابت `SE::_s('CultConvertVampie')=50` در سورس مصرف نمی‌شود.

ترتیب حل شب (اسپرینت ۱): **شکارچی قبل از فرقه** (`GetCultHunter` → `CheckCult`). مرگ رویس در انتهای همان `CheckNight` وقفهٔ انتخاب دوم می‌سازد.

---

# ۲. محدوده

## داخل
- کیبورد شب و گیت‌های skip برای ferqe / Royce / shekar / Mummy / franc  
- الگوریتم کامل `CheckCult` و جدول `CultAttemp`  
- `GetCultHunter` و شاخه‌های قاتل / گرگ / دلبر / کلانتر / فرانک / مومیایی  
- مرگ: `RoyceDead`, `ConvertCult`, `DieCult`, `FrancNightOk`, زنجیره هانتسمن←شکارچی  
- کلیدهای lang دسته

## خارج
- عمق کامل قاتل/آتش/ومپایر/سیاه (اسپرینت‌های بعدی)  
- polish متن پیام  
- برد فرقه (اسپرینت ۴ — تغییر نکند مگر باگ هم‌ارزی)

---

# ۳. شناسنامه نقش‌ها

| نقش | تیم Mongo | در سطل ferqe رأی؟ | اکشن شب |
|-----|-----------|-------------------|---------|
| `role_ferqe` | ferqeTeem | بله | دعوت/تبدیل (`AskConvert`) |
| `role_Royce` | ferqeTeem | بله | همان + مرگ → شب ویژه |
| `role_Mummy` | ferqeTeem | بله (شمارش) | محافظ فقط بعد از `DieCult` |
| `role_franc` | ferqeTeem | خیر | محافظ؛ بعد از خالی شدن سطل ferqe → قاتل |
| `role_shekar` | روستا | — | شکار خانه (`howToHoHome`) |

جفت کانفیگ (اسپرینت ۳): ferqe ↔ shekar ↔ Royce؛ پیش‌بالانس: ferqe/Royce بدون shekar → تزریق shekar؛ بالانس: franc نیازمند ferqe.

---

# ۴. کیبورد شب و گیت‌های skip

گیت‌های مشترک `SendNightRole` (قبل از case نقش): قبلاً در `SendNight`؛ `NotSend_{role}`؛ یخ‌زدهٔ شب قبل؛ زندانی شاهدخت؛ `NotSendNight == Night_no`؛ `NotSend:{uid} == Night_no`.

## ۴.۱ فرقه‌گرا / رویس

| مورد | مقدار |
|------|--------|
| متن | `AskConvert` (+ `DiscussWith` اگر هم‌تیمی نام‌دار باشد) |
| callback | `NightSelect_Ferqe` |
| کیبورد | همه زنده به‌جز اعضای سطل ferqe |
| ذخیره CM | اگر `_GetByTeam(ferqeTeem) > 1`: رأی تیمی `Selected:Cult:{target}` + پیام `CultistVotedConvert`؛ وگرنه فقط `Selected:{uid}` |
| نکته | `_GetByTeam` شامل فرانک/مومیایی هم هست → با یک فرقه + فرانک زنده، مسیر «تیمی» فعال می‌شود حتی اگر فقط یک رأی‌دهندهٔ تبدیل باشد |

## ۴.۲ شکارچی (`role_shekar`)

| مورد | مقدار |
|------|--------|
| متن | `howToHoHome` |
| callback | `NightSelect_Shekar` |
| ذخیره | `Selected` + `UserInHome` (نام و نقش مهاجم) |
| skip ویژه | فقط گیت‌های مشترک |

## ۴.۳ مومیایی

| مورد | مقدار |
|------|--------|
| شرط ارسال | فقط اگر `GamePl:DieCult` ست باشد؛ وگرنه `continue` (کیبورد نمی‌آید) |
| متن | `AskMummy` |
| callback | `NightSelect_Mummy` |
| کیبورد | زنده‌ها به‌جز اعضای سطل ferqe (`in_list=true`) |
| ذخیره | `role_Mummy:AngelIn:{هدف}` + `AngelNameSaved` + `Selected` + `UserInHome` |

`DieCult` از اولین مرگ یک `role_ferqe` (نه رویس) با `CheckMummy(..., kill)` می‌آید.

## ۴.۴ فرانک

| حالت | متن | کیبورد | ذخیره CM |
|------|-----|--------|----------|
| بدون `FrancNightOk` | `AskFranc` | زنده‌ها به‌جز سطل ferqe؛ پارامتر سوم true | محافظ: `AngelIn` + `AngelNameSaved` + `UserInHome` |
| با `FrancNightOk` | `FrancAskNight` | همه به‌جز خودش | فقط `Selected` (قتل؛ بدون AngelIn) |

فعال‌سازی `FrancNightOk`: در `UserDead` اگر `team == ferqeTeem` → `CheckFranc`: اگر سطل `PlayerByTeam()['ferqe']` خالی و فرانک زنده → پیام `FrancDeadCult`، `NotSend` همان شب، `FrancNightOk=true`.  
**گاتچا:** مومیایی زنده سطل ferqe را غیرخالی نگه می‌دارد → فرانک قاتل نمی‌شود تا مومیایی هم از سطل خارج شود (بمیرد/تبدیل نشود چون مومیایی تبدیل‌پذیر از فرقه نیست در مسیر عادی).

---

# ۵. ترتیب حل شب (دسته)

داخل `CheckNight` (پس از قاتل/شیمیدان/آتش/کماندار/ومپایر):

1. `GetCultHunter`  
2. `CheckCult`  
3. … نقش‌های دیگر …  
4. `GetFranc` (بعد از لیلیس/عجوژه/کنت)  
5. در انتها: اگر `RoyceDead == Night_no` → `RoyceDeadSelect` (بدون return اجباری کل شب)

`GetMummy` در سورس تعریف شده ولی از pipeline صدا زده نمی‌شود — بازخورد «حمله نخورد» مومیایی در عمل ارسال نمی‌شود؛ محافظت همچنان در لحظهٔ حمله با `AngelIn` کار می‌کند.

---

# ۶. `CheckCult` — الگوریتم گام‌به‌گام

1. سطل ferqe خالی → خروج.  
2. اگر `RoyceSelectd2` و `RoyceDead == Night_no` → پاک کردن `CheckNight` / `SendNightAll` / `RoyceDead` / `RoyceSelectd2` (پایان وقفهٔ شب ویژه؛ سپس ادامهٔ resolve).  
3. `CultMummy = ConvertCult ? 20 : 0`.  
4. هدف:
   - اگر `count(ferqe) > 1`: `GetTeamCultSelected()` (بیشترین رأی در `Selected:Cult:*`؛ در تساوی اولین max پس از sort). خالی → خروج. بازدیدکنندهٔ نمایشی = آخرین `role_ferqe` از نظر `change_time` (`_getLastCult`) وگرنه عضو اول.  
   - اگر دقیقاً ۱ نفر در سطل: نیاز به `Selected:{uid}`؛ همان انتخاب.  
5. هدف نامعتبر/نیست → خروج.  
6. ثبت `UserInHome` برای بازدیدکننده؛ پاک `Selected:Cult:*`.  
7. هدف مرده → `CultVisitDead` / `CultVisitDeadOne` به تیم؛ پایان.  
8. تله هانتسمن روی هدف: با رول `R(100) >= 50` و هانتسمن زنده → مرگ بازدیدکننده (`HuntsmanKill`)، پیام‌های هانتسمن/بازدیدکننده/گروه/تیم؛ حذف تله.  
9. زندانی شاهدخت → `PrincessPrisonerCultAttack` به تیم؛ پایان.  
10. اگر هدف `role_qhost` → `GostFinded`.  
11. سوئیچ نقش هدف (بخش ۷).

موفقیت تبدیل مشترک: PV `CultConvertYou`، تیم `CultJoin`، `rpush SendNight`، `ConvertPlayer → role_ferqe`.

---

# ۷. شاخه‌های ویژه هدف در `CheckCult`

فرض: `CultMummy` = ۰ یا ۲۰.

### دلبر (`role_Sweetheart`)
- اگر `SweetheartLove:team == Cult` → تبدیل قطعی.  
- وگرنه: عاشق کردن بازدیدکننده (`LoverBYSweetheart(..., Cult)`)، پیام‌های `MsgPlayerCultLoved` / `MsgPlayerCultsLoved` / `MsgPlayerLoveCultsMessage`؛ بدون تبدیل هدف.

### قاتل (`role_Qatel`)
- اگر `R < (50 - CultMummy)` → مرگ بازدیدکننده + `CultConvertKillerPublic` / `One`.  
- else اگر هدف در خانه (`UserInHome:{selected}`) → `CultVisitEmpty*`.  
- else → باز هم مرگ بازدیدکننده با همان پیام‌های عمومی.  
**هیچ مسیر تبدیلی برای قاتل نیست.**

### ومپایر (`role_Vampire`)
- اگر `R < (50 - CultMummy)` → مرگ بازدیدکننده (`Vampire_Convert`) + `VampireDeadCult` (+ تیم `VamireDeadCultR`).  
- else → `CultVisitEmpty*`.

### اصیل (`role_Bloodthirsty`)
- اگر `VampireFinded`:
  - اگر `R < (50 - CultMummy)` → تبدیل بازدیدکننده به ومپایر (`VampireConvert`) + پیام‌های تیم/فرد.  
  - else → مرگ بازدیدکننده + `GroupMessageDeadCult`.  
- اگر هنوز لو نشده → فقط `CultAttempt` به هدف + `CultVisitAttemp*` (بدون مرگ/تبدیل).

### شکارچی فرقه (`role_shekar`) — قطعی
- گروه `CultConvertCultHunter`؛ مرگ بازدیدکننده؛ PV شکارچی `CultHunterKilledCultVisit`.

### کلانتر (`role_kalantar`)
1. اگر `R < (50 + CultMummy)` → تبدیل موفق.  
2. else اگر `R < (50 - CultMummy)` → مرگ بازدیدکننده با `CultConvertHunter` (علت `shot`).  
3. else → `CultAttempt` + `CultVisitAttemp*`.

### گرگ پایه (Tolle / Gorgine / Wolfx / Alpha)
- اگر هدف در خانه → `CultVisitEmpty*`.  
- else → مرگ بازدیدکننده `CultConvertWolfPublic` (علت `eat`).  
(ملکه/سفید/جادوگر اینجا نیستند → default / CultAttemp.)

### فراماسون — تبدیل قطعی + `SendMasonAfterChangeRole`.

### default
- خانه خالی هدف → `CultVisitEmpty*`.  
- else `CultAttemp(role)`: ۱ → تبدیل؛ ۰ → `CultAttempt` + `CultVisitAttemp*`.

---

# ۸. جدول `CultAttemp` (شانس تبدیل)

فرمول: موفقیت اگر `R(100) < (پایه + CultMummy)`؛ `CultMummy` فقط وقتی `ConvertCult` ست است (+۲۰).  
قطعی = همیشه ۱؛ مقاوم = همیشه ۰. نقش‌های خارج جدول → ۰.

| نقش هدف | پایه | با ConvertCult |
|---------|------|----------------|
| روستایی ساده، پسر گیج، ناظر، احمق، مست، خائن، منافق، کدخدا، دلبر†، حاکم، شاهزاده، تفنگدار، فراماسون†، پیش‌رزرو، الهه، وحشی، گرگنما، قاضی، دلقک | قطعی ۱ | ۱ |
| عسل | ۶۰ | ۸۰ |
| پیشگو / نگاتیو / Augur / جادوگر گرگ / دردسرساز | ۴۰ | ۶۰ |
| شیمیدان | ۵۰ | ۷۰ |
| افسونگر / نفرین‌شده / خوابگزار | ۶۰ | ۸۰ |
| شوالیه / جاسوس / ریش‌سفید | ۳۰ | ۵۰ |
| گیاه‌شناس / لوسیفر†† / فاحشه | ۷۰ | ۹۰ |
| آهنگر | ۷۵ | ۹۵ |
| صلح‌جو / کاراگاه | ۸۰ | ۱۰۰ (عملاً قطعی با باف) |
| ملکه یخ، آتش‌نشان، کماندار، ملکه جنگل، گرگ سفید، `role_lucifer` (حروف کوچک)، هانتسمن، همزاد | ۰ | ۰ |
| default (شامل فرشته، فرانک، مومیایی، رویس، فرقه، قاتل، شکار، کلانتر‡، …) | ۰ | ۰ |

† دلبر/فراماسون در سوئیچ `CheckCult` جداگانه قبل از CultAttemp هندل می‌شوند.  
†† `role_lucifer` مقاوم ۰ ولی `role_Lucifer` شانس ۷۰ دارد — ناسازگاری نام در سورس؛ در بازنویسی آگاهانه یکی را انتخاب کنید.  
‡ کلانتر/شکار/قاتل/گرگ پایه در سوئیچ ویژه؛ به CultAttemp نمی‌رسند.

`SE::_s('CultConvertVampie')` به این جدول وصل نیست.

---

# ۹. `GetCultHunter` — الگوریتم

گیت: نقش هست، زنده، `Selected` دارد. Kenyager → هدف تصادفی.

1. هدف مرده → `HunterVisitDead`؛ خروج.  
2. تله هانتسمن مثل فرقه (۵۰٪ مرگ شکارچی).  
3. شفای مجیک → پیام بلاک به دو طرف؛ خروج.  
4. سوئیچ هدف:

| هدف | نتیجه |
|-----|--------|
| دلبر با عشق `CultHunter` | `HunterFailedToFind` |
| دلبر دیگر | `LoverBYSweetheart(..., CultHunter)` + `MsgPlayerCHLoved` |
| قاتل | مرگ شکارچی `SerialKillerKilledCH` |
| فرانک | ۱۰٪ (`R<=10`): مرگ شکارچی (`CultHunterFrancMessage` / `CultHunterKillByFrancGroup`)؛ وگرنه مرگ فرانک (`CultHunterKillFranc*`) |
| `role_ferqe` یا `role_Royce` | PV شکار `HunterFindCultist`؛ PV قربانی `HunterKilledCultistOn`؛ گروه `HunterKilledCultist`؛ مرگ هدف؛ شمارش `HunterKillFerqe` برای دستاورد ≥۳؛ اگر `AngelIn` مومیایی روی قربانی → مومیایی هم می‌میرد با پیام‌های `MummyCultHunter*` |
| سایر | `HunterFailedToFind` |

مومیایی و فرانک (در حالت محافظ) در default شکست شکار هستند مگر شاخهٔ franc.

---

# ۱۰. سایدافکت مرگ (`HL::UserDead`)

| تریگر | اثر |
|-------|-----|
| مرگ `role_ferqe` | `CheckMummy(..., kill)`: اگر مومیایی زنده و هنوز `DieCult` نباشد → PV `MummyMessageWhenKillCult` + `DieCult=true` (فعال‌سازی کیبورد مومیایی از شب بعد) |
| مرگ `role_Royce` (غیر afk) | تیم `RoyceDead`؛ `RoyceDead = Night_no + 1`؛ `CheckMummy(..., royce)`: اگر هنوز `ConvertCult` نباشد و مومیایی زنده → تیم `AfterDieRoyce` + `ConvertCult=20` |
| مرگ `role_Royce` با afk | فلگ شب ویژه و پیام RoyceDead ست نمی‌شود |
| مرگ هر `ferqeTeem` | `CheckFranc` (بخش ۴.۴) |
| مرگ `role_shekar` | اگر هانتسمن زنده → `NotSend` همان شب + `HuntsmanDeadCultHulter` + تبدیل هانتسمن به `role_shekar` |
| `ConvertCult` / `DieCult` یک‌بارمصرف | تکرار پیام/باف با فلگ موجود بلاک می‌شود |

### شب ویژه رویس (`RoyceDeadSelect`)
وقتی در انتهای CheckNight مقدار `RoyceDead == Night_no`: بستن کیبورد، `RoyceSelectd2=true`، پاک همه `Selected:*`، +۳۰ثانیه، حذف فرقه از `SendNight`، پاک `CheckNight`/`SendNightAll` تا دوباره انتخاب کنند. حل بازدید دوم در `CheckCult` بعدی است.

اگر هنگام حل لیست زنده هنوز `RoyceDead` ست باشد، پاک کردن فلگ `Kill` برای لیست بازیکنان به تعویق می‌افتد (مشابه HunterKill / توله).

---

# ۱۱. `GetFranc` در resolve

- بدون انتخاب / مرده / نقش نیست → خروج.  
- هدف مرده → خروج خاموش.  
- اگر `FrancNightOk`: گروه `FrancKillGroupMessage` (نام + نقش کوتاه)، مرگ هدف، PV `FrancKillPlayerMessage`.  
- وگرنه (حالت محافظ): اگر `AngelSaved` ست نباشد → PV `NotAttackFeranc` با نام ذخیره‌شده؛ پاک کلیدهای نام/سیو.

محافظت واقعی در حملات دیگر (گرگ یخی، ومپایر، کماندار، قاتل، …) با چک `role_franc:AngelIn:{uid}` و ست کردن `AngelSaved` انجام می‌شود — هم‌الگوی فرشته.

---

# ۱۲. تعاملات کلیدی دسته

| طرف مقابل | رفتار |
|-----------|--------|
| شکارچی ↔ فرقه/رویس | شکار قبل از resolve فرقه؛ کشت قطعی + زنجیره مومیایی |
| شکارچی ↔ قاتل | قاتل شکارچی را می‌کشد |
| شکارچی ↔ فرانک | ۱۰٪ مرگ شکارچی وگرنه مرگ فرانک |
| فرقه ↔ قاتل | فقط خطر مرگ بازدیدکننده (جدول CultMummy)؛ بدون تبدیل |
| فرقه ↔ گرگ پایه | خوردن بازدیدکننده مگر خانه خالی |
| فرقه ↔ کلانتر | تبدیل / شلیک / شکست سه‌مرحله‌ای با باف مومیایی |
| فرقه ↔ دلبر | عشق Cult یا تبدیل اگر از قبل عاشق فرقه |
| مومیایی | باف ConvertCult؛ دفاع AngelIn؛ مرگ همراه قربانی اگر شکارچی بکشد |
| هانتسمن | تله روی هدف بازدید؛ جانشینی شکارچی |
| شاهدخت | زندانی → فرقه حمله را با پیام تیم رها می‌کند |

---

# ۱۳. کلیدهای Lang (دسته)

### نقش / پرس شب
`role_ferqe`, `role_ferqe_n`, `role_ferqe_team`, `role_Royce`, `role_Royce_n`, `role_Mummy`, `role_Mummy_n`, `role_franc`, `role_franc_n`, `role_shekar`, `role_shekar_n`, `AskConvert`, `DiscussWith`, `AskFranc`, `FrancAskNight`, `AskMummy`, `howToHoHome`, `CultistVotedConvert`

### تبدیل / بازدید فرقه
`CultConvertYou`, `CultJoin`, `CultAttempt`, `CultVisitAttemp`, `CultVisitAttempOne`, `CultVisitEmpty`, `CultVisitEmptyOne`, `CultVisitDead`, `CultVisitDeadOne`, `CultConvertCultHunter`, `CultHunterKilledCultVisit`, `CultConvertHunter`, `CultConvertWolfPublic`, `CultConvertKillerPublic`, `CultConvertKillerPublicOne`, `VampireDeadCult`, `VamireDeadCultR`, `VampireMessageCultConvert`, `BloodthirstyCultMessageConvert`, `PlayerMessageConvertToVampire`, `GroupMessageDeadCult`, `MsgPlayerCultLoved`, `MsgPlayerCultsLoved`, `MsgPlayerLoveCultsMessage`, `PrincessPrisonerCultAttack`, `PrincessPrisonerCultTeam`

### شکارچی
`HunterVisitDead`, `HunterFindCultist`, `HunterFailedToFind`, `HunterKilledCultist`, `HunterKilledCultistOn`, `SerialKillerKilledCH`, `CultHunterFrancMessage`, `CultHunterKillByFrancGroup`, `CultHunterKillFrancMessage`, `CultHunterKillFrancGroup`, `MsgPlayerCHLoved`, `CHKillsCultistEnd`, `HuntsmanDeadCultHulter`

### رویس / مومیایی / فرانک
`RoyceDead`, `AfterDieRoyce`, `MummyMessageWhenKillCult`, `MummyAngel`, `MummyAngelPlayerMessage`, `MummyAngelMummyMessage`, `MummyAngelOne`, `MummyAngelTeam`, `MummyCultHunterMessage`, `MummyCultHunterKill`, `MummyCultHunterKillGroupMessage`, `FrancDeadCult`, `FrancKillGroupMessage`, `FrancKillPlayerMessage`, `NotAttackFeranc`, `PlayerMessageFrancS` (در بلاک حملات)

### تنظیمات گروه (مرتبط)
`Hunting_shekar`, `Hunting_shekar_day`

---

# ۱۴. فلگ‌های State (مرجع سریع)

| کلید | معنی |
|------|------|
| `Selected:Cult:*` | رأی تیمی تبدیل |
| `ConvertCult` | باف +۲۰ (پس از مرگ رویس با مومیایی زنده) |
| `DieCult` | اولین مرگ ferqe → باز شدن کیبورد مومیایی |
| `RoyceDead` | شماره شبی که انتخاب دوم می‌آید |
| `RoyceSelectd2` | وقفهٔ انتخاب دوم فعال |
| `FrancNightOk` | فرانک در حالت قتل |
| `role_Mummy:AngelIn:*` / `AngelSaved` / `AngelNameSaved` | محافظ مومیایی |
| `role_franc:AngelIn:*` / مشابه | محافظ فرانک |
| `HunterKillFerqe:{uid}` | شمار کشت فرقه برای دستاورد |
| `NotSend:{uid}` | یک شب بدون کیبورد (فرانک پس از بیداری قتل؛ هانتسمن پس از ارتقا) |

---

# ۱۵. معیار پذیرش QA — دسته ۵الف

### کیبورد / گیت
- [ ] ferqe تنها: `AskConvert` بدون DiscussWith تیمی اجباری  
- [ ] چند عضو ferqeTeem در Mongo: رأی Cult + `CultistVotedConvert`  
- [ ] shekar هر شب `howToHoHome` مگر NotSend/یخ/زندان  
- [ ] Mummy قبل از `DieCult` کیبورد نگیرد؛ بعد از مرگ اولین ferqe بگیرد  
- [ ] Franc بدون FrancNightOk محافظ؛ با فلگ متن `FrancAskNight` و قتل  
- [ ] مرگ همه ferqe+Royce+Mummy → FrancNightOk؛ اگر Mummy زنده بماند فلگ نیاید  

### CheckCult
- [ ] هدف مرده / زندان / خانه خالی طبق کلیدها  
- [ ] شکارچی هدف → مرگ بازدیدکننده قطعی  
- [ ] قاتل: شانس مرگ با/بدون ConvertCult؛ بدون تبدیل  
- [ ] گرگ پایه: خوردن مگر UserInHome  
- [ ] کلانتر: سه شاخه با باف ±۲۰  
- [ ] دلبر عاشق Cult → تبدیل؛ وگرنه عشق  
- [ ] فراماسون تبدیل + MasonConverted  
- [ ] جدول CultAttemp برای نمونه‌های قطعی/۰/درصدی (±۲۰ با ConvertCult)  
- [ ] lucifer vs Lucifer تصمیم‌گیری‌شده و تست‌شده  

### شکارچی
- [ ] قبل از فرقه در همان شب resolve می‌شود  
- [ ] کشت ferqe/Royce + مرگ مومیایی گارد  
- [ ] قاتل شکارچی را می‌کشد؛ فرانک ۱۰٪  
- [ ] شکست روی غیرفرقه  

### مرگ / رویس / فرانک
- [ ] Royce غیر afk → پیام تیم + شب بعد انتخاب دوم (+۳۰ث) و پاک Selected  
- [ ] Royce afk → بدون RoyceDead  
- [ ] ConvertCult فقط یک‌بار از مسیر مومیایی+رویس  
- [ ] مرگ shekar → هانتسمن شکارچی + NotSend همان شب  
- [ ] FrancNightOk → قتل شبانه با نقش در پیام گروه  

### رگرسیون
- [ ] برد فرقه / دوئل shekar+ferqe (اسپرینت ۴) نشکند  
- [ ] جفت کانفیگ ferqe/shekar/Royce و تزریق پیش‌بالانس  
- [ ] HunterKill / لیست بازیکن با RoyceDead درست بماند  

پس از QA → اسپرینت ۵ب (دسته بعدی نقش‌های ویژه).
