# مستندسازی منطق ربات ورولف (Onyx Werewolf)

**منبع تحلیل:** سورس PHP در `E:\Project\onyx\html`  
**هدف:** آماده‌سازی بازنویسی به پایتون  
**محدودیت‌ها:** بدون قطعه کد؛ بدون استفاده از `bot\Strong\Game_Mode`

---

# ۱. بخش استدلال و تحلیل (Reasoning)

## ۱.۱ نقشهٔ ذهنی معماری

پیش از نتیجه‌گیری، ساختار واقعی کد با نام فایل‌ها هم‌خوان نیست و باید از روی جریان اجرا بازسازی شود:

1. **ورود آپدیت تلگرام** از مسیر webhook (`Hook` / `CronBot`) و دستورات کاربر (`CM`) انجام می‌شود.
2. **موتور فاز بازی** از مسیر کرون (`Cron` → `cron` → `Handler`) تیک می‌خورد؛ نه از webhook.
3. **وضعیت لحظه‌ای** در Redis دیتابیس ۵ با پیشوند `chat_id` نگه داشته می‌شود (`R` در کرون، `RC` در webhook — دو کلاس تقریباً هم‌شکل).
4. **وضعیت ساختاری بازیکن/بازی** در MongoDB دیتابیس `wop` است (`games`, `games_players`, `join_user`, …).
5. **متن‌های جریان بازی** تقریباً همگی از لایهٔ `Lang` با کلیدهای ترجمه خوانده می‌شوند؛ منبع فایل‌های ini در پوشهٔ `Game_Mode` است که طبق دستور کاربر باز نشده‌اند. بنابراین در بخش پیام‌ها، کلیدها و متن‌های هاردکد مستند شده‌اند، نه متن فارسی داخل ini.

## ۱.۲ چرا منطق نقش در `R.php` نیست؟

نام‌گذاری گمراه‌کننده است:

- `R.php` / `RC.php` لایهٔ Redis و چند کمک‌تابع گیف هستند.
- `GR::GetRoleRandom` و `HL::GetRoleRandom` بازیکن تصادفی برمی‌گردانند، نه نقش.
- توزیع نقش واقعی در `join.php` است: `GetRoleRandom` (ساخت استخر) + `UserRole` (برش، تبدیل اجباری، بالانس) + `AssingeRoleToPlayer` (اختصاص و پیام PV).
- وزن بالانس در `SE::_W` و شانس‌های میدانی در `SE::_s` تعریف شده‌اند.
- تیم نقش در `SE::GetRoleTeam` و لیست نقش هر مود در توابع `GetRole` / `mightyRole` / `EasyRole` / `VampireRole` / `RomanticRole` / `GetWereWolfRole` است.

## ۱.۳ دو لایهٔ «احتمال» در نقش‌دهی

تحلیل نشان می‌دهد سیستم **قرعهٔ وزنی مستقیم روی نقش‌ها ندارد**. به‌جای آن:

**لایهٔ استخر:** نقش‌ها با تکرار و آستانهٔ بازیکن وارد یک لیست بزرگ می‌شوند؛ چند بار shuffle می‌شوند؛ سپس به تعداد بازیکن برش می‌خورند. شانس تقریبی حضور یک نقش ≈ تعداد کپی در استخر ÷ اندازهٔ استخر (پس از فیلتر on/آستانه/VIP).

**لایهٔ بالانس:** دست نهایی با وزن‌های `SE::_W` جمع زده می‌شود؛ اگر شرط‌های تعادل برقرار نباشد، کل دست دور ریخته و تا سقف ۵۵۰ بار دوباره ساخته می‌شود. وزن‌ها روی «قبول/رد دست» اثر می‌گذارند، نه روی احتمال قرعهٔ تک‌نقش.

## ۱.۴ چرا وزن روستا باید از گرگ بیشتر باشد؟

در جمع‌بندی `GetRoleWight`، گرگ‌ها وزن‌های دورقمی دارند (۱۰–۱۲+)، در حالی که روستایی پایه وزن ۱ دارد. نقش‌های قدرتمند روستا (پیشگو ۷، فرشته ۷، کلانتر ۶، …) این شکاف را جبران می‌کنند. شرط `Rosta > Wolf` تضمین می‌کند دست فقط وقتی قبول شود که قدرت تجمعی روستا از گرگ بیشتر باشد؛ در غیر این صورت بازی از اول نامتعادل است. شرط `Ferqe < Rosta` جلوی تسلط عددی/وزنی فرقه در شروع را می‌گیرد.

## ۱.۵ جریان فاز چگونه جلو می‌رود؟

یک timestamp به نام `timer` در Redis برابر `now + مدت فاز` ست می‌شود. هر تیک کرون:

1. قفل همزمانی `InComplater` را چک می‌کند.
2. اگر بازی تمام شده (`GameIsEnd`) پردازش نمی‌کند.
3. برای night/day/vote: `CheckEndGame` → `checkTime` (پایان زودهنگام) → `CheckTimer` (اگر زمان تمام شده، حل فاز و انتقال).
4. سپس هندلر فاز (`NG` / `DY` / `VT` / `join`) کیبورد/پیام می‌فرستد.

نکتهٔ معماری مهم: **انتخاب‌های بازیکن در طول فاز فقط ذخیره می‌شوند**؛ اثر واقعی تقریباً همیشه در پایان تایمر با `CheckNight` / `CheckDay` / `CheckVote` اعمال می‌شود (به‌جز توانایی‌های فوری مثل صلح، خواب‌گذار، حاکم، دردسرساز، شلیک مرگ کلانتر).

## ۱.۶ وابستگی متقابل نقش‌ها در تنظیمات گروه

`GR::ChangeConfig` جفت‌نقش‌ها را همگام می‌کند تا تنظیمات ادمین به حالت‌های غیرقابل‌بازی نرسد: Vampire↔Bloodthirsty، فرقه↔شکار↔رویس، IceQueen↔Firefighter، قاتل↔کماندار، و خاموش شدن نقش‌های وابسته به گرگ وقتی هیچ گرگ پایه‌ای روشن نباشد. این منطق «پیش‌گیری در تنظیمات» مکمل «تبدیل اجباری در UserRole» است.

