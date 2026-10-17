# اقتصاد / فروشگاه / سکه / چالش و سامانه‌های آرایشی (غیرگیم‌پلی هسته)

**دامنه:** لایه‌های متا کنار بازی ورولف — نه پایپ‌لاین شب/روز/رأی/نقش‌ها.  
**منبع:** `CM.php`، `GR.php`، `HL.php`، `Handler.php`، `join.php`، `Hook.php`، `CronJob.php`، Commands مربوط، `main_fa.ini`.  
**مرتبط:** `docs/php-gaps-and-defects-fa.md` (§۱۲، ۱۵، ۱۶)، `docs/remediation-accepted-fixes-fa.md` (§۸، ۱۱)، `docs/sprint-10-commands-callbacks-fa.md`، `docs/economy-gaps-and-stubs-fa.md`.  
**سبک:** تحلیل رفتاری + جداول؛ بدون بلوک کد پیاده‌سازی.

---

## ۱. نمای معماری

این خوشه سیستم‌هایی است که به `Players.credit` (سکه/اونیکس)، خرید آرایشی/جادو، پرداخت ریالی، شرط‌بندی جانبی، حساب VIP، و UI خصوصی وصل‌اند. گیم‌پلی هسته (نقش، شب، لینچ) فقط در نقاط تماس مشخص مصرف می‌کند (مثلاً ~~مود `coin`~~ **حذف محصولی**، دزد، اثر جادو در Handler).

> **قفل:** مود بازی `coin` از بازنویسی پایتون حذف است؛ مستند currency/shop زیر برای متا باقی می‌ماند.

| سامانه | نقش | نقطه ورود اصلی | ماندگاری |
|--------|-----|----------------|----------|
| سکه (`credit`) | موجودی | `/mycoin`، join مود coin، شاپ، ادمین، دونیت، بت، پیام خصوصی | Mongo `Players.credit` |
| خرید ریالی سکه | شارژ | `/coin` → `GetCoin_*` | `transaction` + درگاه pay.ir (ناقص) |
| فروشگاه | خرج سکه | `/shop`، منوی «🛍 فروشگاه» | Redis شمارنده جادو؛ Mongo نقش/لقب/اموجی/XP |
| جادو (مجیک) | مصرف در بازی | کال‌بک `slectMajik/...` پس از نقش‌دهی | Redis موجودی + `GamePl:UseMajik:*` |
| اموجی کنار اسم | آرایشی | شاپ Emoji → پیام خصوصی | `Players.ActivePhone` |
| لقب | جایگزینی نام نمایشی | شاپ MajiKLaqab → `setLaqabToMe/{id}` | `laqab_lists` + `Players.fullname` / `set_laqab` |
| شرط‌بندی اسب | مینی‌گیم جدا | کال‌بک‌های Bet (فرمان `/bet` خاموش) | `bet_game`، `player_bets` |
| چالش گروهی | محصول وعده‌داده‌شده | `/startchallenge` | Mongo `challenge_game` فقط **خوانده** می‌شود |
| تورنمنت | ثبت‌نام جدا | `CM_JoinTornumet` | `PlayerTornumets` / `tornumets` |
| حساب VIP/نقره | ارتقا ماهانه | `/account` | `Players.user_role` + `expire` |
| دستاورد | آنلاک پیام | `SavePlayerAchivment` در پایان بازی | `achievement_player` |
| قهرمان (Hero) | UI نیمه‌کاره | `/myhero` | `Heros` (خرید سکه در کال‌بک مرده) |
| لیگ | امتیاز هفتگی | `/myleaguescore`، `/getleague` | `leagueData` + Redis `LeagueData` |

```
کاربر خصوصی ──► منو/کامند ──► CM_*
                              │
                              ├─► GR::UpdateCoin / MinCreditCredit ──► Players.credit
                              ├─► Redis NoPerdis (جادو، قفل خرید اموجی، بت)
                              ├─► درگاه pay.ir (donate / GetChargeItem)
                              └─► در بازی: Handler → HL::HandelMajik
```

---

## ۲. سکه (currency)

### ۲.۱ فیلد و توابع ماندگاری

| مفهوم | محل |
|--------|------|
| موجودی | `Players.credit` |
| خواندن | `GR::GetUserCredit` |
| نوشتن مطلق | `GR::UpdateCoin($Coin,$user_id)`، `HL::UpdateCoins`، `HL::UpdateCoin` (ترتیب آرگومان متفاوت در مسیر دزد) |
| نوشتن برای خود کاربر | `GR::MinCreditCredit($New)` |

