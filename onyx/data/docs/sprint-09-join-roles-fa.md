# اسپرینت ۹ — لابی جوین + توزیع نقش (اجرایی)

**وضعیت:** سند تحلیل عمیق PHP — پایه بازنویسی پایتون  
**هدف اسپرینت:** هم‌ارزی رفتار لابی، استخر نقش، تبدیل اجباری، بالانس وزن، تخصیص DM، و انتقال به شب  
**خروجی قابل قبول:** مسیر join→نقش→night برای مودهای کامل؛ مود Mafia و باگ‌های قطعی PHP صریحاً به‌عنوان شکسته/ناقص علامت خورده‌اند  
**مرجع سورس:** `join.php`, `GR.php` (`StartGameForGroup`, `PlayerJoinTheGame`, `ExtendToGame`), `CM.php` (`CM_StartGame`, مسیر `joinToGAME_`), `SE.php` (لیست نقش مودها، `_W`, `GetRoleTeam`)  
**مرجع کلان:** `docs/werewolf-python-rewrite-master-fa.md`  
**مرتبط:** اسپرینت ۳ (جفت‌نقش)، اسپرینت ۵* (تیم‌ها)، بدون اتکا به Notes_Mode

---

# ۱. جریان تایمر لابی (Lobby timer workflow)

## ۱.۱ شروع بازی (`CM_StartGame` → `GR::StartGameForGroup`)

1. فقط در چت گروهی؛ گروه بن‌شده رد می‌شود؛ کاربر بن‌شده قطع می‌شود.
2. اگر بازی فعالی نباشد (`CheckGPGameState == 0`): در صورت نبود `SetUpRoles`، `UnlockAllRole` همه کلیدهای نقش را `on` می‌کند.
3. مود Vampire فقط اگر `role_Vampire` و `role_Bloodthirsty` هر دو خاموش نباشند؛ وگرنه پیام `DisabledVampireMode` و توقف.
4. `StartGameForGroup`: پاک‌سازی `GamePl:*`، `game_state = join`، `Day_no = 1`، `Night_no = 0`، ثبت سند Mongo در `games`، `timer = now + join_timer` (پیش‌فرض ۹۰ اگر تنظیم نباشد).
5. بلافاصله بعد: `GamePl:gameModePlayer = $Mode`، ویدئو/کپشن شروع، دکمه deep-link جوین، پیام لیست بازیکن و ذخیره `Player_ListMessage_ID` (اختیاری pin).

## ۱.۲ ورود بازیکن (`joinToGAME_` در CM → `GR::PlayerJoinTheGame`)

1. چک «قبلاً در بازی / فلگ join_user»، نام تکراری، سقف `max_player` (پیش‌فرض تنظیم گروه ۳۵؛ اگر خالی باشد در مسیر جوین ۴۵).
2. اگر `leftTime <= 0` یا `game_state !== join` → ورود رد.
3. مود `coin`: کسر ۱۰ سکه قبل از جوین.  
   > **تصمیم محصول: مود سکه (`coin`) حذف — در پایتون پیاده نشود** (remediation §۱۷؛ MF-60). کسر ۱۰ فقط برای آن مود تاریخی است؛ کیف پول/شاپ جدا می‌مانند.
4. اگر `leftTime <= 10` در لحظه جوین/فرار/تست: `text = 30` و `ExtendToGame` (تمدید اضطراری).
5. درج Mongo در `games_players` (نقش/تیم null)، push به `join_user`، push نام به `GamePl:NewUserJoin`، به‌روزرسانی لیست با throttle پنج‌ثانیه‌ای (`time_update` / `UserJoin`).

## ۱.۳ تیک کرون لابی (`join::Handel` وقتی `game_state == join`)

هر تیک (در نبود `GamePl:StartNewGame`):

1. `NextGameMessage` (اعلان next-list سپس پاک‌سازی لیست).
2. `LeftTime = timer - now`.
3. `SendStarterMessage` یک‌بار (نام استارتر).
4. `UpdatePlayerList`:
   - اگر تعداد بازیکن ≥ `max_player` → `timer = now - 5` (شروع فوری در تیک بعدی).
   - ویرایش متن لیست؛ پیام‌های جوین دسته‌ای با برچسب زمان تقریبی (۵/۴/۳/۲ دقیقه، «دقایق»، ۳۰ث، ۱۰ث).