## ۱.۷ پیام‌ها و محدودیت Game_Mode

تقریباً ۱۰۸۶ کلید یکتای Lang در منطق فراخوانی می‌شوند. متن کامل فارسی/انگلیسی داخل فایل‌های `main_*` / `general_*` / `nightclub_*` در `Game_Mode` است. طبق قانون مطلق کاربر این فایل‌ها خوانده نشدند. برای بازنویسی پایتون باید همان کلیدها را با همان placeholderهای `{0}`, `{1}`, … پیاده‌سازی کرد و متن‌ها را بعداً از ini وارد کرد.

## ۱.۸ جمع‌بندی استدلال (قبل از مستندات)

- موتور بازی = کرون + Handler + چهار فاز join/night/day/vote.
- نقش‌دهی = استخر + shuffle + slice + تبدیل اجباری + فیلتر وزن بالانس.
- وضعیت = Redis لحظه‌ای + Mongo ساختاری.
- پیام جریان بازی = کلید Lang؛ پیام‌های ادمین/فروشگاه عمدتاً هاردکد فارسی.

---

# ۲. بخش مستندات فنی (Technical Documentation)

## ۲.۱ کلاس‌ها و هدف منطقی توابع اصلی

### لایهٔ اجرا و زمان‌بندی

| واحد | هدف منطقی |
|------|-----------|
| `Cron` / `cron` | بارگذاری Redis/Mongo برای هر گروه فعال؛ مقداردهی R، HL، Handler، join، NG، DY، VT |
| `Handler::Handel` | قفل همزمانی؛ دیسپچ فاز جاری؛ فراخوانی چک تایمر و پایان بازی |
| `CronJob` | آمار گروه و شرط‌بندی؛ **نه** موتور فاز شب/روز |
| `Hook` | مسیر webhook آپدیت تلگرام؛ دستورات و جوین دستی |
| `CM` | تمام دستورات و کال‌بک‌های کاربر (شروع، جوین، رأی، انتخاب شب/روز، تنظیمات، فروشگاه، بن، …) |

### لایهٔ وضعیت و کمک‌تابع

| واحد | هدف منطقی |
|------|-----------|
| `R` / `RC` | خواندن/نوشتن Redis با اسکوپ `chat_id`؛ لیست‌ها؛ TTL؛ دسترسی سراسری بدون پیشوند |
| `HL` | تغییر فاز، تایمر، مرگ، تبدیل نقش، برد/باخت، پیام گروهی صف‌شده، پایان بازی |
| `GR` | کمک‌توابع گروه/بازیکن در مسیر webhook؛ آنلاک نقش‌ها؛ کیبورد نقش؛ بن؛ آمار |
| `SE` | لیست نقش مودها؛ نگاشت تیم؛ وزن بالانس `_W`؛ شانس میدانی `_s`؛ گیف‌ها |
| `Lang` | بارگذاری ترجمه از ini؛ جایگزینی placeholder |
| `KB` | عملاً برچسب دکمه ندارد؛ کمک تنظیم گروه |

### فازها

| واحد | هدف |
|------|------|
| `join` | تایمر لابی؛ نقش‌دهی؛ اعلام شروع؛ لیست بازیکن |
| `NG` | ارسال اکشن شب؛ حل شب (`CheckNight`) به ترتیب ثابت |
| `DY` | اکشن روز؛ حل روز؛ پیام عاشق‌ها |
| `VT` | کیبورد رأی؛ شمارش؛ اعدام؛ رأی دوم دردسرساز |

---

## ۲.۲ جریان کاری (Workflow) کامل بازی

### الف) لابی (join)

1. کاربر/ادمین `CM_StartGame` را در گروه می‌زند.
2. کلیدهای `GamePl:*` پاک می‌شوند؛ `game_state = join`؛ تایمر = now + `join_timer` (پیش‌فرض ۹۰ث).
3. سند Mongo در `games` با وضعیت join ساخته می‌شود؛ مود بازی در `GamePl:gameModePlayer` ذخیره می‌شود.
4. در اولین بازی گروه، `UnlockAllRole` تقریباً همه نقش‌ها را `on` می‌کند.
5. بازیکنان با `CM_Join` وارد می‌شوند → سند `games_players` با `user_state=1` و نقش null؛ لیست Redis به‌روز می‌شود.
6. کرون هشدار ۶۰/۳۰/۱۰ ثانیه می‌دهد؛ در ۱۰ ثانیهٔ آخر ممکن است ۳۰ث تمدید خودکار شود.
7. با اتمام تایمر: اگر بازیکن < ۵ (یا برای Vampire < ۷) → بستن بازی؛ وگرنه `GameStarted`.

### ب) نقش‌دهی و ورود به شب

1. `UserRole` تا ۵۵۰ تلاش دست متعادل می‌سازد.
2. بازیکن و نقش ۳ بار shuffle و جفت می‌شوند.
3. پیام نقش به PV؛ تیم/نقش در Redis و Mongo ذخیره می‌شود.
4. در مود Romantic جفت عشق ساخته می‌شود.
5. `game_state = night`؛ `RoleAssinged = true`.

### ج) چرخهٔ اصلی

```
night → (CheckNight) → day → (CheckDay) → vote → (CheckVote) → night → …
```

- ورود از vote به night: `Night_no` افزایش می‌یابد.
- ورود از day به vote: `Day_no` افزایش می‌یابد.
- بین رأی و شب بعد: `BittanCheck` تبدیل‌های گازگرفتگی را اعمال می‌کند.

### د) وقفه‌های داخل چرخه

| وقفه | اثر |
|------|-----|
| مرگ کلانتر | فاز متوقف؛ شلیک مرگ (`HunterKill` / `KalanShot` / `Skip`) |
| مرگ توله گرگ | بازگشایی انتخاب گرگ‌ها + حدود ۴۵ث اضافه |
| مرگ رویس | انتخاب ویژه رویس |
| صلح‌طلب | لغو رأی آن دور (`GroupInSolh`) |
| حاکم | فقط حاکم رأی می‌دهد؛ تایمر رأی کوتاه |
| خواب‌گذار | شب بعد تایمر شب = ۰ (شب رد می‌شود) |
| داوینا | روز بعد ۳۰ث + قفل چت |
| دردسرساز | یک دور رأی اضافه بدون رفتن به شب |
| یخ‌زده | بدون اکشن/رأی آن دور |