### ۲.۲ مسیرهای کسب (earn)

| مسیر | مقدار / فرمول | وضعیت در PHP |
|------|----------------|--------------|
| مود بازی `coin` — برد | `((تعدادبازیکن × ۱۰) − ۵) / تعدادبرندگان` گرد شده؛ پیام `WinCoinEndGame` | فعال در `SendListEndGame` |
| مود `coin` — فرار از لابی | +۱۰؛ `BackSendCoinFlee` | فعال |
| مود `coin` — اسمایت | +۱۰؛ `BackSendCoinSmite` | فعال |
| مود `coin` — KillGame | +۱۰ به بازیکنان زنده؛ `BackSendCoinKill` | فعال |
| مود `coin` — بازی شروع‌نشده بسته شد | +۱۰؛ `BackSendCoinEndGame` | فعال در `GroupClosedThGame('join')` |
| `/getfreecoin` → `CM_FreeCoin` | +۱۰۰ یک‌بار؛ کلید Redis `get_free_coin1:{uid}` | **در ابتدای تابع `return false` — مرده** |
| `/getcoin` → `CM_GetCoin` | +۶۰ هر ۱۰ دقیقه؛ `userGetCoin:{uid}` | **همان؛ `return false` اول** |
| `/addcoin` (ادمین) | `+/-` روی موجودی | فعال فقط برای `ADMIN_ID` (شاخه‌های اشتباه به smite هم دارد) |
| `/sendcoin` | انتقال حداقل ۴ سکه با ریپلای | فعال؛ سقف روزانه ۵ در کامنت غیرفعال |
| برد شرط اسب | ضریب ۵ / ۸ / ۱۰ روی مبلغ اسب برنده | `CronJob::PlayerBetWin` |
| دزد در شب | جابه‌جایی سکه بین بازیکنان | گیم‌پلی هسته؛ مصرف‌کننده economy |
| دونیت / شارژ ریالی | پس از verify وب | verify در درخت bot **دیده نشد**؛ Token خالی |

### ۲.۳ مسیرهای خرج (spend)

| مسیر | مقدار | یادداشت |
|------|--------|---------|
| جوین مود `coin` | −۱۰ | قبل از `PlayerJoinTheGame` |
| شاپ (اکثر آیتم‌ها) | طبق جدول §۳ | |
| لقب در `SetLaqab` | −۳۰ | با قیمت دکمه شاپ (۴۰) ناهماهنگ |
| ارتقا silver / vip | ۲۰۰ / ۳۵۰ | یک ماه |
| پیام خصوصی «پخ:» | −۳ | فقط در بازی |
| تأیید شرط بت | مبلغ `total` در `player_bets` | |
| انتقال `/sendcoin` | مبلغ ارسالی | |

### ۲.۴ کلیدهای Redis مرتبط با سکه

| کلید | معنی |
|------|------|
| `get_free_coin1:{uid}` | یک‌بار رایگان (کد مرده) |
| `userGetCoin:{uid}` | کول‌داون getcoin (کد مرده؛ expire ۶۰۰ث) |
| `sendCoinTo:{uid}` | شمارش ارسال روزانه (محدودیت کامنت‌شده) |
| `PlayerEmojiBuy:{uid}` | قفل سفارش اموجی ناتمام |
| `PlayerEmojiBuyMessageID:{uid}` | پیام رسید اموجی |
| `UserBet:{uid}` | واحد هر کلیک بت (پیش‌فرض ۱۰) |
| `MajikSearPlayer:{uid}` و مشابه | موجودی جادو (نه داخل `GamePl:`) |

---

## ۳. فروشگاه

### ۳.۱ جریان کلی

1. `/shop` یا منوی خصوصی → `CM_Shop` (اگر `PlayerEmojiBuy` باشد فقط دکمه لغو).  
2. کال‌بک `ShopItem_{id}` → `ShopItemSet`: چک موجودی، پیام تأیید با `BTNSP_YES_{item}` / `BTNSP_NO`.  
3. `ShopCheckout`: کسر سکه (به‌جز Emoji و MajiKLaqab در این مرحله)، تحویل آیتم، پیام ادمین `AdminMessageCheckOut`.

### ۳.۲ کاتالوگ قیمت (`CM::GetCoin`)

