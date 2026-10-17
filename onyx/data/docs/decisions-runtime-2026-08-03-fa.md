# یادداشت تصمیم‌های اجرایی — ۲۰۲۶-۰۸-۰۳

منبع: `acceptance-backlog` + `remediation` + `change-spec-webapp` §۷.۰.

## جوین MF-15…22

| ID | تصمیم اجرا | یادداشت |
|----|------------|---------|
| MF-15 | **mirror** | Foolish = دقیقاً ۱ گرگ (`foolish_roles`) |
| MF-17 | **fix** | BookIn فقط `role_joker`/`role_harley` — بدون Halrly |
| MF-18 | **fix** | `role_lookup.first_key_for_role` ایندکس ۰ را None نمی‌داند |
| MF-19 | **fix** | شرط Khaen با `has_base_wolf` واضح (نه `\|\|`/`and` PHP) |
| MF-20 | **fix** | `non_vg` فقط `role_lucifer` |
| MF-21 | **fix** | `set_phase` فقط phase؛ timer جدا و معتبر |
| MF-22 | **fix** | یک پاس وزن در `role_balance`؛ بدون Monafer |

## وزن G نقش‌های جدید

| نقش | وزن | سطل |
|-----|-----|-----|
| DarNeshan | **۱۰** | ferqe |
| BeladMoon | **۷** | vampire |

آستانه‌ها: DarNeshan≥۱۱، BeladMoon≥۲۵ (قفل موقت مهندسی از change-spec).

## اقتصاد / وب

| موضوع | تصمیم |
|--------|--------|
| چالش | فقط وب؛ بات redirect |
| FreeCoin/GetCoin | remove |
| دزد | remove (PN-12) |
| شارژ ریالی | **UI + قیمت‌گذاری ساخته می‌شود** — بدون محصول کامل بانک درگاه تأیید نمی‌کند؛ کلید واقعی بعد از تأیید درگاه |
| لقب شاپ | قیمت واحد **۴۰** |
| Sear (MF-41) | **fix کامل** — خرید در وب‌اپ؛ مصرف در بازی داخل پنل مجیک |
| سیاست نیمه‌مرده‌ها | **تکمیل نه حذف** (Hero، Achievement، OnlineGame، تورنمنت، آیتم‌های شاپ، …) |
| پنل سودو | WebApp تب مدیریت + `/sudo`؛ اعطای دستی تا درگاه؛ تعمیر لجر/شارژ؛ قفل اسپانسر گروه |
| مجیک داخل بازی | پنل پس از نقش؛ mj:؛ Reveal↔Khabar / Protect↔Hil / Silence↔Ghost؛ Sear کامل؛ refund مرگ؛ فیلتر روح در شب/روز/رأی |
| شارژ کاربر | سفارش pending + sandbox-pay + **POST /api/shop/charge/verify** |
| دستاورد پایان | games_played/wins + first_win/ten_games/wolf_win/loyal_villager |
| آنلاین | صف Redis join/leave |
| چالش بات | deep-link WebApp |
| Hero/Achievement/Online/Tournament | API وب + تب‌ها + فرمان بات |
| ارشد رنک PN-01 | SessionSenior + پنل کنترل بازی (sr:) |
| RoleLink PN-02…04 | شوالیه→شاهزاده؛ خنیاگر↔دلبر |
| sendcoin | سقف ۵/روز (MF-47) |
| ledger | جدول `web_coin_ledger` |

### قفل ۲۰۲۶-۰۸-۰۵ — کاربر

1. شارژ ریالی را «نساز تا درگاه» **لغو** شد → باید ساخته شود تا بتوان درگاه گرفت.  
2. جادوی اعلام نقش حذف نمی‌شود → کامل.  
3. برای موارد وعده‌داده‌شدهٔ نیمه‌مردهٔ اقتصاد/متا: **همه را کامل کن؛ حذف نکن.**  
   (حذف‌های قبلی محصولی مثل بت / Bomber / مود coin / دزد / FreeCoin سرجایشان می‌مانند.)

## DX

MF-23 env-only؛ MF-26 `answer_safe` روی کال‌بک‌ها؛ MF-28 `get_role_user_id` → None.