### ه) پایان

`CheckEndGame` برنده را برمی‌گرداند → `GamedEnd`: پیام برد، لیست، آنمیوت، پاک‌سازی `games` / `games_players` / `join_user` و کلیدهای `GamePl:*`؛ تنظیمات پایدار گروه باقی می‌مانند.

---

## ۲.۳ توابع کلیدی به تفکیک فاز

### شروع / جوین

| تابع | وظیفه |
|------|--------|
| `CM_StartGame` | شروع لابی، ست مود، پیام جوین |
| `CM_Join` / `join::Handel` | مدیریت تایمر و هشدارها |
| `join::GameStarted` | نقش‌دهی و ورود به night |
| `join::UserRole` | الگوریتم توزیع و بالانس |
| `join::GetRoleRandom` | ساخت استخر نقش |
| `join::AssingeRoleToPlayer` | اختصاص + پیام PV تیمی |
| `CM_ForceStart` / `CM_Extend` / `CM_Flee` | شروع اجباری / تمدید / فرار |
| `CM_Nextgame` / `cancel_nextgame` | صف بازی بعدی |

### شب

| تابع | وظیفه |
|------|--------|
| `NG::Handel` | ارسال اکشن شب + اعلام شکارچی + چک لوسیفر |
| `NG::SendNightRole` | کیبورد انتخاب شب |
| `NG::GetMessageNight` | متن پرسش شب هر نقش |
| `NG::CheckNight` | حل‌کنندهٔ اصلی شب (ترتیب ثابت) |
| `CM::NightSelectedCheck` | ثبت انتخاب کال‌بک |
| `CM::NightSelectDodge` | انتخاب به‌جای بازیکن دزدیده‌شده توسط لوسیفر |
| `CM::FighterFight` | تأیید شعله‌ور کردن لیست آتش‌نشان |
| `CM::Skip` / `CM::KalanShot` | رد/شلیک کلانتر هنگام مرگ |

### روز

| تابع | وظیفه |
|------|--------|
| `DY::Handel` | پیام عاشق + اکشن روز |
| `DY::SendDayRole` | کیبورد نقش‌های روز |
| `DY::CheckDay` | حل اکشن‌های روز |
| `DY::CheckTofangdar` / `CheckBlackKnight` / `GetDinamit` / `CheckKaragah` / `CheckSpy` / `CheckPrincess` / `CheckDian` / `CheckKent` | حل نقش‌های خاص روز |
| `CM::DaySelectedCheck` / `DaySelectedDodge` | ثبت/داج روز |

### رأی

| تابع | وظیفه |
|------|--------|
| `VT::Handel` / `SendVote` | ارسال و آپدیت کیبورد رأی |
| `VT::CheckVote` / `CollectVote` | شمارش و اعدام |
| `VT::TroubleVote` | رأی دوم دردسرساز |
| `CM::VoteUser` / `DodgeVote` | ثبت رأی عادی / داج لوسیفر |

### پایان و مرگ

| تابع | وظیفه |
|------|--------|
| `HL::CheckEndGame` | قوانین برد چندتیمی |
| `HL::GamedEnd` / `GameEndMessage` / `SendListEndGame` | اعلام و بستن |
| `HL::UserDead` | زنجیره مرگ، عشق، تبدیل، میوت |
| `HL::BittanCheck` | اعمال تبدیل گازگرفتگان |
| `HL::ConvertPlayer` / `ConvertHamzad` / … | تبدیل نقش‌ها |

---

## ۲.۴ ترتیب حل شب (`NG::CheckNight`)

1. مرگ دسته‌جمعی ملکه جنگل (در صورت فلگ)
2. جوکر → هارلی → شوالیه
3. تیم گرگ → بتای گرگ
4. وقفه احتمالی مرگ توله
5. ببر → گرگ برفی
6. قاتل (با وقفه کلانتر)
7. شیمیدان → بمبر → آتش‌نشان → مگنتو → کماندار → چیانگ
8. ومپایر → شکارچی فرقه → فرقه → لوسیفر
9. عروس مرده → فرشته → ملکه یخی → لیلیس → عجوزه → کنت → فرانک → افسونگر
10. ناتاشا/فاحشه → گاو → هانتسمن → روح → موش → گرگ سفید → فال‌بین‌ها → ققنوس → دزد → نگاتیو → جادوگر → دینامیت → هندوانه → خنیاگر
11. انتخاب رویس در صورت مرگ
12. پاکسازی فلگ‌های محافظت/درخانه

### الگوی حمله و حفاظت (تقریبی)

- تله هانتسمن (~۵۰٪ کشت مهاجم)
- هیال جادویی / هیال ققنوس → بلاک
- زندان شاهزاده → بلاک حمله به زندانی
- گاردها: فرانک → مامی → گرگ سفید → فرشته (معمولاً روی گرگ کار نمی‌کند) → لیلیس (شانس کشت مهاجم)
- فرشته روی گرگ/قاتل بخوابد → خودش می‌میرد
- ناتاشا در خانه قربانی → مرگ همزمان
- آلفا / ملکه جنگل / افسونگر: شانس تبدیل به‌جای کشتن
- خنیاگر: منحرف کردن بسیاری از انتخاب‌ها به هدف تصادفی

---

## ۲.۵ حل روز و رأی

### روز (`CheckDay`) — ترتیب

تفنگ‌دار → (وقفه کلانتر) → شوالیه سیاه → دینامیت‌یاب → کارآگاه → جاسوس → شاهزاده → دیان → کنت.

### رأی