5. پنجره‌های یادآوری با کیبورد جوین (به‌خاطر تیک کرون چندثانیه تلورانس دارند):
   - حدود ۶۰ث: `LeftTime` در ۵۸…۶۲ → پیام «یک دقیقه»
   - حدود ۳۰ث: ۲۸…۳۲ → پیام ۳۰ ثانیه
   - حدود ۱۰ث: ۸…۱۱ → پیام ۱۰ ثانیه  
   در این caseها بعد از ارسال، return می‌شود (هنوز شروع نمی‌شود).
6. `default`: اگر `LeftTime <= 0`:
   - قفل `StartNewGame`، ثبت `EndJoinTimeGame`، پاک `time_update` و `UserJoin`
   - اگر تعداد < حداقل مود → بستن بازی (`GroupClosedThGame('join')`)، پیام کمبود بازیکن
   - وگرنه پاک پیام‌های موقت و `GameStarted()`

## ۱.۴ تمدید (`ExtendToGame`)

- مقدار درخواستی با `max_extend_timer` سقف می‌شود.
- اگر پس از تمدید باقیمانده < ۱۰ث → حداقل +۱۰ث.
- اگر باقیمانده کل از `join_timer` بیشتر شود → `timer = now + join_timer` (سقف طول لابی).
- جوین/فرار در ۱۰ث آخر خودکار +۳۰ث درخواست می‌کنند (سپس همان قواعد اعمال می‌شود).

---

# ۲. حداقل / حداکثر بازیکن بر مود

| قاعده | مقدار در PHP |
|--------|----------------|
| حداقل عمومی (همه مودها به‌جز Vampire) | **۵** (`join::Handel`) |
| حداقل Vampire | **۷** |
| حداکثر | `max_player` گروه؛ پیش‌فرض راه‌اندازی گروه **۳۵**؛ در UI گزینه‌های ۱۵/۲۰/۳۰/۳۵/۴۵ و ۵۰/۶۰ برای گروه‌های allow؛ در مسیر جوین اگر کلید خالی باشد fallback **۴۵** |
| پر شدن سقف | زودتر تمام‌کردن تایمر لابی (`timer = now - 5`) |

حداقل‌های **ورود نقش به استخر** (نه حداقل شروع بازی) جدا هستند — بخش ۳.

مودهایی که در توزیع نقش شاخه دارند: Normal, Mighty, Easy, Vampire, Romantic, WereWolf, Foolish, Bomber؛ شاخهٔ Mafia جدا و ناقص است (بخش ۷).

---

# ۳. خلاصه قوانین استخر `GetRoleRandom`

ورودی: `countPlayer`. خروجی: آرایهٔ نقش‌ها معمولاً **بزرگ‌تر از N**؛ بعداً `UserRole` با `array_slice(..., 0, N)` برش می‌زند. احتمال حضور ≈ سهم کپی‌ها در استخر پس از فیلتر کانفیگ، مشروط به قبول بالانس.

## ۳.۱ ثابت کمکی SG

`SG = 5` اگر N < ۲۰، وگرنه `6` (آستانهٔ ۱۰ در کد بی‌اثر است چون هر دو شاخهٔ <۱۰ و <۲۰ مقدار ۵ دارند).

## ۳.۲ مود Bomber (خروج زودهنگام)

> **تصمیم محصول: حذف نقش/مود/BombCount — در پایتون پیاده نشود.** (remediation §۱۶؛ MF-59)

- تعداد بمبر: `round(min(max(N/SG, 1), 5))` → بین ۱ تا ۵
- بقیه `role_rosta`
- بدون لیست SE مودهای دیگر

## ۳.۳ مود Foolish (خروج زودهنگام)

- حلقه گرگ: `round(min(max(N/5, 3), 1))` → **همیشه ۱** به‌خاطر باگ min/max (بخش ۸)
- اگر N ≥ ۱۱: اضافه `WolfJadogar`, `ngativ`, `PishRezerv`
- همیشه یک `pishgo`
- بقیه `ahmaq`

## ۳.۴ گرگ‌های پایه (غیر Vampire یا Vampire با N>۷)

از `SE::WolfRole` (توله، گرگینه، x، آلفا) پس از shuffle، تعداد `round(min(max(N/5, 1), 3))` یعنی ۱…۳، فقط اگر کلید نقش `on` باشد.

