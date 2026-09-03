# گزارش ناقصی‌ها / stub / مسیرهای مرده — اقتصاد و متای غیرگیم‌پلی

**دامنه:** سکه، شاپ، چالش، مجیک، لقب، اموجی، بت، VIP، دستاورد، قهرمان، پرداخت.  
**مرجع اصلی رفتاری:** `docs/economy-shop-challenge-fa.md`  
**هم‌پوشانی با گزارش عمومی:** `docs/php-gaps-and-defects-fa.md`، تصمیم‌ها در `docs/remediation-accepted-fixes-fa.md`.

علامت‌گذاری:  
- **مرده / stub** = کد یا UI هست ولی اجرا نمی‌شود یا بدنه خالی است  
- **ناقص** = بخشی کار می‌کند، بخشی نه  
- **فقط Lang** = متن/وعده بدون handler متناظر  
- **ناهماهنگ** = دو منبع حقیقت (قیمت، کلید، رفتار)

---

## ۱. تحلیل اولویت‌دار (قبل از نتیجه‌گیری)

### P0 — شکستن محصول یا crash

| ID | مورد | شواهد | اثر |
|----|------|--------|------|
| G-CH1 | `/startchallenge` بدون `CM_StartChallenge` | `StartChallengeCommand` صدا می‌زند متد غایب؛ فقط کامنت `// Challenge Game` | fatal در رانتایم |
| G-CH2 | کالکشن `challenge_game` هرگز insert نمی‌شود | فقط `countDocuments`/`findOne` در `CheckGPGameState` | حتی با handler، سشن چالش از این درخت ساخته نمی‌شود |
| G-CH3 | `/challengeforce` و deep-link `ChallengeJoin_` | فقط در Lang / URL کانفیگ؛ handler جوین چالش در کد **دیده نشد** | UI دروغین |
| G-PAY1 | `TokenPayment = ""` | `Hook.php` | درگاه donate/coin بدون API key معتبر |
| G-PAY2 | `GetChargeItem` لینک پرداخت نمی‌دهد | `var_export($result)` به کاربر | شارژ سکه از UI عملاً خراب |
| G-PAY3 | endpoint verify در workspace | redirect به onyxwerewolf.com/verify؛ فایل verify در repo **یافت نشد** | تکمیل خرید ریالی نامشخص |

### P1 — قابلیت وعده‌داده‌شده ولی خاموش/نیمه‌کاره

| ID | مورد | شواهد | اثر |
|----|------|--------|------|
| G-BET1 | `/bet` خاموش | `BetCommand` → `return false`؛ `CM_bet` کامنت | remediation: remove یکدست یا wire |
| G-BET2 | کال‌بک‌های بت زنده | `BetGame`، `bst`، `bgs_confirm`، … هنوز در Callbackquery | سطح حمله/UX دوگانه |
| G-BET3 | `BetGame/bomb` | دکمه در `CM_bet`؛ `CreateBet` فقط `hourse` | بن‌بست |
| G-FREE1 | `CM_FreeCoin` | `return false` اولین خط؛ بدنه +۱۰۰ مرده؛ Lang `FreeCoinSuccess` زنده | فرمان بی‌اثر |
| G-FREE2 | `CM_GetCoin` | همان الگو؛ +۶۰ هر ۱۰د مرده | فرمان بی‌اثر |
| G-MAG1 | جادوی اعلام نقش | `UseMajik('MajikSear')` → `return false` فوری | خرید ممکن، مصرف غیرممکن |
| G-MAG2 | Sear در Handler | `HandelMajik` بدون case `MajikSearPlayer` | حتی فعال‌سازی فرضی بی‌اثر |
| G-MAG3 | پنل reply مجیک | ساخت در `GetMajicKeybaord`؛ ارسال در Hook کامنت؛ Genericmessage مسیریابی ندارد | مسیر مرده |
| G-HERO1 | خرید قهرمان با سکه | دکمه‌های `BfdHero/all`… بدون case در `CreateHero` | فقط UI قیمت |
| G-ACH1 | `AddPlayerAchio` / `CheckPlayerAchio` | بدنه خالی | API گمراه‌کننده؛ مسیر زنده = `SavePlayerAchivment` |
| G-ACH2 | `CM_Achievement` | خواندن بدون ارسال پیام به کاربر | دستور نمایش عملاً خالی |