1. اگر صلح فعال → بدون اعدام.
2. بیشترین رأی یکتا لازم است؛ تساوی/صفر = بدون کشت.
3. استثناها: شاهزاده (اولین اعدام زنده)، شوالیه سیاه (مصونیت با شمارنده)، منافق (اعدام = برد فوری)، کلانتر (مرگ + شلیک نهایی).
4. پسر گیج: ۵۰٪ منحرف کردن رأی.
5. کدخدا فاش‌شده: رأی دوگانه.
6. یخ‌زده‌ها رأی نمی‌دهند.

---

## ۲.۶ شرایط برد (`CheckEndGame`) — خلاصه

- صف تبدیل باز → بازی ادامه دارد.
- دینامیت با ۳ بمب → برد دینامیت.
- صفر زنده → `nothing`.
- مود بمبر: کاشت همه بمب‌ها یا برتری عددی.
- ۱ نفر زنده: بعضی نقش‌های خاص → `nothing`؛ وگرنه تیم همان نفر.
- ۲ نفر: عاشق → `lover`؛ سیاه → `black`؛ آتش‌نشان/یخ؛ دوئل کلانتر؛ قاتل؛ گرگ؛ فرقه؛ …
- جوکر/هارلی: ۳ کتاب یا بازیکن ≤ ۳ → `joker`.
- برتری عددی گرگ / ومپایر / فقط روستا / فقط یک تیم باقی‌مانده.
- رویدادهای خاص: اعدام منافق، علامت دیان (روز ۴)، و غیره.

کدهای برندهٔ رایج: `rosta`, `wolf`, `ferqeTeem`, `qatel`, `lover`, `monafeq`, `nothing`, `joker`, `Bomber`, `Firefighter`, `vampire`, `black`, `dinamit`.

---

## ۲.۷ مکانیسم دقیق محاسبه وزن و توزیع نقش

### ۲.۷.۱ وزن بالانس `SE::_W`

| نقش | وزن |
|-----|-----|
| role_rosta | 1 |
| role_Watermelon | 0 |
| role_feramason | 1 × تعداد فراماسون در دست |
| role_lucifer | 17 |
| role_Chemist | 10 |
| role_Bloodthirsty | 10 |
| role_Vampire | 8 |
| role_pishgo | 7 |
| role_Knight | 8 |
| role_Ruler | 4 |
| role_Botanist | 6 |
| role_karagah | 6 |
| role_elahe | 2 |
| role_tofangdar | 6 |
| role_rishSefid | 5 |
| role_Gorgname | −1 |
| role_Nazer | 6 اگر پیشگو در دست باشد، وگرنه 2 |
| role_Hamzad | 2 |
| role_kalantar | 6 |
| role_Fereshte | 7 |
| role_Ahangar | 2 |
| role_KhabGozar | 3 |
| role_Khaen | 0 |
| role_Kadkhoda | 4 |
| role_Mast | 3 |
| role_Vahshi | 1 |
| role_Shahzade | 3 |
| role_faheshe | 6 |
| role_ngativ | 4 |
| role_ahmaq | 3 |
| role_PishRezerv | 6 |
| role_PesarGij | −1 |
| role_NefrinShode | 1 − تعداد گرگ پایه در دست |
| role_Solh | 6 |
| role_shekar | 7 |
| role_Spy | 5 |
| role_Sweetheart | 4 |
| role_ferqe | 10 |
| role_WolfJadogar | 2 |
| role_WhiteWolf | 12 + تعداد گرگ پایه |
| role_WolfTolle | 12 |
| role_WolfGorgine | 10 |
| role_Wolfx | 11 |
| role_WolfAlpha | 12 |
| role_Honey | 9 |
| role_enchanter | 8 |
| role_forestQueen | 6 |
| role_Qatel | 15 |
| role_Archer | 14 |
| role_monafeq | 1 (در `_W`؛ در جمع‌بندی جداگانه نادیده/بازنویسی می‌شود) |
| role_Firefighter / role_IceQueen | هر کدام 15 |
| role_Royce | 10 |
| role_trouble / role_Huntsman | هر کدام 8 |
| سایر (default) | 0 |

### ۲.۷.۲ جمع وزن تیم (`GetRoleWight`)

- **گرگ:** جادوگر + توله + گرگینه + Wolfx + آلفا + عجوزه + افسونگر + سفید + ملکه جنگل
- **قاتل:** قاتل + کماندار
- **فرقه:** فرقه + رویس
- **آتش:** آتش‌نشان + ملکه یخ
- **اصیل (blod):** وزن Bloodthirsty (وابسته به ترتیب پیمایش به‌خاطر جمع با متغیر Vampire)
- **ومپایر:** وزن Vampire
- **لوسیفر:** در جمع صفر
- **منافق:** در این تابع `CountPlayer/2` ست می‌شود ولی در شرط‌های fail استفاده نمی‌شود
- **روستا:** بقیه (کلانتر هم به روستا اضافه می‌شود و شمارنده `kalan` +1)

### ۲.۷.۳ شرط بالانس اصلی (غیر Foolish/Bomber و غیر Vampire)

- وزن روستا **باید بیشتر** از وزن گرگ باشد
- وزن فرقه **نباید ≥** وزن روستا باشد
- جفت‌های اجباری: جوکر↔هارلی، یخ↔آتش، مگنتو با یخ، فرانک با فرقه، شکارچی↔فرقه (از ۱۱ نفر وقتی فرقه on)، شکارچی با پیشگو، پیش‌رزرو با پیشگو، داوینا با قاتل، ملکه جنگل با آلفا، سیاه↔عروس، دیان با حداقل یکی از سیاه/عروس، اصیل↔ومپایر↔کلانتر

### ۲.۷.۴ فرمول‌های وابسته به تعداد بازیکن (N)

| کمیت | فرمول |
|------|--------|
| مقیاس SG | N < 20 → 5 ؛ N ≥ 20 → 6 |
| تعداد گرگ پایه در استخر | `round(clamp(N/5, 1, 3))` |
| تعداد ومپایر اضافه (مود مربوط) | `round(N/5)` |
| کپی روستایی/فرقه اضافه | `round(N/SG)` |
| بمبر در مود Bomber | `round(clamp(N/SG, 1, 5))` + بقیه روستایی |
| گرگینه در Foolish | عملاً همیشه ۱ |
| حداقل شروع | ۵ عادی / ۷ Vampire |
| سقف تلاش بالانس | ۵۵۰ |
| حداکثر بازیکن گروه | `max_player` (پیش‌فرض ۳۵) |

