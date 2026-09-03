# اسپرینت ۶ — لایه پیام و Lang

**پیش‌نیاز:** اسپرینت ۱+ (منطق فازها)  
**هدف:** اتصال کلید→متن هم‌ارز PHP بدون هاردکد متن در موتور  
**بانک متن:** `docs/werewolf-messages-fa-complete.md` + `bot/Strong/Game_Mode/*.ini`

---

# ۱. تحلیل و استدلال

موتور PHP متن را در منطق نقش نمی‌نویسد؛ کلید می‌دهد و `Lang->_` با placeholder جایگزین می‌کند. دو نمونه رانتایم:

- **L** = `main_{userLang}` — UI خصوصی  
- **LG** = `{groupMode}_{groupLang}` — جریان بازی گروه  

Fallback: فایل جاری → `general_fa` → `main_fa` → `Translation not found! >> {key}`.

بازنویسی باید موتور را به کلید وابسته کند تا تعویض fa/en/nightclub فقط با تعویض فایل باشد.

---

# ۲. محدوده

## داخل
- بارگذاری ini مسطح  
- API ترجمه با `{0}`…`{n}`  
- دو کاتالوگ L و LG  
- فهرست کلیدهای اجباری اسپرینت ۱–۴  
- هاردکدهای مجاز (جادو، منوی استارت، تیم لوسیفر، چت خصوصی)

## خارج
- بازنویسی همه متن‌های nightclub  
- سیستم گیف/ویدیو کامل (فقط نگاشت کلید گیف کافی است)

---

# ۳. قرارداد لایه ترجمه (برای تیم پیاده‌سازی)

وقتی کد نوشته شود، موتور باید فقط با کلید کار کند:

1. بارگذاری `{mode}_{lang}.ini` به‌صورت کاتالوگ مسطح  
2. گرفتن متن با کلید + جایگزینی `{0}`…`{n}`  
3. دو کاتالوگ موازی: L برای UI کاربر، LG برای جریان گروه  
4. منطق بازی رشتهٔ خام نفرستد؛ فقط کلید (+placeholder)  
5. کلید غایب: fallback به general_fa سپس main_fa؛ در تست اختیاری fail-fast  

Placeholder PHP به شکل `{0}` است — همان را حفظ کنید.

---

# ۴. کلیدهای اجباری حداقلی موتور (اسپرینت ۱–۴)

فاز: `MassgeFortypeSummery_night/day/vote`, `SandmanNight`, `NoAttakInDay`, `endTime`, `SelectOk`, `howVote`, `killed_user`, `no_kill`, `user_role`

گرگ/گاز: `eatUserTeem`, `eat_you`, `wolfEat`, `PlayerBitten*`, `BittenTurned`, `BittenTurnedVampire`, `EnchanterPlayerBitten*`

قاتل: `AskKill`, `SerialKillerKilledYouTow`, `HunterShotChoice`

برد: `winner_*` / `win_*` طبق اسپرینت ۴، `endGame`, `winner`, `loset`

نقش: `role_*` و `role_*_n`

---

# ۵. هاردکد مجاز (کپی عین متن)

- پنل جادو و چهار دکمه خبرچینی/اعلام نقش/محافظ/روح  
- دکمه‌های منوی `/start`  
- نام تیم‌های لوسیفر  
- پیام‌های چت خصوصی تیمی (۳ سکه و …)

بقیه باید از ini بیاید.

---

# ۶. معیار پذیرش

- [ ] تعویض `general_fa` ↔ `general_en` بدون تغییر کد موتور  
- [ ] placeholder چندآرگومانی درست  
- [ ] کلید غایب fallback یا خطای تست مشخص  
- [ ] شب/رأی/برد حداقل کلیدهای بخش ۴ را استفاده کنند نه رشته خام  
- [ ] nightclub فقط با عوض کردن mode لود شود  

موازی با اسپرینت ۱–۵ قابل اجراست؛ بلاک‌کننده منطق نیست.