Vampire با N≤۷ این بلوک را رد می‌کند (گرگ پایه اضافه نمی‌شود مگر بعداً از لیست مود).

## ۳.۵ ومپایر تکراری

اگر (Vampire و Vampire on) یا (Mighty و N≥۲۵ و Vampire on): به‌ازای هر ۵ نفر یک `role_Vampire` اضافه.

## ۳.۶ انتخاب لیست SE بر مود

| مود | منبع لیست |
|-----|-----------|
| Normal / پیش‌فرض ناشناخته | `GetRole()` |
| Mighty | `mightyRole()` |
| Easy | `EasyRole()` |
| Vampire | `VampireRole()` |
| Romantic | `RomanticRole()` |
| WereWolf | `GetWereWolfRole()` |

لیست shuffle می‌شود؛ سپس برای هر نقش switch آستانه‌دار:

| نقش / گروه | شرط ورود تقریبی |
|------------|------------------|
| shekar / ferqe / Royce | on و N≥۱۱ |
| Mouse | on و N≥۱۱ و AllowGroup |
| BlackKnight / BrideTheDead | N≥۳۰ و AllowGroup |
| dian | N≥۲۵ و AllowGroup |
| Magento | N≥۲۰ و AllowGroup |
| kentvampire / isra / Chiang / Princess | N≥۲۵ (+Allow برای چندتایی) |
| Phoenix / hipo / javidShah / davina / Cow / qhost / Mummy / Archer | N≥۱۵ (+Allow یا on) |
| betaWolf / Lilis / Harly / Joker / iceWolf / Botanist / Watermelon / Bomber / dinamit / hellboy | N≥۲۰ (+Allow/on) |
| franc | N≥۱۱ و Allow |
| babr | N≥۷ و Allow |
| Huntsman / enchanter / forestQueen / Honey / WhiteWolf | on و N≥۲۰ |
| lucifer | on و N≥۱۵ |
| Vampire / Bloodthirsty از لیست | on و (Vampire یا Mighty≥۲۵) |
| Spy | on و N≥۱۱ |
| Firefighter / IceQueen | on و N≥۱۸ |
| Knight | on و N≥۱۳ |
| monafeq | فقط on |
| default | اگر `R::Get(role)==on` **یا** کلید نقش در Redis وجود نداشته باشد |

## ۳.۷ پرکننده‌های انتهایی

- غیر Mighty: دو `feramason` اگر on یا کلید غایب
- اگر `shekar` در لیست باشد: دو `ferqe` اضافه
- اگر N>۱۱ و ferqe on: `round(N/SG)` تا `ferqe` اضافه
- غیر Mighty و rosta on: `round(N/SG)` تا `rosta`

---

# ۴. تبدیل اجباری + شرایط بالانس `UserRole` (با شماره مرجع)

حلقهٔ do/while تا `$balanced`؛ حداکثر **۵۵۰** تلاش؛ شکست → بستن بازی + `ErrorStartGame_Balance`.

## ۴.۱ تبدیل‌های اجباری (به ترتیب کد، قبل از وزن)

1. **جادوگر/عسل/افسونگر/خائن بدون تیم گرگ در Slice:** با تقدم عملگر `and`/`||` شرط به شکل «(هر یک از آن نقش‌ها) و نبود `wolf` در enemy» است؛ سپس اولین نقش از لیست جستجو (`WolfJadogar`, `Khaen`, `Honey`, `enchanter`, `betaWolf`, `forestQueen`, `WhiteWolf`) با یک گرگ تصادفی از `WolfRole` عوض می‌شود. (تقدم عملگر و کلیدهای اضافه در بخش ۸.)
2. **Archer بدون Qatel** → Archer تبدیل به Qatel.
3. **forestQueen بدون WolfAlpha** → تبدیل به WolfAlpha (کامنت می‌گوید روستایی؛ کد آلفا می‌گذارد).
4. **Vampire بدون Bloodthirsty** → یک کلید «روستایی» از `GetRandomvgKey` → Bloodthirsty.
5. **Bloodthirsty بدون kalantar** → Vg → kalantar.
6. **Bloodthirsty بدون Vampire** → Vg → Vampire.
7. **ferqe بدون shekar** → Vg → shekar.
8. **Royce بدون shekar** → Vg → shekar.
9. **PishRezerv بدون pishgo** → PishRezerv → pishgo.