### ۲.۷.۵ آستانهٔ ورود نقش به استخر

| حداقل N | نقش‌ها |
|---------|--------|
| ≥ 7 | ببر |
| ≥ 11 | شکارچی، فرقه، رویس، موش، جاسوس، فرانک؛ کپی اضافه فرقه اگر N>11 |
| ≥ 13 | شوالیه |
| ≥ 15 | ققنوس، هیپو، جاویدشاه، داوینا، کماندار، گاو، روح، مومیایی، لوسیفر |
| ≥ 18 | آتش‌نشان، ملکه یخ |
| ≥ 20 | مگنتو، بتاگرگ، لیلیس، هارلی، جوکر، هانتسمن، عجوزه، ملکه جنگل، افسونگر، گرگ سفید، گرگ یخی، گیاه‌شناس، هندوانه، بمبر، دینامیت، هل‌بوی |
| ≥ 25 | دیان، کنت ومپایر، اسرا، پرنسس، چیانگ |
| ≥ 30 | شوالیه سیاه، عروس مردگان |

نقش‌های VIP علاوه بر آستانه نیاز به `group_roles` با `status=true` برای همان چت دارند (`CheckAllowGroup`).

### ۲.۷.۶ مسیرهای ویژه مود

**Bomber:** فقط بمبر (۱–۵) + روستایی؛ بالانس فقط وجود هر دو را چک می‌کند؛ سپس منطق کاشت بمب و توزیع قطعات روی ۴ نفر اول.

**Foolish:** ۱ گرگینه + (از ۱۱: جادوگر، نگاتیو، پیش‌رزرو) + پیشگو + بقیه احمق؛ fail اگر گرگینه یا پیشگو نباشد.

**Vampire:** لیست `VampireRole`؛ ومپایر/اصیل مخصوص این مود (یا Mighty با N≥25)؛ حداقل ۷ بازیکن.

**Mighty:** بدون افزودن خودکار فراماسون و کپی روستایی.

### ۲.۷.۷ تبدیل‌های اجباری قبل از بالانس (به‌ترتیب)

1. جادوگر/عجوزه/افسونگر/خائن بدون گرگ پایه → جایگزینی با گرگ تصادفی از `WolfRole`
2. کماندار بدون قاتل → قاتل
3. ملکه جنگل بدون آلفا → آلفا
4. ومپایر بدون اصیل → یک اسلات امن → اصیل
5. اصیل بدون کلانتر → کلانتر
6. اصیل بدون ومپایر → ومپایر
7. فرقه یا رویس بدون شکارچی → شکارچی
8. پیش‌رزرو بدون پیشگو → پیشگو

### ۲.۷.۸ شانس‌های میدانی `SE::_s` (درصد)

| کلید | مقدار | معنی |
|------|-------|------|
| alpha_convert | 20 | تبدیل آلفا |
| Enchanter_Conver | 30 | تبدیل افسونگر |
| forestQueen_Convert | 10 | تبدیل ملکه جنگل |
| HunterKillWolfChanceBase | 30 | شانس شکارچی در برابر گرگ |
| HunterKillVampireChanceBase | 30 | شانس شکارچی در برابر ومپایر |
| RulerSecendVote | 40 | ثانیه/پارامتر رأی دوم حاکم |
| VampireChangeWolfD | 40 | تبدیل/تغییر ومپایر-گرگ |
| VampireChangeWolfDU | 50 | همان خانواده |
| VampireChangeWolfC | 10 | همان خانواده |
| WolfDeadChnageInVampie | 40 | مرگ گرگ در تعامل ومپایر |
| CultConvertVampie | 50 | فرقه → ومپایر |
| KalanVampireDead | 30 | کلانتر/ومپایر |
| BVampireChangeConvet | 40 | تبدیل اصیل |
| VampireChangeConvet | 20 | تبدیل ومپایر |
| VampireChangeNotKill | 50 | عدم کشت ومپایر |
| DodgeQatelDead | 35 | مرگ در داج قاتل |
| DodgeWolfDead | 35 | مرگ در داج گرگ |
| DodgeBloodDead | 50 | مرگ در داج اصیل |
| ChemistSuccessChance | 50 | موفقیت شیمیدان |

### ۲.۷.۹ تیم نقش (`GetRoleTeam`)

| تیم | نقش‌های نمونه |
|-----|----------------|
| rosta | روستایی، فراماسون، پیشگو، کارآگاه، تفنگدار، کلانتر، فرشته، شکارچی، … |
| wolf | انواع گرگ، عجوزه، افسونگر، ملکه جنگل، بتا، یخی |
| vampire | Vampire، Bloodthirsty، Chiang، kentvampire |
| Firefighter | Firefighter، IceQueen، Lilis، Magento |
| ferqeTeem | ferqe، Royce، Mummy، franc |
| qatel | Qatel، Archer، davina |
| lucifer | lucifer |
| joker | Joker، Harly |
| Bomber | Bomber |
| black | BlackKnight، BrideTheDead، dian |
| monafeq / hamzad / dinamit / dozd / khenyager | تک‌نقش‌های ویژه |

### ۲.۷.۱۰ گرگ‌های پایه (`WolfRole`)

`role_WolfTolle`, `role_WolfGorgine`, `role_Wolfx`, `role_WolfAlpha`

---

## ۲.۸ فهرست نقش‌ها (کلید داخلی)

### روستا
role_rosta, role_feramason, role_pishgo, role_PishRezerv, role_karagah, role_elahe, role_tofangdar, role_rishSefid, role_Gorgname, role_Nazer, role_kalantar, role_Fereshte, role_Ahangar, role_KhabGozar, role_Khaen, role_Kadkhoda, role_Mast, role_Vahshi, role_Shahzade, role_faheshe, role_ngativ, role_ahmaq, role_PesarGij, role_NefrinShode, role_Solh, role_shekar, role_Ruler, role_Spy, role_Sweetheart, role_Knight, role_trouble, role_Huntsman, role_Chemist, role_Augur, role_Princess, role_qhost, role_Phoenix, role_babr, role_Cow, role_Botanist, role_Watermelon, role_Mouse, role_clown, role_javidShah, role_hipo, role_GraveDigger (در کیبورد)