### P2 — باگ منطقی / ناهماهنگی قیمت و Lang

| ID | مورد | شواهد |
|----|------|--------|
| G-LAQ1 | قیمت لقب | شاپ/Lang: ۴۰ سکه؛ `ShopCheckout` برای MajiKLaqab کسر نمی‌کند؛ `SetLaqab` کسر ۳۰ |
| G-LAQ2 | همگام نام با لقب | در Hook شاخه `set_laqab`: به فیلد بولین/فلگ به‌عنوان نام ارجاع (`firstname = set_laqab`) |
| G-XP1 | متن عنوان Xp500 | دکمه «۵۰۰ اکس‌پی»؛ `ShopItemTitle_Xp500` می‌گوید ۱٬۰۰۰ |
| G-COIN1 | برچسب تومان در برابر ریال | Lang تومان؛ `GetChargeItem` مبلغ را ×۱۰ نسبت به عدد تومان می‌فرستد (سازگار با ریال درگاه) — در مستندسازی پایتون باید واحد صریح شود |
| G-FREE3 | پیام حداقل بازی FreeCoin | چک `total_game < 100` ولی متن می‌گوید «حداقل ۵۰ بازی» (کد مرده ولی ناهماهنگ) |
| G-SEND1 | سقف ۵ ارسال روزانه | منطق در کامنت؛ شمارنده `sendCoinTo` هنوز افزایش می‌یابد بدون محدودیت |
| G-SHOP1 | `ShopItem_sponser100` / `dozd_coin` | فقط Lang؛ دکمه در شاپ/coin نیست |
| G-ONLINE | `CM_OnlineGame` | متن صریح «هنوز راه‌اندازی نشده» |
| G-JOIN-COST | کسر سکه عمومی per-mode | بلوک `Coin[$Mode]` در join کاملاً کامنت؛ فقط مود `coin` سخت‌کد ۱۰. **مود `coin` = remove accepted (MF-60)** → مسیر −۱۰ جوین از scope پایتون خارج؛ جدول عمومی هنوز باز اگر بعداً برگردد |

### P3 — نقص کیفیت / ریسک نگهداری

| ID | مورد | یادداشت |
|----|------|---------|
| G-ADDCOIN | `CM_AddCoin` | شاخه‌های username/replay به smite می‌لغزند؛ API درهم |
| G-HERO2 | `des_hero_*` غیر all | `$Img` ممکن است تعریف‌نشده بماند |
| G-EMOJI | `has_emojis_old` | regex قدیمی؛ اموجی‌های پیچیده ممکن است رد شوند |
| G-MAG4 | برگشت جادو هنگام مرگ | منطق refund در HandelMajik کامنت شده؛ کلیدهای `PlayerDie` فقط Lang |
| G-TORN | تورنمنت | جوین بدون جریان پرداخت کامل در همان متد |
| G-TX | نبود ledger | اکثر updateها set مطلق؛ تراکنش Mongo فقط برای pay.ir/donate |

---

## ۲. موارد «فقط در Lang / کامنت» بدون پیاده‌سازی کامل

| موضوع | منبع متن | کد متناظر |
|--------|----------|-----------|
| استارت چالش گروهی | `StartChallengeGame`، `ChallengeStart` | متد استارت غایب |
| force چالش | متن `/challengeforce` | Command/متد **دیده نشد** |
| بت انفجار | `bet_bomb` | CreateBet پیاده نیست — **≠ نقش/مود Bomber گیم‌پلی** (آن‌ها remove جدا §۱۶) |
| اسپانسر ۱۰۰ سکه شاپ | `ShopItem_sponser100` | دکمه نیست |
| بازی آنلاین بدون گروه | `CM_OnlineGame` | صریحاً «بزودی» |
| کیبورد مجیک بدو ورود به بازی | `KeyBoardUseMajik` | بلوک Hook کامنت |
| اثر Sear ۱۰۰٪ برای احمق/جادوگر | `HelpShop` | Handler ندارد |