`nonVg` (نقش‌هایی که نباید برای تبدیل Vg انتخاب شوند) شامل دشمنان و چند نقش ویژه است؛ تکراری و با تایپوی `role_Lucifer` در کنار `role_lucifer` وجود دارد.

## ۴.۲ شرط اولیه تیم

پس از Slice مجدد: اگر `count(safe) > 0` و `count(enemy) > 0` → `$balanced = true`؛ وگرنه false می‌ماند مگر بعداً مود خاص.

`SliceRole` فقط بخشی از دشمنان را enemy می‌شمارد: گرگ‌های پایه، Firefighter/IceQueen (برچسب wolf)، قاتل/کماندار، Bomber، Vampire/Bloodthirsty، ferqe/Royce، dinamit. نقش‌هایی مثل iceWolf، WhiteWolf، Honey، enchanter، lucifer، Joker در **default → safe** می‌افتند؛ WolfJadogar/forestQueen/monafeq/… نه enemy نه safe.

## ۴.۳ وزن (`GetRoleWight` + `_W`)

مجموع وزن تیم‌ها: wolf، ferqe، rosta، qatel، Vampire، blod، kalan، FireFighter.  
`Monafeq = floor(Rosta+Wolf+Qatel+Ferqe+Vampire + FireFighter/N)` به‌خاطر تقدم `/` فقط روی FireFighter تقسیم می‌شود و **در هیچ شرط بالانس استفاده نمی‌شود**.  
حلقهٔ محاسبه وزن در کد **دو بار پشت‌سرهم** تکرار شده (بخش ۸).

مقادیر مهم `_W` (مرجع عددی): روستایی ۱؛ پیشگو ۷؛ کلانتر ۶؛ شکارچی ۷؛ فرقه/رویس ۱۰؛ قاتل ۱۵؛ کماندار ۱۴؛ آتش/ملکه یخ ۱۵؛ توله ۱۲؛ گرگینه ۱۰؛ Wolfx ۱۱؛ آلفا ۱۲؛ سفید ۱۲+تعدادگرگ‌پایه؛ Jadogar ۲؛ Honey ۹؛ enchanter ۸؛ forestQueen ۶؛ Bloodthirsty ۱۰؛ Vampire ۸؛ **lucifer: در بالانس مؤثر مستثنی/۰ (سیاست الف قفل‌شده؛ عدد ۱۷ PHP فقط متادیتای گمراه‌کننده قدیمی)**؛ iceWolf فعلاً در PHP default ۰ و سبد rosta — fix جدا در مرتفع‌سازی §۹.

## ۴.۴ شرایط بالانس عددی / جفتی (مرجع شرط)

برای مودهایی که **نه Foolish و نه Bomber** هستند:

### الف) اگر مود ≠ Vampire — هر یک از این‌ها بالانس را false می‌کند

| # | شرط |
|---|------|
| A1 | `Rosta <= Wolf` |
| A2 | `Ferqe >= Rosta` |
| A3 | `blod > 0 && Vampire == 0` |
| A4 | `blod > 0 && kalan == 0` |
| A5 | `Vampire > 0 && blod == 0` |
| A6 | `N < 11` و Royce در بازی و `role_ferqe == off` |
| A7 | Royce بدون ferqe وقتی ferqe on |
| A8 | `N >= 11` بدون shekar وقتی ferqe on |
| A9 | shekar بدون ferqe وقتی ferqe on |
| A10 | IceQueen بدون Firefighter یا برعکس |
| A11 | shekar بدون pishgo |
| A12 | PishRezerv بدون pishgo |
| A13 | davina بدون Qatel |
| A14 | forestQueen بدون WolfAlpha |
| A15 | BrideTheDead ↔ BlackKnight نامتقارن |
| A16 | dian بدون هر دو BlackKnight و BrideTheDead |

### ب) بلوک Vampire (همیشه در غیر Foolish/Bomber ارزیابی می‌شود)

| # | شرط false |
|---|-----------|
| V1–V3 | مود Vampire و (blod==0 یا Vampire==0 یا (Wolf>0 و N<8)) |
| V4–V6 | همان A3–A5 |
| V7 | BlackKnight بدون BrideTheDead |
| V8 | IceQueen بدون Firefighter |