### گرگ
role_WolfTolle, role_WolfGorgine, role_Wolfx, role_WolfAlpha, role_WolfJadogar, role_Honey, role_enchanter, role_WhiteWolf, role_forestQueen, role_betaWolf, role_iceWolf

### فرقه / قاتل / آتش / ومپایر / سیاه / ویژه
role_ferqe, role_Royce, role_Mummy, role_franc  
role_Qatel, role_Archer, role_davina  
role_Firefighter, role_IceQueen, role_Lilis, role_Magento  
role_Vampire, role_Bloodthirsty, role_kentvampire, role_Chiang  
role_BlackKnight, role_BrideTheDead, role_dian  
role_monafeq, role_lucifer, role_Joker, role_Harly, role_Bomber, role_Hamzad, role_dinamit, role_dozd, role_khenyager, role_hellboy

---

# ۳. بخش مدیریت وضعیت (State Management)

## ۳.۱ معماری دو لایه

| لایه | نقش |
|------|-----|
| Redis (DB 5) | فاز، تایمر، انتخاب‌ها، فلگ‌های لحظه‌ای، صف پیام؛ کلید scoped: `{chat_id}:{key}` |
| MongoDB (`wop`) | اسناد پایدار جلسه و پروفایل |

### متدهای مفهومی Redis (`R`/`RC`)

| متد | معنی |
|-----|------|
| GetKey | کلید واقعی = chat_id:کلید |
| Get / GetSet | خواندن / نوشتن |
| CheckExit | وجود کلید (exists) — نه «خروج از بازی» |
| Del / DelKey | حذف تک‌کلید یا الگو |
| push / rpush / LRange / LRem | لیست‌ها |
| Ex | TTL |
| NoPerfix / NewServer | Redis بدون پیشوند گروه |

## ۳.۲ وضعیت سطح گروه

### فاز
`game_state`: `join` → `night` → `day` → `vote` → … → پایان (حذف / end)

همزمان `games.game_status` در Mongo.

### تایمرهای پیکربندی (پیش‌فرض هنگام افزودن بات)

| کلید | پیش‌فرض |
|------|---------|
| join_timer / day_timer / night_timer / vote_timer / secret_timer | ۹۰ث |
| max_extend_timer | ۶۰ |
| timer | timestamp پایان فاز جاری |
| max_player | ۳۵ |

### تنظیمات پایدار گروه (نمونه)

game_mode (پیش‌فرض general)، lang (fa)، type_mode (Normal/Chaos/Players)، expose_role، expose_role_after_dead، show_user_id، allow_flee، allow_extend، randome_mode، secret_vote (+count/name)، cult_hunter_expose_role، cultHunter_NightShow، role_fool، role_hypocrite، role_Cult، role_Lucifer، mute_die، PinMessage_on_group، SetUpRoles، group_link، و ده‌ها `role_*` on/off.

### شمارنده‌ها و فلگ‌های `GamePl:*` (مهم‌ترین‌ها)

- شناسه: game_id، StarterName، StartGameAt، StartedTime، gameModePlayer، EndJoinTimeGame
- شمارنده: Day_no (شروع ۱)، Night_no (شروع ۰)
- همزمانی: InComplater، GameIsEnd، SetTimer، CheckNight، CheckDay، CheckVote، CheckVoteSend، Update_vote
- کنترل فاز: Kill، RoleAssinged، SendNight، SendNightAll، SendDayRole، SendVote، NightRoleSends
- افکت: KhabgozarOk، DavinaOk، AhangarOk، MastEat، HunterKill، HunterKillVote، StopBlack، WolfCubeDead، RoyceDead، DeadforestQueen، trouble
- رأی ویژه: GroupInSolh، RulerOk، VoteCount، BlackVoteNo
- پیام‌ها: Player_ListMessage_ID، deleteMessage، EditMarkup، JoinKeyboard، Player_list، group_message، MessageNightSend، VoteMessage، MutedPlayer

## ۳.۳ وضعیت سطح بازیکن

### Mongo — `games_players`

| فیلد | معنی |
|------|------|
| user_state | ۱ زنده، ۰ مرده، ۲ smite |
| user_status | on / علت مرگ (vote, love, smite, afked, bomber, …) |
| user_role / team | نقش و تیم |
| dead_time / change_time / join_time | زمان‌ها |
| Number_game | نام نمایشی |

### Redis — انتخاب و روابط

- Selected:{user_id} (+ :user) — هدف شب/روز
- Selected:Vote:{user_id} — رأی‌دهندگان
- Selected:Wolf / Vampire / Magento — رأی تیمی
- UserInHome — بازدید خانه
- love / lover / CheckLover / SweetheartLove* — عشق
- ChangedUserRole، VampireBitten، BittanPlayer، EnchanterBittanPlayer، … — تبدیل
- DontVote، AfkedPlayer (سراسری)
- GunnerBult، SheriffBult، BombPlanted/BombCount، HuntsmanT، PlayerIced، PrincessPrisoner، BookIn، …

## ۳.۴ تغییرات وضعیت در رویدادها

| رویداد | تغییر کلیدی |
|--------|-------------|
| Join | insert games_players؛ push لیست؛ PlayerJoin فلگ |
| Flee | فقط در join؛ حذف از games_players و join_user |
| Start لابی | پاک GamePl؛ game_state=join؛ insert games |
| شروع واقعی | نقش‌دهی؛ RoleAssinged؛ night |
| شروع شب | timer=night_timer (یا ۰ اگر خواب‌گذار)؛ پاک انتخاب‌ها؛ کیبورد شب |
| شروع روز | timer=day_timer (یا ۳۰ داوینا)؛ اکشن روز |
| مرگ | user_state=0/2؛ علت؛ زنجیره عشق/نقش؛ میوت اختیاری |
| پایان | پیام برد؛ آنمیوت؛ پاک جلسه؛ آمار group_stats |