اگر چیزی در Lang هست و در این جدول نیست ولی در کد هم پیدا نشد، در بازنویسی با برچسب «در کد دیده نشد» نگه دارید — اختراع نکنید.

---

## ۳. ارجاع متقابل به گزارش‌های قبلی

| موضوع | `php-gaps-and-defects-fa.md` | `remediation-accepted-fixes-fa.md` |
|--------|------------------------------|-------------------------------------|
| Achio خالی | §۱۲ | §۱۱ remove/یک‌مسیره کردن |
| `/startchallenge` | §۱۵ | §۸ fix (MVP یا پاسخ کنترل‌شده — تصمیم fix) |
| `/bet` خاموش | §۱۶ | §۱۱ remove یکدست کال‌بک/فرمان |
| مود بازی `coin` | — (اقتصاد-shop §۱۰.۳) | §۱۷ remove؛ MF-60 — **نه** حذف credit/شاپ |
| BombCount / Bomber | sprint-09/05e (نه gaps هسته) | §۱۶ remove؛ MF-16/58/59 |
| محصول جانبی چالش/بت | اولویت محصول انتهای فایل gaps | سطح محصول جدول پایانی |

این سند جزئیات اقتصاد/شاپ/مجیک را عمیق‌تر می‌کند؛ تصمیم‌های پذیرفته‌شدهٔ fix/remove را عوض نمی‌کند مگر کاربر خلافش بگوید.

---

## ۴. بک‌لاگ پیشنهادی رفع (برای PHP فعلی یا پایتون)

| اولویت | کار | نتیجه مطلوب |
|--------|-----|--------------|
| P0 | پیاده‌سازی یا حذف امن `/startchallenge` + عدم throw | بدون crash |
| P0 | تعریف وضعیت چالش: یا insert کامل `challenge_game` + جوین + force، یا پاک کردن دکمه‌ها/کلیدهای Lang از مسیر کاربر | یک حقیقت |
| P0 | Token + جریان verify + واریز سکه؛ یا مخفی کردن `/coin` بسته‌ها تا آماده شدن | شارژ واقعی یا بدون وعده |
| P1 | یکدست‌سازی بت: حذف فرمان+کال‌بک+Cron یا فعال‌سازی مستند | |
| P1 | روشن کردن Sear (مصرف + اثر) یا حذف از شاپ/HelpShop | |
| P1 | حذف/deprecate FreeCoin و GetCoin یا برداشتن `return false` | |
| P1 | تکمیل خرید Hero یا حذف دکمه‌های قیمت | |
| P2 | یکسان‌سازی قیمت لقب (۳۰ در برابر ۴۰) و کسر در یک نقطه | |
| P2 | اصلاح همگام‌سازی نام با `set_laqab` | |
| P2 | اصلاح عنوان Lang Xp500 | |
| P3 | ledger تراکنش سکه؛ سقف sendcoin؛ پاکسازی stub Achio | |

---

## ۵. نتیجه‌گیری کوتاه

لایه اقتصاد در PHP **نیمه‌زنده** است: شاپ جادو/دزد/XP/اموجی، ~~مود `coin`~~ (**حذف محصولی از پایتون** — فقط مود؛ نه کل credit/شاپ)، ارتقا VIP، و اثر سه جادو (خبرچینی/روح/محافظ) کار می‌کنند. در مقابل، **چالش گروهی، شارژ ریالی تمیز، سکه رایگان، `/bet`، جادوی Sear، خرید Hero، و نمایش Achievement** یا stubاند یا عمداً خاموش یا فقط در Lang وعده داده شده‌اند. بازنویسی پایتون باید برای هر ردیف P0/P1 تصمیم صریح «پیاده / حذف از محصول» بگیرد تا parity مبهم نماند.