### ج) جفت‌های سراسری (همه مودها پس از بلوک بالا)

| # | شرط |
|---|------|
| P1 | Joker بدون Harly یا برعکس |
| P2 | franc بدون ferqe |
| P3 | Magento بدون IceQueen |

### د) مود Foolish / Bomber

| مود | باید باشد |
|-----|-----------|
| Foolish | حداقل یک `WolfGorgine` و یک `pishgo` |
| Bomber | حداقل یک `Bomber` و یک `rosta` |

### ه) طول آرایه

`count(AnArray) !== countPlayer` → false.

پس از خروج موفق از حلقه: shuffle بازیکن و نقش، فلگ Dinamit، ساخت `RoleAssinged` + جمع لینک تیم‌ها، محاسبه BombCount در صورت بمبر، پخش ۴ قطعه بمب به ۴ بازیکن اول پس از shuffle، سپس `AssingeRoleToPlayer`.

---

# ۵. عوارض جانبی `AssingeRoleToPlayer`

برای هر بازیکن در لیست تخصیص‌یافته:

1. ساخت پیام DM نقش با جایگذاری تیم/جفت:
   - Joker↔Harly نام یکدیگر؛ Nazer وضعیت پیشگو؛ Bomber تعداد بمب + تیم؛ Bloodthirsty نام کلانتر؛ Bride↔BlackKnight؛ Qatel کماندار + اختیاری داوینا؛ kalantar متن خون‌آشام؛ فراماسون/فرقه لیست هم‌تیمی؛ Firefighter↔IceQueen؛ forestQueen/Alpha پیام زور و تیم گرگ؛ گرگ‌های پایه تیم آلفا.
2. اگر user_id == ADMIN_ID → `AmirKarimiInGame`.
3. دستاوردهای خاص چند chat_id هاردکد (Crouse / Sun / Org).
4. مود Romantic: جفت عشق دوطرفه با همسایهٔ ایندکس (+۱ یا −۱ اگر آخر لیست).
5. ارسال DM نقش؛ اگر موجودی جادو (خبرچین/اعلام نقش/محافظ/روح) >۰ → پنل مجیک تا پایان بازی.
6. Cow / Watermelon: فلگ NoPersist و دستاورد هندوانه.
7. Redis: `GamePl:user:{id}:team` و `:role`.
8. Mongo `games_players`: set `user_role` و `team`.

قبل از فراخوانی، در `UserRole` فلگ‌های بازی مثل SearUser، گلوله تفنگدار/کلانتر، لیست Cult/Mason/Wolf/…، HuntsmanT=2، BlackVoteNo=2، BookIn برای حداکثر ۸ نفر غیر جوکر/هارلی (تایپو `role_Halrly` باعث می‌شود Harly هم Book بگیرد)، BombCount/BombPlanted ست می‌شوند.

---

# ۶. `GameStarted` → شب

1. `ChangeStartGameTime` → `GamePl:StartedTime`.
2. `GamePl:Kill = true`.
3. پیام گروهی `GameStart`.
4. اگر مود **Mafia** → **return true فوری** بدون نقش و بدون night (بخش ۷).
5. در غیر این صورت `UserRole()`؛ اگر true:
   - `ChangeGameStatus('night')` → `game_state=night`، `timer = now + night_timer` (پیش‌فرض ۹۰؛ اگر خواب‌گذار فعال → timer=۰)، آپدیت Mongo `game_status`.
   - متن وضعیت از `GetGameStatusLang` → SaveMessage → `SendGroupMessage(true)`.
6. اگر UserRole false → false (بازی قبلاً در UserRole بسته شده).

از این نقطه کرون فاز `NG::Handel` را برای شب اجرا می‌کند (اسپرینت ۱).

---

# ۷. ناقص بودن مسیر مود Mafia

وضعیت واقعی PHP: **مسیر شروع می‌شود ولی نقش‌دهی و ورود به شب پیاده نشده / شکسته است.**

1. `GameStarted`: اگر `gameModePlayer == Mafia` فقط `return true` — نه `MafiaUserRole`، نه `UserRole`، نه `ChangeGameStatus('night')`. بازیکنان بدون نقش در حالت join قفل‌شده (`StartNewGame`) می‌مانند یا فاز نامشخص.
2. `MafiaUserRole` هرگز از `GameStarted` صدا زده نمی‌شود.
3. حتی اگر صدا زده شود:
   - حلقه `do { … } while ($balance);` وقتی تعداد نقش‌ها با N جور است `$balance=true` می‌ماند → **ادامه حلقه** تا سقف ۵۵۰ (منطق معکوس؛ باید `!$balance` باشد).
   - پس از حلقه هیچ تخصیص نقش، Assinge، یا return true مفید ندارد.