### کدهای CheckGPGameState
۰ هیچ / ۲ جوین عادی / ۱ بازی در جریان / ۳ جوین چالش / ۴ چالش در جریان

## ۳.۵ کالکشن‌های Mongo مرتبط

games, games_players, join_user, groups, Players, game_activity, group_stats, challenge_game, save_vote, next_game, group_roles, ban_list, white_list, …

---

# ۴. بخش پیام‌ها

## ۴.۱ نکتهٔ حیاتی دربارهٔ متن‌ها

تقریباً **تمام متن‌های جریان بازی** از کلیدهای `Lang` خوانده می‌شوند. منبع فایل‌ها در `bot\Strong\Game_Mode` است و طبق دستور کاربر **باز نشده‌اند**. در بازنویسی پایتون:

1. همان کلیدها را نگه دارید.
2. placeholderها: `{0}`, `{1}`, … (گاهی `%(timer)s`).
3. دو context زبان: گروهی (`LG`) و خصوصی کاربر (`L`).
4. اعلام نقش PV = کلید دقیقاً برابر شناسه نقش (`role_*`).

در زیر: **کلیدها + تریگر + مکان + placeholder** و سپس **متن‌های هاردکد کامل**.

## ۴.۲ معماری زبان

| مورد | جزئیات |
|------|--------|
| موتور | Lang — parse فایل ini |
| الگوی نام | `{mode}_{lang}.ini` مثل main_fa، general_en، nightclub_fa |
| زبان‌ها | fa، en، fr، in |
| fallback | general_fa → main_fa → `Translation not found! >> {key}` |
| KB.php | برچسب دکمه ندارد؛ دکمه‌ها از کلید Lang یا هاردکد |

## ۴.۳ پیام‌های جریان بازی — کلیدها

### عضویت / شروع (گروه و PV)

| کلید | مکان | تریگر | Placeholder |
|------|------|--------|-------------|
| Join_Message | گروه | تایمر عضویت | {0}=زمان |
| OnlyJoinTheGameTime | گروه | یادآوری زمان | {0} |
| joinToGame | دکمه | جوین | — |
| JoinTheGame | PV | جوین موفق | {0}=نام گروه |
| GameStart / GameStartOnGroup | گروه | شروع | — |
| StarterMessage | گروه/PV | شروع‌کننده | {0} |
| NotifyNewGame | PV | اعلان بازی جدید | {0}=گروه |
| NotStartGameForPlayer | گروه | بازیکن کم | — |
| ErrorStartGame_Balance | گروه | شکست بالانس نقش | — |
| MaxPlayer | گروه/PV | سقف | {0} |
| NotAllowToJoin / NotNameAllow / NotFoundGameId | PV | خطای جوین | — |
| players / playerlistOn | گروه | لیست | تعداد و لیست |
| minuts / minut / Secend / Seconds / minutes | کمکی زمان | — | {0} |

### اعلام نقش — PV

برای هر بازیکن کلید هم‌نام نقش ارسال می‌شود (۸۲+ شناسه `role_*`).

کلیدهای کمکی تیمی:

| کلید | معنی |
|------|------|
| pishgo_not / Not_pishgo | وضعیت پیشگو برای ناظر |
| bomberTeam | هم‌تیمی بمبر |
| BlackName / BrideName | جفت سیاه |
| role_QatelIfArcher | نام کماندار برای قاتل |
| role_kalantarBloodInHome | اصیل در خانه |
| role_feramason_team / role_ferqe_team / role_wolf_team | هم‌تیمی‌ها |
| role_FirefighterIce / role_IceQueenFire | جفت آتش/یخ |
| role_forestQueenAlpha / role_WolfAlpha_force | جفت آلفا/ملکه |
| YoWatermelon / user_role | قالب‌های کمکی |

پسوند نام کوتاه نقش در مرگ/رأی: `{role}_n`.

### فاز شب/روز — گروه

| کلید | تریگر | Placeholder |
|------|--------|-------------|
| MassgeFortypeSummery_night | شروع شب | {0}=night_timer |
| MassgeFortypeSummery_day | شروع روز | {0}=day_timer |
| Day_nos | شماره روز | {0} |
| SandmanNight | شب خواب‌گذار | — |
| NoAttakInDay | بدون حمله شب قبل | — |
| MessageDayWhenDavina | روز داوینا | — |
| Shekar_msg | شکارچی شب | {0} نام، {1} شمارش |

### اکشن شب — PV (Ask*)

AskKill, AskConvert (+DiscussWith), AskDetect, AskCupid1/2, AskVampire, AskWhenBlood, AskWhenBloodTeam, AskEnchanter, AskFireFighter, AskArcher, AskBabr, AskBomber ({0} بمب، {1} تیم), AskWhiteWolf, AskFranc, FrancAskNight, AskPhoenix, AskCow, AskKentVampire, AskIceWolf, AskGhost, AskDinamit_night, AskMummy, AskDozd, AskChemist, AskLilis, AskLilisAfterDie, AskBrideTheDead, AskMagento (+MagentoTeam), AskJokerFind, AskHarly, Askkhenyager, Ask_Honey, HowAngelIs, howSeeIs, howFahesheIs, askJado, role_hunstmanAsk, role_MouseAsk، …

نتایج: eatUser, eat_you, DefaultKilled, ChemistSuccess, IceWolfIcedMessage, CultConvertYou, VampireConvert، و ده‌ها کلید مرگ/اثر با {0}=نام و {1}=نقش کوتاه.

### اکشن روز — PV

AskShoot ({0}=گلوله)، AskPrincess، AskDianDay/AskDianTowDay، AskDayKentVampire، AskDinamit_day، SpyAsk، BlackKnightAsk، AskDavina، Asktrouble، howEstelamIs، solh_L+solh_btn، Kadkhoda_l+Kadkhoda_btn، RulerAsk+RulerButton، ahangar_L+دکمه‌ها، KHABGOZAR_l+دکمه‌ها، UserBittenByWolf/Vampire + Btn_okSend/Btn_NotOk.

### رأی