| شناسه آیتم | قیمت سکه | تحویل |
|------------|----------|--------|
| Dozd | ۴۰۰ | `buy_role` با `role_dozd`؛ یک‌بار (`checkLastByRole`) |
| Emoji | ۵ | ورود به حالت انتظار اموجی؛ کسر هنگام `EmojySend` |
| MajikSear | ۲ | +۱ به Redis `MajikSearPlayer:{uid}` |
| MajiKhabar | ۵ | `MajiKhabarPlayer:{uid}` |
| MajiKGhost | ۱۱ | `GhostPlayer:{uid}` |
| MajiKHil | ۹ | `MajiKHilPlayer:{uid}` |
| MajiKLaqab | ۴۰ (نمایش) | فقط لیست لقب؛ کسر واقعی در `SetLaqab` با ۳۰ |
| Xp500 / 1000 / 5000 / 10000 | ۲۰ / ۴۰ / ۲۰۰ / ۴۰۰ | به فیلد `Site_Password` به‌عنوان XP؛ سطح در `Site_Username` |

پیش‌فرض سوئیچ اگر شناسه ناشناخته باشد: ۶۰۰۰۰۰ (تقریباً unreachable از کیبورد فعلی).

### ۳.۳ آیتم‌های Lang بدون دکمه شاپ

- `ShopItem_sponser100` — فقط در ini؛ در کیبورد `CM_Shop` **دیده نشد**.  
- `dozd_coin` در پنل `/coin` (خرید ریالی نقش دزد) — در `GetChargeItem` قیمت `dozd` تعریف شده ولی دکمه در `CM_Coin` نیست.

### ۳.۴ خطا / لغو / بدون refund خودکار

- کمبود موجودی: آلرت `PleaseChargeAccount`.  
- سفارش اموجی باز: `ShopItemBeforItem` + `BTNSP_NO` پاک‌کردن کلیدهای Redis.  
- نقش دزد تکراری: `FiledByRole`.  
- پس از کسر موفق، مسیر برگشت وجه خودکار در کد شاپ **دیده نشد** (عملیات غیرقابل برگشت طبق `ShopItemTitleDoc`).

---

## ۴. شارژ ریالی و دونیت

### ۴.۱ `/coin` — بسته‌ها

| کال‌بک | سکه وعده | مبلغ ریال در `GetChargeItem` | برچسب Lang (تومان) |
|--------|----------|------------------------------|---------------------|
| GetCoin_100 | ۱۰۰ | ۱۰۰۰۰۰ | ۱۰٬۰۰۰ |
| GetCoin_300 | ۳۰۰ | ۲۸۰۰۰۰ | ۲۸٬۰۰۰ |
| GetCoin_600 | ۶۰۰ | ۵۴۰۰۰۰ | ۵۴٬۰۰۰ |
| GetCoin_1000 | ۱۰۰۰ | ۹۲۰۰۰۰ | ۹۲٬۰۰۰ |

رفتار فعلی `GetChargeItem`: فراخوانی `GR::send` به pay.ir سپس ارسال `var_export($result)` به کاربر — لینک پرداخت تمیز و واریز سکه پس از verify در همین تابع **پیاده نشده**. `Hook::$TokenPayment` رشته خالی است.

### ۴.۲ `/donate` — `CM_Dontate`

- بدون مبلغ: لینک `https://me.pay.ir/onyxwerewolf` + `DonateText`.  
- با عدد: مبلغ = ورودی ×۱۰ (ریال)، ذخیره `transaction` با `item=sponser`، لینک درگاه.  
- لیست اسپانسر: `CM_Sponsers` از تراکنش‌های `status=1`.

صفحه/`verify` وب در workspace bot **یافت نشد**؛ واریز نهایی سکه پس از پرداخت در این ریپو مستند نیست.

---

## ۵. چالش (Challenge)

### ۵.۱ آنچه در Lang و UI هست

کلیدها: `JoinChallenge`، `StartChallengeGame`، `ChallengeStart`، `ChallengePlayers`، `StartLastChallenge`، اشاره به `/challengeforce`.  
لینک جوین: `Challenge_URL` + `game_id` → `https://t.me/OnyxWereBetaBot?start=ChallengeJoin_…`.

### ۵.۲ آنچه در کد هست

| قطعه | رفتار |
|------|--------|
| `StartChallengeCommand` | صدا می‌زند `CM::CM_StartChallenge()` |
| `CM_StartChallenge` | **متد وجود ندارد** (فقط کامنت `// Challenge Game` نزدیک `CM_KillGame`) |
| `GR::CheckGPGameState` | اگر سندی در `challenge_game` با `group_id` و `game_status=join` باشد → کد وضعیت ۳ |
| `CM_Join` / `CM_StartGame` case 3 | دکمه URL چالش |
| درج در `challenge_game` | در کل درخت PHP **دیده نشد** |