4. `GetRoleMafia` به `SE::MafiaRole()` و `SE::RoleMafiaMode()` وابسته است — **این دو متد در کل درخت سورس تعریف نشده‌اند** → در صورت فراخوانی Fatal error.
5. همان باگ `min(max(...,3),1)` فقط یک نقش مافیای تخصصی می‌گذارد؛ حلقه شهروند با ایندکس `$i` باقی‌مانده از حلقه قبل ایندکس اشتباه می‌زند.

**برای بازنویسی پایتون:** مود Mafia یا خارج از scope هم‌ارزی اعلام شود، یا از صفر با قرارداد جدید طراحی شود — کپی کور PHP ممکن نیست.

---

# ۸. باگ‌های PHP (لیست اجرایی)

## ۸.۱ `min(max(x, 3), 1)` — همیشه ۱

در `GetRoleMafia` و حلقه گرگ Foolish: `max(…,3)` حداقل ۳ است؛ `min(۳,۱)=۱`. نیت احتمالی `min(max(x,1),3)` بوده. اثر: همیشه یک اسلات تخصصی مافیا / همیشه یک گرگینه در Foolish از آن حلقه.

## ۸.۲ `GetRandomvgKey` — تصادفی نیست، همیشه ایندکس آخر

پارامتر `$key` در foreach بازنویسی می‌شود؛ شرط فقط ایندکس ۰ را «بررسی» می‌کند ولی نتیجه را نگه نمی‌دارد؛ مقدار برگشتی پس از حلقه آخرین کلید آرایه است. تبدیل‌های Vg (Bloodthirsty/kalantar/Vampire/shekar) عملاً **آخرین اسلات نقش** را عوض می‌کنند، نه یک روستایی تصادفی امن.

## ۸.۳ `while ($balance)` در `MafiaUserRole`

منطق معکوس: موفقیت باعث تکرار تا ۵۵۰ و سپس بستن بازی با خطای بالانس می‌شود.

## ۸.۴ تقدم عملگر در شرط جادوگر/خائن

ترکیب `||` با `and`: شرط گرگ‌نبودن روی کل ORها اعمال می‌شود (نه فقط روی Khaen). رفتار ممکن است با نیت کامنت یکی باشد ولی با `&&` یکنواخت نیست و با آرایه جستجوی گسترده‌تر (`betaWolf`/`forestQueen`/`WhiteWolf`) ناهماهنگ است.

## ۸.۵ حلقه وزن تکراری

بلوک `GetRoleWight` + استخراج متغیرها + فرمول Monafer **دو بار پشت‌سرهم** بدون تغییر — هزینه CPU و نشانهٔ copy-paste؛ Monafer بلااستفاده.

## ۸.۶ iceWolf وزن ۰ در سبد روستا

`GetRoleWight` iceWolf را در case گرگ ندارد → default → به `Rosta` اضافه می‌شود با `_W` default = ۰. تیم Mongo او `wolf` است ولی بالانس وزن او را روستایی می‌بیند. در `SliceRole` هم safe محسوب می‌شود.

## ۸.۷ lucifer — سیاست بالانس قفل‌شده (الف)

`SE::_W('role_lucifer')` در PHP مقدار ۱۷ برمی‌گرداند ولی case در `GetRoleWight` خالی است.  
**تصمیم محصول (`remediation-accepted-fixes-fa.md` §۱۲):** همین بی‌اثر بودن بالانس حفظ شود؛ وزن بالانس مؤثر = مستثنی/۰؛ عدد ۱۷ از مسیر accept/reject دست حذف یا جدا برچسب شود. Slice او را safe می‌شمارد؛ قدرت نقش در اکشن شب ۰ و dodge است نه در وزن شروع.

## ۸.۸ Bloodthirsty در وزن: استفاده از `$Vampire` قبل از به‌روزرسانی

`$Blod = ($Vampire + SE::_W(...))` در حالی که `$Vampire` هنوز مقدار قبلی حلقه است — وابستگی ترتیبی اشتباه نسبت به case Vampire.

