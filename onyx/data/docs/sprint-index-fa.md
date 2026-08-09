# ایندکس اسپرینت‌های بازنویسی پایتون — ورولف

نقشهٔ دستورکار هم‌ارزی با PHP. هر اسپرینت تا QA بسته‌نشود وارد بعدی نشوید.  
این پوشه فقط مستند است؛ پیاده‌سازی کد فقط با درخواست صریح جداگانه.

**نقطهٔ ورود واحد:** همین فایل. تحلیل ادغام اسناد قدیمی: [`werewolf-sprint-doc-merge-fa.md`](werewolf-sprint-doc-merge-fa.md).

| # | موضوع | سند | وضعیت سند |
|---|--------|------|-----------|
| ۰ | مرجع کلان | `werewolf-python-rewrite-master-fa.md` | آماده |
| ۱ | پایپ‌لاین شب | `sprint-01-night-pipeline-fa.md` | آماده |
| ۲ | تبدیل گاز | `sprint-02-gas-conversion-fa.md` | آماده |
| ۳ | جفت‌نقش + تبدیل اجباری | `sprint-03-role-pairs-fa.md` | آماده |
| ۴ | بردهای خاص | `sprint-04-win-conditions-fa.md` | آماده |
| ۵الف | فرقه + شکارچی + رویس/مومیایی/فرانک | `sprint-05a-cult-team-fa.md` | آماده |
| ۵ب‌ج‌د | قاتل · آتش · ومپایر | `sprint-05bcd-killer-fire-vampire-fa.md` | آماده |
| ۵ه | سیاه · جوکر · لوسیفر · ~~بمبر~~ · دینامیت · همزاد (+ دزد/خنیاگر یکتا) | `sprint-05e-special-teams-fa.md` | آماده — **بمبر/BombCount/مود Bomber: remove accepted** |
| ۵و | روستایی‌های ویژهٔ باقی‌مانده (عمق عملیاتی) | `sprint-05f-village-specials-fa.md` | آماده |
| ۶ | پیام‌ها / Lang | `sprint-06-messages-lang-fa.md` + بانک `werewolf-messages-fa-complete.md` | آماده |
| ۷ | فاز روز کامل | `sprint-07-day-pipeline-fa.md` | آماده |
| ۸ | فاز رأی / اعدام (VOTE/LYNCH) | `sprint-08-vote-lynch-fa.md` | آماده |
| ۹ | لابی جوین + توزیع نقش | `sprint-09-join-roles-fa.md` | آماده — مودهای `Bomber` و `coin` خارج از پایتون |
| ۱۰ | دستورات و کال‌بک‌ها | `sprint-10-commands-callbacks-fa.md` | آماده |
| ۱۱ | حلقه زمان‌بندی Handler/Cron | `sprint-11-handler-cron-fa.md` | آماده |
| — | ناقصی‌ها و نقص‌های PHP | `php-gaps-and-defects-fa.md` | آماده |
| — | تصمیم‌نامه مرتفع‌سازی (fix/remove پذیرفته‌شده) | `remediation-accepted-fixes-fa.md` | آماده (+ §۱۶ Bomber، §۱۷ مود coin) |
| — | بک‌لاگ acceptance — ماتریس mirror/fix/remove | `acceptance-backlog-mirror-fix-fa.md` | آماده |
| — | اقتصاد / شاپ / سکه / چالش / آرایشی (غیرگیم‌پلی هسته) | `economy-shop-challenge-fa.md` | آماده |
| — | شکاف‌ها و stubهای لایه اقتصاد/متا | `economy-gaps-and-stubs-fa.md` | آماده |
| — | کپی دستاورد + آمار پایان (پیشنهادی هیجانی) | `achievements-endstats-copy-full-fa.md` (+ نمونه‌ها) | جزئی اعمال (AchioUnlock + winner_wolf/monafeq general + کاتالوگ وب) |
| — | تغییرات محصول (ارشد رنک / سینک نقش‌ها) | `change-spec-meta-rank-role-links-fa.md` | پیشنهادی — غیرهم‌ارز PHP |
| — | تغییرات محصول (وب‌اپ: اقتصاد/پروفایل/فید + لیست رنک/سلطنت) | `change-spec-webapp-social-economy-fa.md` | §۷.۰ قفل؛ شارژ UI+قیمت ساخته می‌شود (درگاه بعد از تأیید بانک) |
| — | نقش جدید دارنشان🕯️ (فرقه) | `change-spec-role-darneshan-fa.md` | پیشنهادی — **نقش جدید — در PHP نیست**؛ `product-new`؛ جنس علامت→اعدام→تبدیل |
| — | نقش جدید بلاد مون🌕 (ومپایر) | `change-spec-role-bloodmoon-fa.md` | پیشنهادی — **نقش جدید — در PHP نیست**؛ `product-new`؛ جنس شب‌قفل سراسری (≠ دارنشان) |
| — | تحلیل ادغام werewolf↔sprint | `werewolf-sprint-doc-merge-fa.md` | آماده |
| — | UX کاربر (لابی تا پایان) | `werewolf-user-workflow-fa.md` | keep — مکمل |
| — | UX میان‌بازی و پایان | `werewolf-midgame-end-user-journey-fa.md` | keep — مکمل |

## اسناد قدیمی `werewolf-*` (وضعیت پس از ادغام)

| فایل | وضعیت |
|------|--------|
| `werewolf-python-rewrite-master-fa.md` | **keep** — مرجع کلان |
| `werewolf-messages-fa-complete.md` | **keep** — بانک متن |
| `werewolf-user-workflow-fa.md` | **keep** — UX |
| `werewolf-midgame-end-user-journey-fa.md` | **keep** — UX |
| `werewolf-logic-documentation-fa.md` | stub ارجاع → master + s01/s09/s11/s06 |
| `werewolf-day-and-lynch-documentation-fa.md` | stub ارجاع → s07 + s08 |
| `werewolf-win-conditions-fa.md` | stub ارجاع → s04 |
| `werewolf-village-roles-batch1-fa.md` | stub ارجاع → s05f (+ s05a) |
| `werewolf-enemy-special-roles-fa.md` | stub ارجاع → s05a/bcd/e/f (یکتا در s05e §۱۵) |
| `werewolf-roles-complete-reference-fa.md` | stub ارجاع → master §۸ + s01 §۱۵ + s05* |

## ترتیب کار تیم توسعه (پس از آماده بودن سند)

1. شب کامل (۱)  
2. گاز (۲)  
3. جفت‌نقش (۳)  
4. برد (۴)  
5. نقش‌ها: ۵الف → ۵ب‌ج‌د → ۵ه → ۵و  
6. پیام‌ها (۶)  
7. روز کامل (۷)  
8. رأی / اعدام (۸) — پس از نقش‌های اثرگذار بر رأی  
9. لابی / نقش‌دهی (۹)  
10. دستورات / کال‌بک (۱۰) + تصمیم‌های mirror/fix از `acceptance-backlog-mirror-fix-fa.md`  
11. حلقه زمان‌بندی Handler/Cron (۱۱) — موتور ساعت؛ الزامی یا معادل queue  

## قانون stub (برای وقتی کد نوشته شود)

در اسپرینت ۱ اسلات‌های CheckNight می‌توانند stub باشند؛ از اسپرینت ۵ به بعد هر دسته باید اسلات مربوطه را از stub به رفتار کامل برساند بدون جابه‌جا کردن ترتیب resolve.