نتیجه: چالش از نظر محصول در پیام‌ها زنده است؛ از نظر بک‌اند ایجاد سشن و handler استارت **شکسته/غایب**. جزئیات backlog در `economy-gaps-and-stubs-fa.md` و remediation §۸.

### ۵.۳ تمایز با تورنمنت / لیگ / بت

- **تورنمنت:** `CM_JoinTornumet` — Mongo جدا؛ پرداخت داخل این مسیر کامل دیده نشد (فیلد `pay`).  
- **لیگ:** امتیاز `leagueData`؛ نمایش لیست در Redis.  
- **بت اسب:** مینی‌گیم کانال جدا؛ نه چالش گروهی ورولف.

---

## ۶. پنل مجیک (جادو)

### ۶.۱ خرید و موجودی

خرید از شاپ → شمارنده Redis سراسری کاربر (نه per-game). هر خرید +۱.

### ۶.۲ فعال‌سازی در بازی

پس از توزیع نقش (`join.php`): اگر مجموع موجودی جادو > ۰، اینلاین‌کیبورد با کال‌بک‌های:

`slectMajik/{chat_id}/{type}` → `CM::UseMajik($type)`.

انواع: `MajiKhabar`، `MajikSear`، `MajiKGhost`، `MajiKHil`.

قواعد مشترک فعال‌سازی:

- باید `in_game` باشد.  
- موجودی > ۰ وگرنه `NotBuy`.  
- حداکثر یک جادو در هر بازی: کلید `{group_id}:GamePl:UseMajik:{uid}`.  
- کم کردن شمارنده Redis و ست کردن نوع برای Cron.

### ۶.۳ اعمال توسط Handler/Cron — `HL::HandelMajik`

| نوع Redis | اثر پس از `GamePl:StartNewGame` |
|-----------|----------------------------------|
| MajiKhabarPlayer | `SendMajikKhbarr` — افشای نقش تصادفی (ترجیحاً غیرهم‌تیم؛ طبق تیم کاربر) |
| GhostPlayer | فلگ شب/روز روح: `GamePl:GhostPlayer_Night/Day:{uid}`؛ مخفی از لیست هدف |
| MajiKHilPlayer | `GamePl:Heal_Night:{uid}`؛ `CheckMajikHealPlayer` |
| MajikSearPlayer | **در HandelMajik case ندارد** |

### ۶.۴ جادوی اعلام نقش (Sear)

- در شاپ قابل خرید و موجودی ذخیره می‌شود.  
- `UseMajik('MajikSear')` بلافاصله `return false` (بدنهٔ زیرش مرده).  
- حتی اگر فعال می‌شد، Handler اثر Sear را اعمال نمی‌کند.  
- توضیحات `HelpShop`: برای احمق/جادوگر ۱۰۰٪ نقش — فقط در Lang.

پنل reply-keyboard `GetMajicKeybaord` وجود دارد؛ ارسال خودکار آن در Hook **کامنت شده**؛ مسیریابی متن دکمه‌های «اعلام نقش/خبر چینی/…» به `UseMajik` در Genericmessage **دیده نشد** (مسیر زنده = اینلاین پس از نقش‌دهی).

---

## ۷. آرایشی: اموجی، لقب، مدال، VIP نمایشی

### ۷.۱ اموجی کنار اسم

1. خرید Emoji → پیام انتخاب + Redis `PlayerEmojiBuy`.  
2. کاربر یک اموجی می‌فرستد؛ `has_emojis_old` باید دقیقاً یک match بدهد.  
3. `GR::UpdateEmoji` → فیلد `ActivePhone`.  
4. در جوین، `ActivePhone` کنار `fullname_game` چسبانده می‌شود.

Hook: اگر پیام «اموجی‌گونه» باشد و قفل خرید نباشد، ممکن است early `die('block')` — حین خرید اموجی استثنا می‌شود.

### ۷.۲ لقب (Laqab)

1. شاپ MajiKLaqab → کیبورد از `laqab_lists` (`GetLaqabList`).  
2. `setLaqabToMe/{id}` → اگر آزاد، رزرو، کسر ۳۰ سکه، ست `Players.fullname` به نام لقب و `set_laqab=true`.  
3. همگام‌سازی نام تلگرام در Hook: اگر `set_laqab` باشد نام از تلگرام overwrite نمی‌شود (شاخه باگ‌دار: به `set_laqab` به‌عنوان رشته نام ارجاع می‌دهد نه `fullname`).