## ۸.۹ فرمول BombCount

> **تصمیم محصول: حذف — در پایتون پیاده نشود** (دیگر «mirror یا fix فرمول» نیست؛ MF-16 remove accepted؛ remediation §۱۶).

برای N>۵: `max(min(N/BomberCount, 1), 10)` همیشه **۱۰** → `BombMaxCount = N - 10`. برای N≤۵: `N - 2`. به‌نظر معکوس/خراب نسبت به نیت «سقف کاشت».

## ۸.۱۰ تایپو `role_Halrly`

در حلقه BookIn، Harly از استثنا خارج نمی‌شود و ممکن است Book بگیرد.

## ۸.۱۱ `GetKeyRoleByN` اگر نقش در ایندکس ۰ باشد

وقتی `array_search` صفر برمی‌گرداند، شرط `$key == 0` برقرار می‌ماند و جستجو ادامه می‌یابد؛ اگر هیچ نقشی یافت نشود کلید ۰ برمی‌گردد و نقش ایندکس ۰ اشتباه عوض می‌شود.

## ۸.۱۲ `GetRoleMafia` حلقه شهروند

`foreach ($MafiaRole as …)` با `CitizenRole[$i]` و `$i` بیرونی — ایندکس نامعتبر / Notice.

## ۸.۱۳ متدهای غایب SE برای مافیا

`MafiaRole` / `RoleMafiaMode` تعریف نشده.

## ۸.۱۴ GameStarted مافیا بدون شب

بخش ۷.

## ۸.۱۵ آپدیت Mongo در `ChangeGameStatus`

`['$set' => ['game_status' => $to, 'timer']]` — عنصر `'timer'` بدون مقدار؛ در MongoDB ممکن است رفتار نامعتبر/هشدار بدهد (خارج از join صرف، ولی در مسیر night اثر دارد).

## ۸.۱۶ ناهماهنگی کامنت / کد forestQueen

کامنت: تبدیل به روستایی؛ کد: `role_WolfAlpha`.

## ۸.۱۷ `role_Lucifer` در nonVg

کلید با L بزرگ در لیست nonVg با شناسه واقعی `role_lucifer` یکی نیست — فیلتر Vg ناقص برای آن املا.

---

# ۹. QA (چک‌لیست پذیرش هم‌ارزی / رگرسیون)

## لابی

- [ ] شروع مود Normal: `game_state=join`، timer ≈ join_timer، لیست پین/آیدی پیام ذخیره شود
- [ ] جوین تا max_player؛ جوین بعدی رد با MaxPlayer
- [ ] رسیدن به max_player تایمر را زود تمام کند و بازی شروع شود (اگر ≥ حداقل)
- [ ] N < 5 (یا <7 Vampire) → بستن + پیام کمبود؛ بدون night
- [ ] یادآوری تقریبی ۶۰/۳۰/۱۰ ثانیه با کیبورد
- [ ] جوین در ۱۰ث آخر ≥۱۰ث به تایمر اضافه کند (با سقف‌های Extend)
- [ ] فرار فقط در join؛ لیست و join_user به‌روز شود

## استخر و مود

- [ ] Bomber: فقط Bomber+rosta؛ تعداد بمبر در بازه ۱…۵ تابع N/SG
- [ ] Foolish: رفتار فعلی PHP (۱ گرگینه از حلقهٔ باگ‌دار) مستند شود؛ در پایتون تصمیم: باگ‌سازگار یا اصلاح‌شده
- [ ] Vampire N=۷ حداقل شروع؛ گرگ پایه از بلوک اول نیاید اگر N≤۷
- [ ] Mighty N≥۲۵ بتواند Vampire/Bloodthirsty از قوانین مربوطه بگیرد
- [ ] آستانه‌های AllowGroup نقش‌های قفل‌شده را حذف کنند

## تبدیل و بالانس

- [ ] Archer تنها → Qatel
- [ ] ferqe/Royce بدون shekar → shekar اجباری (با آگاهی از باگ GetRandomvgKey اگر باگ‌سازگار)
- [ ] جفت Joker/Harly، IceQueen/Firefighter، Bride/BlackKnight رد بالانس اگر ناقص
- [ ] Rosta <= Wolf رد
- [ ] بیش از ۵۵۰ شکست بالانس → بستن + ErrorStartGame_Balance
- [ ] پس از موفقیت همه N بازیکن در Mongo نقش و تیم غیرnull

