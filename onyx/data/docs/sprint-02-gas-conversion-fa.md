# اسپرینت ۲ — تبدیل گاز (`BittanCheck`)

**پیش‌نیاز:** اسپرینت ۱ بسته (فلگ گاز در شب ست می‌شود)  
**هدف:** تبدیل تأخیری نقش در مرز رأی→شب + بلاک پایان بازی تا پاک شدن فلگ  
**مرجع سورس:** `HL.php` (BittanCheck / BittanPlayer / VampireConvert / CheckEndGame)، `NG.php` (WolfTeam / CheckVampire)، گیاه‌شناس در `DY`/`CM`

---

# ۱. تحلیل و استدلال

گاز همان شب نقش را عوض نمی‌کند. فقط فلگ Redis می‌گذارد تا بازیکن یک روز با نقش قبلی بازی کند (و بتواند درمان گیاه‌شناس بگیرد). تبدیل واقعی فقط در `BittanCheck` هنگام انتقال vote→night است. تا وقتی هر یک از سه فلگ باز باشد، `CheckEndGame` عمداً false برمی‌گرداند — حتی اگر تیمی غالب باشد.

اولویت تلاش گاز در حمله گرگ: افسونگر ۳۰٪ → ملکه جنگل ۱۰٪ → آلفا ۲۰٪ → خوردن. ومپایر مسیر جدا با فلگ `VampireBitten` است.

ریسک شناخته‌شده PHP: اگر `_getPlayer` خالی برگردد فلگ پاک نمی‌شود و بازی گیر می‌کند. در پایتون باید حداقل Del امن روی player-not-found انجام شود (تصمیم صریح: رفتار اصلاح‌شده مستند شود).

---

# ۲. محدوده

## داخل
- سه فلگ و setter/cleaner
- ترتیب `BittanCheck`
- فراخوانی دقیقاً در vote→night قبل از `ChangeGameStatus('night')`
- بلاک `CheckEndGame` با فلگ‌های باز
- درمان گیاه‌شناس (پاک فلگ بدون تبدیل)
- پیام‌های BittenTurned*

## خارج
- عمق کامل همه شاخه‌های CheckVampire (می‌تواند stub با همان قرارداد فلگ باشد)
- بردهای خاص (اسپرینت ۴)
- جفت‌نقش کانفیگ (اسپرینت ۳)

---

# ۳. فلگ‌ها

| فلگ | ست | نتیجه تبدیل اگر زنده |
|-----|----|----------------------|
| `EnchanterBittanPlayer` | گاز موفق افسونگر | `role_WolfGorgine` / تیم wolf + پیام `BittenTurned` |
| `BittanPlayer` | گاز آلفا یا ملکه جنگل | همان گرگینه + `BittenTurned` |
| `VampireBitten` | گاز ومپایر | `role_Vampire` / تیم vampire + `BittenTurnedVampire` |

اگر هدف قبل از تبدیل مرده: فقط Del فلگ، بدون ConvertPlayer.

پیش‌شرط‌های شانس (از اسپرینت ۱): لیست `Enchanter`، `forestQueenBitten` پس از مرگ آلفا، کلید `VampireConvert` (معمولاً ۴۰ پس از افشای اصیل).

---

# ۴. ترتیب `BittanCheck`

1. EnchanterBittanPlayer → زنده؟ Convert گرگینه + CheckPlayerEnchanter؛ مرده؟ Del  
2. BittanPlayer → زنده؟ Convert گرگینه؛ مرده؟ Del  
3. VampireBitten → زنده؟ Convert ومپایر؛ مرده؟ Del  

هر سه در یک اجرا می‌توانند پردازش شوند (گاز روی دو نفر مختلف در یک شب).

محل فراخوانی: داخل انتقال vote→night، بعد از CheckVote و پاک‌سازی‌های MastEat/Ahangar، **قبل از** ChangeGameStatus(night) و افزایش Night_no.

---

# ۵. گیاه‌شناس (روز)

اگر فلگ گاز باز و گیاه‌شناس زنده: به گازخورده پیشنهاد افشا (`UserBittenByWolf` / `UserBittenVampire`).  
تأیید مسیر BotanistOk → Del فلگ مربوطه → بدون تبدیل شب بعد.

---

# ۶. معیار پذیرش QA

- [ ] آلفا ۲۰٪ موفق → فلگ BittanPlayer → روز با نقش قبلی → بعد رأی BittenTurned + گرگینه  
- [ ] اولویت افسونگر قبل از آلفا وقتی هدف طلسم است  
- [ ] ملکه فقط پس از AlphaDead با ۱۰٪  
- [ ] ومپایر بدون کلید VampireConvert گاز تأخیری ندهد  
- [ ] مرگ قبل از تبدیل → فقط Del؛ endgame آزاد شود  
- [ ] گیاه‌شناس فلگ را پاک کند و تبدیل نشود  
- [ ] با فلگ باز، حتی غالب عددی، بازی تمام نشود  
- [ ] player-not-found فلگ را پاک کند (اصلاح نسبت به PHP)  
- [ ] NefrinShode همچنان تبدیل فوری شب باشد نه وابسته به این اسپرینت  

پس از QA → اسپرینت ۳.