لقب‌های اشغال‌شده کال‌بک `activeLast` (بدون handler اختصاصی مفید).

### ۷.۳ مدال زمان بازی

`userGameTime:{uid}` (دقیقه) → `getMedal` → ایموجی‌های 🥉…🔪 کنار اسم در جوین. این مدال **خرید شاپ نیست**؛ پیشرفت زمانی است.

### ۷.۴ الماس ادمین

فقط `ADMIN_ID` در لیست هاردکد → پسوند 💎 در نام بازی.

---

## ۸. شرط‌بندی (Bet) — جدا از چالش

| بخش | وضعیت |
|-----|--------|
| `/bet` → `BetCommand` | `return false`؛ فراخوانی `CM_bet` کامنت |
| `CM_bet` | منوی اسب / انفجار |
| `BetGame/hourse` | `CreateBet` → ساخت/عضویت بت |
| `BetGame/bomb` | در منو هست؛ در `CreateBet` **پیاده نشده** |
| `bst` / `bgs_confirm` / `bls_reject` / `bghChangeBet` | پنل ثبت شرط و تغییر واحد |
| تسویه برد | CronJob روی اسب برنده |
| `CM_Game` | شبیه‌سازی مسابقه اسب (اداری/تست‌گونه) |

تصمیم remediation: حذف یکدست یا فعال‌سازی صریح — فعلاً فرمان خاموش، کال‌بک‌ها زنده.

---

## ۹. حساب کاربری، VIP، تنظیمات نقش خریداری‌شده

| فرمان/کال‌بک | رفتار |
|--------------|--------|
| `/account` | نوع `user` / `silver` / `vip` + انقضا |
| `upAcc` / `ugrade` | تأیید و کسر ۲۰۰/۳۵۰؛ `ChangeUserType` یک ماه |
| VIP | ست متن/گیف رویدادهای بازی (`asdopt`، `settext`، `setgif`) |
| `/mysetting` | اگر `buy_role` داشته باشد تاگل فعال/غیرفعال نقش؛ وگرنه ریدایرکت شاپ |
| `SGFDRol|{role}` | `UpdateSettingRole` |

---

## ۱۰. دستاورد، قهرمان، سایر متا

### ۱۰.۱ Achievement

- مسیر زنده: `HL::SavePlayerAchivment` → کالکشن `achievement_player` + پیام `AchioUnlock` + کلید + `_dic`.  
- stub: `AddPlayerAchio` / `CheckPlayerAchio` خالی؛ `CM_Achievement` فقط `GetAchievement` را صدا می‌زند بدون خروجی.  
- نمونه آنلاک از گیم‌پلی: `Wasted_Silver`، `Cult_Leader`، `Psychopath_Killer`، `YouWatermelon` و …

### ۱۰.۲ Hero

- `/myhero` UI ساخت؛ `CreateHero` رکورد `Heros` با `payment:20`.  
- دکمه‌های قیمت ۵۰…۱۵۰۰ سکه (`BfdHero/all` و …) در `CreateHero` **case ندارند** → خرید قهرمان با سکه در عمل مرده.  
- توضیح عکس فقط برای `des_hero_all` مسیر تصویر دارد؛ بقیه des ممکن است `$Img` تعریف‌نشده باشد.

### ۱۰.۳ مود سکه بازی (`/startcoin`)

> **تصمیم محصول: مود سکه به کل حذف — در پایتون پیاده نشود.**  
> کلید مود: `gameModePlayer=coin`؛ استارت: `/startcoin` → `CM_StartGame('coin')` (remediation §۱۷؛ MF-60).  
> **تفکیک:** حذف فقط **مود گیم‌پلی** است. موجودی `Players.credit`، شاپ `/shop`، شارژ ریالی `/coin`، `/mycoin`، `/sendcoin` و مصرف‌کننده‌های گیم‌پلی مثل دزد **حذف نشده‌اند** مگر تصمیم جدا.

لابی عادی با `gameModePlayer=coin`: ورودی −۱۰؛ برد سهم از pot؛ استرداد در فرار/کیل/اسمایت/کنسل جوین. این **مود گیم‌پلی** است ولی کاملاً به اقتصاد وصل است. (رفتار PHP تاریخی؛ خارج از scope بازنویسی.)