## Assinge و شب

- [ ] هر بازیکن DM نقش درست با نام جفت/تیم
- [ ] Romantic: هر بازیکن یک love دوطرفه
- [ ] غیر Mafia: game_state=night و timer شب
- [ ] پیام وضعیت شب در گروه ارسال شود
- [ ] Mafia: رفتار فعلی PHP (بدون نقش/شب) یا قرارداد جدید صریح در تست مشخص باشد

## وزن / نقش‌های حساس

- [ ] lucifer طبق سیاست الف: افزودن به دست سطل‌های وزن را عوض نکند؛ ۱۷ در بالانس استفاده نشود  
- [ ] iceWolf پس از fix در سطل wolf با وزن غیرصفر (سند مرتفع‌سازی §۹)
- [ ] ~~BombCount برای چند بمبر با N مشخص…~~ — **حذف محصولی** (MF-16/58/59)؛ در پایتون تست فرمول نشود
- [ ] مود `Bomber` و مود `coin` در استخر/استارت پایتون نباشند (remove accepted)

---

# ۱۰. بخش صریح: PHP ناقص / شکسته

موارد زیر را **نباید** به‌عنوان رفتار سالم محصول برای کپی کور فرض کرد:

1. **مود Mafia به‌طور کامل شکسته/ناتمام است:** `GameStarted` نقش نمی‌دهد و به شب نمی‌رود؛ `MafiaUserRole` صدا زده نمی‌شود؛ در صورت صدا زدن حلقه معکوس + متدهای غایب SE + استخر خراب.
2. **`GetRandomvgKey` تصادفی/روستایی‌انتخاب‌کن نیست** — تبدیل‌های وابسته به Vg در عمل آخرین اسلات را هدف می‌گیرند.
3. **`min(max(x,3),1)`** تعداد گرگ Foolish و مافیای تخصصی را خراب می‌کند.
4. **وزن lucifer در بالانس اعمال نمی‌شود**؛ **iceWolf به سطل روستا با وزن ۰** می‌رود و در Slice دشمن نیست.
5. **فرمول BombCount** برای N>۵ عملاً همیشه N−۱۰ است. → **حذف محصولی کامل BombCount+نقش+مود** (دیگر mirror/fix فرمول نیست؛ §۱۶ remediation).
6. **`SE::MafiaRole` / `RoleMafiaMode` وجود ندارند.**
7. **Monafer محاسبه‌شده در بالانس استفاده نمی‌شود**؛ حلقه وزن دوبل است.
8. **تایپو Halrly** و **املای Lucifer در nonVg** فیلترها را سوراخ می‌کنند.
9. **آپدیت Mongo `timer` در ChangeGameStatus** از نظر ساختار `$set` مشکوک/شکسته است.

**توصیه بازنویسی:** برای مودهای Normal/Mighty/Easy/Vampire/Romantic/WereWolf/Foolish هم‌ارزی رفتاری با جدول بالانس و استخر؛ **مودهای `Bomber` و `coin` در پایتون پیاده نشوند** (حذف محصولی). برای Mafia یا حذف از MVP یا طراحی تمیز جدا. باگ‌های ۸.۱–۸.۳ و ۸.۶–۸.۷ را در سند تصمیم پایتون صریحاً «باگ‌سازگار» یا «اصلاح‌شده» علامت بزنید تا QA دوگانه نشود.

---

# ۱۱. محدوده اسپرینت (In / Out)

## داخل

- کل مسیر لابی تا اولین شب برای مودهای غیر Mafia
- استخر `GetRoleRandom` + لیست‌های SE
- تبدیل اجباری و جدول بالانس `UserRole`
- عوارض `AssingeRoleToPlayer` (بدون منطق شب نقش‌ها)
- مستندسازی صریح شکست Mafia و باگ‌های قطعی

## خارج

- resolve شب / روز / رأی (اسپرینت ۱+)
- Notes_Mode (ممنوع برای منطق)
- پیاده‌سازی کامل مود Mafia مگر تصمیم محصول جدا
- بانک پیام کامل (اسپرینت ۶) جز کلیدهای لازم لابی/نقش

---

**پایان سند اسپرینت ۹.**