| کلید | مکان | معنی |
|------|------|------|
| MassgeFortypeSummery_vote | گروه | شروع رأی؛ {0}=vote_timer |
| MassgeFortypeSummery_Secretvote | گروه | رأی مخفی؛ {0}=secret_timer |
| RulerMessageVoteNow | گروه | رأی حاکم |
| howVote / DodgehowVote | PV | کیبورد رأی / داج |
| lynic_to | گروه | شمارش |
| voteUser / RulerVoteMessage | گروه | X به Y |
| SecretLynchResultNumber / Full | گروه | نتیجه مخفی |
| killed_user / RulerKillPl | گروه | اعدام |
| no_kill / RuleTimeEnd / PacifistNoLynchNow | گروه | بدون اعدام |
| KillShahzade / BlackKnightKillVote | گروه | مصونیت‌ها |
| HunterLynchedChoice / HunterShotChoice | PV | تیر مرگ کلانتر |

### مرگ / AFK

DefaultKilled و انواع *Killed / *_eat؛ afkedPlayerMessage؛ LoverDied؛ PlayerDead؛ is_dead / is_on / is_smited؛ mutedPlayer (PV)؛ BittenTurned / BittenTurnedVampire؛ زنجیره‌های HL برای همزاد/عاشق/فرانک/رویس.

### برد / باخت

winner_rosta, winner_wolf, winner_ferqeTeem, winner_qatel, winner_lover, winner_monafeq, winner_nothing, winner_joker, winner_Bomber, win_Firefighter, win_vampire, win_black, win_dinamit، endGame ({0} زنده/کل، {1} خطوط، {2} مدت)، winner/loset/is_smited در خطوط لیست، WinCoinEndGame (PV)، TannerEnd، FirefighterEnd، IceFirefighterEnd، HunterKillsWolfEnd، WolfKillsHunterEnd، SKHunterEnd، CHKillsCultistEnd، SerialKillerWinsOverpower، VampireKillsHunterEnd، …

### دکمه‌ها (کلید Lang)

joinToGame, Btn_okSend, Btn_NotOk, solh_btn, Kadkhoda_btn, RulerButton, ahangar_btn, ahangar_btnY, KHABGOZAR_BTN, KHABGOZAR_BTN_N, DavinaYes/No, troubleBtnYes/No, ButtenFireFighter, cancel, UnlokAll, config_*, CloseBuy, KeyBoardUseMajik, NotInGameCloseKeyboard، …

**آمار تقریبی کلیدها در منطق:** ~۱۰۸۶ یکتا؛ ~۸۲ نقش PV؛ ~۴۱ Ask*؛ ~۲۱ برد؛ ~۳۱ رأی؛ ~۲۲۷ مرگ/کشتن.

## ۴.۴ متن‌های هاردکد کامل (خارج از Game_Mode)

### منوی کیبورد PV
- 🩸 برترین کاربران کیل
- 👥 لیست گروه ها
- 🎓 آکادمی مافیا
- 💰 خرید سکه
- 🛍  فروشگاه
- 📞 پشتیبانی
- 📣 اخبار
- مجیک: 🤪 خبر چینی ؛ 🔮 اعلام نقش ؛ 😇 محافظ ؛ 👻 روح

### بن / ادمین / محدودیت
- شما هنوز بازی در اونیکس ندارید  دوست عزیز!
- حداقل بایستی 50 بازی داشته باشید!!
- گروه مسدود میباشد!
- روز خوبی داشته باشید
- پیام‌های بن با قالب «شما تا %s دقیقه/روز/هفته/ماه/سال …» و «برای همیشه …» و «مدیر محدود کننده : %s»
- دسترسی به این بخش برای شما محدود شده است
- تو خصوصی بفرست!
- بستن صفحه
- دکمه‌های ادمین: بن کردن کاربران، بن برای همیشه، وارن دادن، اسمایت کردن کاربر، بستن بازی، مدیر همه چیز، …
- عنوان: تنظیمات دسترسی مدیر %s
- این دستور از جانب مدیر اصلی بسته شده است برای شما
- شما بدلیل اسپم نمودن دستورات ربات از ربات بصورت دائمی بن شده اید!
- لیگ این هفته به اتمام رسید!

### نام تیم‌ها (هاردکد در CM)
تیم گرگ ؛ تیم روستا ؛ تیم ومپایر ؛ تیم فرقه ؛ تیم قاتل ؛ نامشخص

### سایر
- ارسال / منصرف شدم / فروارد برای تمامی بازیکنان
- شرط‌بندی اسب: اسب شماره 1..8 🐴 ؛ ❌ لغو و خروج ؛ ✅ ثبت شرط

---

# ۵. راهنمای بازنویسی پایتون (جمع‌بندی عملیاتی)

1. **State store:** Redis با پیشوند chat_id + Mongo برای جلسه/پروفایل؛ همان نام کلیدهای `GamePl:*` را حفظ کنید تا مهاجرت آسان شود.
2. **Tick loop:** معادل Handler هر ۱–۲ ثانیه: قفل → CheckEndGame → checkTime → CheckTimer → فاز هندلر.
3. **Role engine:** پیاده‌سازی دقیق GetRoleRandom → slice → forced converts → weight checks → retry≤550.
4. **Night resolver:** ترتیب CheckNight را عیناً حفظ کنید؛ ترتیب اثر حفاظتی را تغییر ندهید.
5. **i18n:** لایهٔ کلیدمحور با `{0}`؛ متن‌ها را از iniهای Game_Mode وقتی مجاز شد وارد کنید.
6. **مودها:** Normal/Mighty/Easy/Vampire/Romantic/WereWolf/Bomber/Foolish را جدا نگه دارید؛ Bomber/Foolish مسیر استخر جدا دارند.
7. **تست طلایی:** برای N=5,7,11,15,18,20,25,30 دست‌های نقش و شرط بالانس را property-test کنید.

---

*پایان مستند. منابع تحلیلی: join.php، SE.php، NG.php، DY.php، VT.php، HL.php، Handler.php، GR.php، CM.php، RC/R.php، Lang.php — بدون خواندن bot\\Strong\\Game_Mode.*