---

## ۱۱. کاتالوگ کلیدهای مهم Lang (`main_fa.ini`)

| کلید | کاربرد |
|------|--------|
| MyCoin / MyCoinD | موجودی در پنل خرید / mycoin |
| 100_coin … 1000_coin | برچسب بسته شارژ |
| ShopDetial / ShopItem_* / ShopItemTitle_* | شاپ |
| ShopCheckOutMessagePlayer_* | رسید بازیکن |
| AdminMessageCheckOut | لاگ ادمین خرید |
| PleaseChargeAccount / NotFoundPlayer / CloseBuy / ShopCloseMsg | خطا/لغو |
| HelpShop | راهنمای جادوها |
| KeyBoardUseMajik / NotBuy / LastUserMajic / SuccessActive_* | مجیک |
| MajikKhabarChinSee / GhostActive / ActiveHealMajik | اثر جادو |
| DonateText / DonateItemText | دونیت |
| FreeCoinSuccess / GetFreeCoinLast / GetCoin / LastGetCoins | مسیرهای رایگان (کد خاموش) |
| NotAnogthCoin / MinCoin / WinCoinEndGame / BackSendCoin* | مود coin |
| JoinChallenge / StartLastChallenge / ChallengeStart | چالش (UI) |
| BetText / bet_hourse / bet_bomb / TextBet / BetMinPlayer / MsgBetSet | بت |
| btnUpToSilver / btnUpToVip / Account_* / TransectionMsg | VIP |
| AchioUnlock / *_dic | دستاورد |

متن کامل: `docs/werewolf-messages-fa-complete.md`.

---

## ۱۲. ماشین‌حالت‌های کوتاه

### ۱۲.۱ خرید شاپ عادی

`لیست شاپ` → `انتخاب آیتم` → `تأیید YES` → `کسر + تحویل` → `رسید`  
شاخه NO / CloseBuy → لغو و پاک‌سازی قفل اموجی.

### ۱۲.۲ خرید اموجی

`تأیید Emoji` → `منتظر پیام اموجی` (Redis) → `اعتبارسنجی تک‌اموجی` → `کسر + ActivePhone` → پاک قفل.

### ۱۲.۳ جادو در سشن

`موجودی Redis` → `نقش‌دهی` → `پنل اینلاین` → `UseMajik` (مصرف + فلگ بازی) → `Handler HandelMajik` → اثر یک‌بار در بازی.

### ۱۲.۴ بت اسب (اگر از کال‌بک وارد شود)

`BetGame/hourse` → انتخاب اسب‌ها با واحد `UserBet` → confirm → کسر credit → status in_game → Cron مسابقه/پرداخت برد.

---

## ۱۳. یادداشت هم‌ارزی برای بازنویسی پایتون (parity)

باید در پایتون بازسازی یا صریحاً تصمیم‌گیری شوند:

1. مدل یکپارچه `credit` با تراکنش قابل audit (PHP اغلب set مطلق بدون ledger).  
2. کاتالوگ شاپ + قیمت‌ها + تحویل Redis/Mongo مطابق جدول §۳.  
3. ~~مود `coin`: ورودی ۱۰، استردادها، فرمول برد.~~ — **حذف محصولی**؛ در QA پایتون نباشد.  
   ارز/شاپ/شارژ جدا تست شوند وقتی تصمیم MF-37… گرفته شد. 
4. چهار جادو: خرید، سقف یک‌بار در بازی، اثر Handler؛ تصمیم برای Sear (الان شکسته).  
5. اموجی / لقب / XP / buy_role + mysetting.  
6. VIP ماهانه و آپشن متن/گیف.  
7. مسیر پرداخت: یا درگاه واقعی + verify، یا حذف وعده از UI.  
8. چالش: یا MVP کامل طبق remediation، یا حذف فرمان/دکمه‌ها.  
9. بت: یا حذف یکدست (`/bet` + کال‌بک + Cron)، یا فعال‌سازی با bomb یا بدون آن.  
10. Achievement فقط از مسیر `SavePlayerAchivment`؛ stubهای Achio را تکرار نکنید.  
11. Hero: یا تکمیل خرید، یا UI بدون دکمه مرده.  
12. پیام خصوصی ۳ سکه و انتقال حداقل ۴ سکه.

گیم‌پلی هسته (نقش‌ها، شب، رأی) در اسپرینت‌های ۱–۹/۱۱ است؛ این سند فقط لایه متا/اقتصاد را پوشش می‌دهد.
