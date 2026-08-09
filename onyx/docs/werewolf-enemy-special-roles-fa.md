# مستند نقش‌های دشمن / ویژه و نقش‌های روستایی باقی‌مانده (Onyx Werewolf)

**منبع تحلیل:** سورس PHP در `E:\Project\onyx\html` (به‌ویژه `NG.php`، `DY.php`، `CM.php`، `HL.php`، `VT.php`، `SE.php`، `join.php`)  
**هدف:** مرجع کامل برای بازنویسی پایتون  
**محدودیت‌ها:** بدون قطعه کد؛ بدون خواندن `bot\Strong\Game_Mode`؛ متن فارسی؛ کلید پیام‌ها به‌جای متن ini

---

# ۱. استدلال کلی و نقشهٔ اجرا

## ۱.۱ ترتیب واقعی حل شب (`CheckNight`)

انتخاب‌های شب فقط در Redis ذخیره می‌شوند. اثر اصلی در پایان تایمر شب با ترتیب ثابت زیر اعمال می‌شود:

1. مرگ تأخیری ملکه جنگل (`DeadforestQueen`) در صورت هم‌شب بودن  
2. جوکر (`CheckJoker`)  
3. هارلی (`CheckHarly`)  
4. شوالیه (`CheckKnight`)  
5. تیم گرگ (`WolfTeam`)  
6. توله / دوباره‌باز شدن گرگ (`CheckBetaWolf` + `WolfCubeDead`)  
7. ببر (`CheckBabr`)  
8. گرگ یخی (`CheckIceWolf`)  
9. قاتل سریالی (`GetKiller`) — اگر شلیک مرگ کلانتر باز شود، ادامه شب قطع می‌شود  
10. شیمیدان (`CheckChemist`)  
11. بمب‌گذار (`CheckBomber`)  
12. آتش‌نشان / سوزاندن لیست (`CheckFireFighter`)  
13. مگنتو (`MagentoTeam`)  
14. کماندار (`CheckArcher`)  
15. چیانگ (`CheckChiang`)  
16. تیم خون‌آشام (`CheckVampire`)  
17. شکارچی فرقه (`GetCultHunter`)  
18. فرقه (`CheckCult`)  
19. انتخاب تیم لوسیفر شب صفر (`CheckLuciferTeam`)  
20. عروس مردگان (`CheckBrideTheDead`)  
21. فرشته نگهبان (`GetAngel`)  
22. ملکه یخ (`CheckIceQueean`)  
23. لیلیس (`CheckLilis`)  
24. عجوزه (`CheckHoney`)  
25. کنت ومپایر استعلام شب (`Checkkent`)  
26. فرانکشتاین (`GetFranc`)  
27. افسونگر (`CheckEnchanter`)  
28. فاحشه (`GetFaheshe`)  
29. گاو (`CheckCow`)  
30. هانتسمن (`CheckHuntsman`)  
31. روح (`GetGhost`)  
32. موش (`CheckMouse`)  
33. گرگ سفید (`GetWhiteWolf`)  
34. فالگیر (`CheckAugur`)  
35. پیشگو (`GetSearSee`)  
36. احمق گروهی (`GetAhmaqSeeGroup`)  
37. ققنوس (`CheckPhoenix`)  
38. دزد (`CheckDozd`)  
39. نگاتیو (`GetNegativ`)  
40. جادوگر گرگ (`GetJado`)  
41. دینامیت (`GetDinamit`)  
42. هندوانه (`Watermelon`)  
43. خنیاگر پاک‌سازی فلگ (`CheckKhenyager`)  
44. انتخاب ویژه مرگ رویس در همان شب

نکته معماری مهم: فریب/جایگزینی اکشن لوسیفر (`CheckLucifer`) در شروع فاز شب (`NG::Handel`) اجرا می‌شود، نه داخل `CheckNight`. انتخاب تیم لوسیفر فقط شب صفر داخل `CheckNight` است.

## ۱.۲ ترتیب حل روز (`CheckDay`)

1. تفنگدار  
2. شوالیه سیاه (`CheckBlackKnight`) — قتل روز  
3. دینامیت روز  
4. کارآگاه  
5. جاسوس  
6. شاهدخت  
7. دیان  
8. کنت ومپایر در حالت تبدیل (`CheckKent`)

## ۱.۳ تیم‌ها از `SE::GetRoleTeam`

| تیم برگشتی | نقش‌ها |
|------------|--------|
| `ferqeTeem` | `role_ferqe`, `role_Royce`, `role_Mummy`, `role_franc` |
| `qatel` | `role_Qatel`, `role_Archer`, `role_davina` |
| `Firefighter` | `role_Firefighter`, `role_IceQueen`, `role_Lilis`, `role_Magento` |
| `vampire` | `role_Vampire`, `role_Bloodthirsty`, `role_Chiang`, `role_kentvampire` |
| `black` | `role_BlackKnight`, `role_BrideTheDead`, `role_dian` |
| `monafeq` / `lucifer` / `joker` / `Bomber` / `hamzad` / `dinamit` / `dozd` / `khenyager` | هر کدام تیم تکی خود |
| `rosta` | نقش‌های روستایی باقی‌ماندهٔ این سند |

هشدار: `HL::PlayerByTeam` برای رأی/اکشن تیمی با `GetRoleTeam` یکی نیست. مثلاً فرانک در لیست رأی فرقه نیست؛ مگنتو آرایهٔ جداگانه `magento` دارد؛ خون‌آشام/کنت/اصیل فقط با فلگ فعال وارد آرایهٔ vampire می‌شوند.

## ۱.۴ سیستم‌های عرضی که باید اول فهمیده شوند

### تبدیل فرقه
- رأی تیمی یا انتخاب تکی → هدف در `UserInHome` برای بازدیدکننده ثبت می‌شود.  
- `CultAttemp` احتمال تبدیل را بر اساس نقش هدف می‌دهد؛ فلگ `ConvertCult` (پس از مرگ رویس با مومیایی زنده) ۲۰٪ به شانس تبدیل می‌افزاید و از شانس مرگ بازدیدکننده در چند شاخه کم می‌کند.  
- موفقیت = `ConvertPlayer(..., role_ferqe)` فوری در همان شب + پیام `CultConvertYou` / `CultJoin`.  
- شکست = پیام تلاش `CultAttempt` به هدف و `CultVisitAttemp*` به تیم.  
- خانه خالی (`UserInHome` هدف) = بازدید بی‌اثر.  
- قاتل / گرگ پایه / شکارچی / خون‌آشام فعال معمولاً بازدیدکننده را می‌کشند یا تبدیل می‌کنند، نه هدف را.

### مسیر قتل قاتل در برابر محافظ‌ها
ترتیب تقریبی در `GetKiller`: تله هانتسمن → زندان شاهدخت → شفای جادویی → شفای ققنوس → شاخه‌های نقش (معشوقه/شوالیه سیاه/جوکر) → محافظ فرانک → محافظ مومیایی → محافظ گرگ سفید → فرشته (برای غیرگرگ) → ضدحمله لیلیس ۶۰٪ → اصیل مخفی = خانه خالی → قتل عادی + کشتن ناتاشای هم‌خانه.

### گاز خون‌آشام
- تیم vampire رأی/انتخاب مشترک دارد.  
- فلگ `VampireConvert` شانس گاز (تبدیل تأخیری) است؛ `VampireBitten` شب بعد در `BittanCheck` به `role_Vampire` تبدیل می‌شود.  
- بدون موفقیت گاز: شانس `VampireChangeNotKill` (۵۰) برای فرار؛ وگرنه قتل.  
- با اصیل آزاد (`Bloodthirsty` فعال) شکست گاز معمولاً به قتل قطعی می‌انجامد.  
- دیدن کلانتر برای اولین بار اصیل را آزاد می‌کند و شانس گاز را از `BVampireChangeConvet` (۴۰) ست می‌کند.

### سوزاندن لیست آتش‌نشان
- هر شب غیرسوزاندن یک نفر به `FirefighterList` اضافه می‌شود.  
- دکمهٔ سوزاندن (`FirefighterOk`) فقط وقتی `Day_no > 1` و لیست خالی نیست فعال است.  
- با `FirefighterOk` در حل شب همهٔ زنده‌های لیست می‌سوزند (با محافظ‌ها)، و بازدیدکنندگان خانه‌شان هم با `CheckInHomePlayer` می‌میرند.  
- شب اول روز (`Day_no == 1`) حل سوزاندن کلاً رد می‌شود.

### کتاب‌های جوکر
- در شروع بازی تا ۷ بازیکن غیرجوکر/هارلی `BookIn` می‌گیرند.  
- جوکر/هارلی هر شب هدف را برای کتاب چک می‌کنند؛ پیدا کردن `FindedBook` را زیاد می‌کند.  
- برد جوکر وقتی `FindedBook >= 3` یا بازیکنان زنده ≤ ۳ و جوکر/هارلی زنده باشند.  
- مرگ صاحب کتاب → کتاب تصادفی به بازیکن دیگر منتقل می‌شود (`RandomBookChange`).  
- اگر هارلی زنده نباشد، جوکر روی دشمنان خاص مستقیماً می‌کشد.

### فریب لوسیفر
- شب صفر: انتخاب تیم هم‌راستا (`ChangeLuciferTeam`).  
- از شب ۱ به بعد در شروع شب: هدف را فریب می‌دهد — یا اکشن شب او را می‌دزدد (`DodgeNightSelect`)، یا رأی فردا را می‌دزدد (`DodgeVote`)، یا اکشن روز را (`DodgeDay`).  
- دیدن قاتل/گرگ/اصیل فعال می‌تواند خود لوسیفر را بکشد (شانس‌های `Dodge*Dead`).

### کاشت بمب
- چهار قطعه تصادفی به چهار بازیکن (`BomberGet`) داده می‌شود: timer / Gunpowder / Chassis / Wicks.  
- بمب‌گذار(ها) شب هدف را انتخاب می‌کنند؛ در `CheckBomber` پیام کاشت می‌رود و `BombPlanted` زیاد می‌شود.  
- برد مود بمب‌گذار: کاشته‌ها ≥ سقف، یا تعداد بمب‌گذار ≥ روستا.  
- دینامیت قطعات را پیدا می‌کند؛ ۳ پیدا = برد دینامیت.

### همزاد هنگام مرگ الگو
- همزاد شب اول الگو را در `GamePl:Hamzad` ذخیره می‌کند.  
- وقتی همان user_id بمیرد، `ConvertHamzad` نقش الگو را به همزاد می‌دهد (با پیام‌های تیم‌محور برای گرگ/فرقه/قاتل/کماندار/…).  
- اگر خود همزاد بمیرد قبل از تبدیل، فلگ پاک می‌شود.

---

# ۲. تیم فرقه (`ferqeTeem`)

## ۲.۱ `role_ferqe` — فرقه‌گرا

### Reasoning
نقش پایهٔ رشد عددی فرقه؛ قدرت از تبدیل شبانه است نه از قتل مستقیم. باید در برابر شکارچی آسیب‌پذیر باشد تا بالانس روستا حفظ شود.

### شناسنامه
- تیم: `ferqeTeem`  
- نوع: تبدیل‌گر تیمی / شب  
- اولویت شب: بعد از شکارچی فرقه، داخل `CheckCult`  
- رأی شب: تیمی (`Selected:Cult:*`) وقتی بیش از یک عضو فرقه در `PlayerByTeam` باشد

### Workflow
1. شب: کیبورد انتخاب هدف.  
2. `CheckCult`: تجمیع رأی → بازدید → شاخه نقش هدف.  
3. موفقیت تبدیل فوری به `role_ferqe`.  
4. مرگ: `CheckMummy(..., kill)` برای باف مومیایی.

### State
- `GamePl:Selected:*` / `GamePl:Selected:Cult:*`  
- `GamePl:UserInHome:{بازدیدکننده}`  
- `GamePl:ConvertCult` (باف سراسری)  
- `GamePl:RoyceDead` / `RoyceSelectd2` برای شب ویژه رویس

### Message keys
`CultConvertYou`, `CultJoin`, `CultAttempt`, `CultVisitAttemp`, `CultVisitAttempOne`, `CultVisitEmpty`, `CultVisitEmptyOne`, `CultVisitDead`, `CultVisitDeadOne`, `CultConvertKillerPublic*`, `CultConvertWolfPublic`, `CultConvertHunter`, `CultConvertCultHunter`, `HunterKilledCultistOn`, `HunterFindCultist`, `HunterKilledCultist`, `role_ferqe`, `role_ferqe_n`

### Edge cases
- خانه خالی هدف = شکست بی‌مرگ.  
- شکارچی همیشه بازدیدکننده را می‌کشد.  
- قاتل: شانس مرگ بازدیدکننده ۵۰٪ منهای باف مومیایی؛ وگرنه اگر خانه پر باشد باز هم مرگ بازدیدکننده در شاخه فعلی.  
- عاشق فرقه (`SweetheartLove:team == Cult`) تبدیل قطعی.  
- همزاد از فرقه تبدیل‌ناپذیر است (`CultAttemp` صفر).  
- فرانک در رأی تیمی `PlayerByTeam` فرقه نیست.

---

## ۲.۲ `role_Royce` — رئیس فرقه

### Reasoning
رهبر فرقه؛ مرگش باید به فرقه فرصت رشد اضطراری بدهد (شب بعد انتخاب ویژه + باف مومیایی).

### شناسنامه
- تیم: `ferqeTeem`  
- نوع: رهبر / تبدیل‌گر  
- اولویت: همان `CheckCult`؛ پس از مرگ فلگ `RoyceDead = Night_no+1`

### Workflow
- شب مثل فرقه رأی/انتخاب می‌کند.  
- مرگ (غیر afk): پیام `RoyceDead` به تیم؛ شب بعد `RoyceDeadSelect`.  
- مرگ: `CheckMummy(..., royce)` → `ConvertCult=20`.

### State
`GamePl:RoyceDead`, `GamePl:RoyceSelectd2`, `GamePl:ConvertCult`

### Message keys
`RoyceDead`, `AfterDieRoyce`, به‌علاوه کلیدهای مشترک فرقه

### Edge cases
- afk رویس فلگ شب ویژه نمی‌سازد.  
- باف `ConvertCult` فقط یک‌بار از مسیر مومیایی رویس ست می‌شود.

---

## ۲.۳ `role_Mummy` — مومیایی

### Reasoning
محافظ فرقه + بافر پس از تلفات. محافظتش شبیه فرشته است ولی کلید جدا (`role_Mummy:AngelIn`) دارد و در حملهٔ شکارچی به فرقهٔ محافظت‌شده خودش هم می‌میرد.

### شناسنامه
- تیم: `ferqeTeem`  
- نوع: دفاع شب  
- در `PlayerByTeam` فرقه هست (رأی تبدیل)  
- `GetMummy` بیشتر پیام «حمله نخورد» می‌دهد؛ محافظت در لحظهٔ انتخاب CM ست می‌شود

### Workflow
1. شب هدف را انتخاب می‌کند → `role_Mummy:AngelIn:{هدف}` و نام ذخیره‌شده.  
2. حملات قاتل/کماندار/خون‌آشام/یخ‌گرگ و… اگر کلید باشد بلاک می‌شوند.  
3. اگر شکارچی فرقه‌ای را بکشد که مومیایی روی اوست، مومیایی هم می‌میرد.  
4. مرگ اولین فرقه‌گرا → `DieCult` + پیام به مومیایی.  
5. مرگ رویس → `ConvertCult=20`.

### State
`GamePl:role_Mummy:AngelIn:*`, `AngelNameSaved`, `AngelSaved`, `DieCult`, `ConvertCult`

### Message keys
`MummyAngel`, `MummyAngelPlayerMessage`, `MummyAngelMummyMessage`, `MummyAngelOne`, `MummyAngelTeam`, `MummyMessageWhenKillCult`, `MummyCultHunterMessage`, `MummyCultHunterKill`, `MummyCultHunterKillGroupMessage`, `AfterDieRoyce`

### Edge cases
- `DieCult` جلوی تکرار پیام مرگ فرقه را می‌گیرد.  
- `ConvertCult` جلوی تکرار باف رویس را می‌گیرد.  
- مومیایی مرده باف نمی‌دهد.

---

## ۲.۴ `role_franc` — فرانکشتاین

### Reasoning
عضو تیم فرقه از نظر `GetRoleTeam`، اما جدا از رأی تبدیل؛ اول محافظ است، وقتی هیچ فرقه‌ای در `PlayerByTeam` نماند به قاتل شبانه تبدیل می‌شود.

### شناسنامه
- تیم: `ferqeTeem`  
- نوع: دفاع → تهاجم مشروط  
- اولویت حل: `GetFranc` بعد از لیلیس/عجوژه/کنت

### Workflow
- حالت عادی: انتخاب هدف = محافظ (`role_franc:AngelIn`) مثل فرشتهٔ فرقه.  
- وقتی آخرین عضو فرقه (`ferqe` در PlayerByTeam) مرد: `CheckFranc` → `FrancNightOk` + یک شب بدون اکشن (`NotSend`).  
- با `FrancNightOk`: انتخاب شب = قتل مستقیم هدف.

### State
`GamePl:role_franc:AngelIn:*`, `AngelNameSaved`, `AngelSaved`, `FrancNightOk`, `UserInHome` برای فرانک

### Message keys
`NotAttackFeranc`, `FrancKillGroupMessage`, `FrancKillPlayerMessage`, `FrancDeadCult`, `PlayerMessageFrancS`, `VampireCult`, `IceAttackCult`, `FireAttackCult`, `ArcherCult`, `KillerICult`, `WolfAttackCult`, `FrancGourd*`, `CultHunterFrancMessage`, `CultHunterKillByFrancGroup`, `CultHunterKillFrancMessage`, `CultHunterKillFrancGroup`

### Edge cases
- شکارچی روی فرانک: ۱۰٪ فرانک شکارچی را می‌کشد، وگرنه شکارچی فرانک را.  
- محافظ فرانک بسیاری از حملات تیم‌ها را بلاک می‌کند.  
- کلیدهای فرانک پایان هر `CheckNight` پاک می‌شوند.

---

# ۳. تیم قاتل (`qatel`)

## ۳.۱ `role_Qatel` — قاتل سریالی

### Reasoning
تهدید شبانهٔ مستقل از گرگ؛ باید تقریباً همه‌چیز را بکشد ولی در برابر شوالیه سیاه، لیلیس، محافظ‌ها و جوکر+هارلی آسیب‌پذیر بماند.

### شناسنامه
- تیم: `qatel`  
- نوع: تهاجمی شب  
- اولویت: بعد از گرگ‌ها، قبل از شیمیدان  
- وزن بالانس بالا (نزدیک نقش‌های قوی)

### Workflow
شب هدف → `GetKiller` با زنجیرهٔ محافظ/ضد → مرگ با پیام گروهی `MesssageQatel` و PV `SerialKillerKilledYouTow`.

### State
`GamePl:Selected:{قاتل}`, تعامل با `HunterKill` اگر هدف کلانتر باشد

### Message keys
`SerialKillerKilledYouTow`, پیام‌های `MesssageQatel`، `GuardBlockedKiller`, `GuardSavedYou`, `NotInHomeEat`, `MsgPlayerSKLoved`, `BlackKnightKillKillerMessage*`, `LilisMessageGourdKiller`, `LilisMessageKiller`, `VampireDeadByKiller*`, `SerialKillerKilledCH`, `ChemistVisitYouSK`, `ChemistSK`, `ChemistSKPublic`, `LuciferDodgeQatelGroupMessage`, `KillerMessageWhenAttack`

### Edge cases
- شوالیه سیاه: عملاً همیشه قاتل می‌میرد (`R(100) < 100`).  
- اصیل قبل از کشف = «خانه خالی».  
- عاشق قاتل: قتل؛ وگرنه عشق اجباری.  
- بازدید فرقه/خون‌آشام از خانه قاتل کشنده است.  
- مرگ قاتل `CheckHilda` را صدا می‌زند.  
- همزاد از قاتل نقش + اطلاع کماندار می‌گیرد.

---

## ۳.۲ `role_Archer` — کماندار

### Reasoning
بازوی دوم تیم قاتل؛ تیر شبانه با کولداون (`ArcherSendFor`)؛ برای شرط برد قاتل وقتی تعداد برابر است مهم است.

### شناسنامه
- تیم: `qatel`  
- نوع: تهاجمی شب با محدودیت زمانی  
- اولویت: بعد از مگنتو

### Workflow
انتخاب شب → `CheckArcher`: ققنوس/مجیک → عاشق → لیلیس ۶۰٪ ضد → فرانک/مومیایی/گرگ سفید → قتل.

### State
`GamePl:ArcherSendFor`, `GamePl:Selected:{کماندار}`

### Message keys
`ArcherDeadPlayer`, `ArcherDeadPlayerGroupMessage`, `ArcherDeadPlayerMessage`, `MsgPlayerACLoved`, `LilisMessageGourdArcher`, `LilisMessageArcher`, `FrancGourdArcherMessage`, `WhiteWolfGourdArcher*`, `MessageForArcher`, `KnightKillPlayer*` (تعامل متقابل)

### Edge cases
- شرط برد قاتل: اگر قاتل+کماندار زنده و تعداد تیم قاتل ≥ بقیه، و `ArcherSendFor == Night_no+1` باشد، قاتل می‌برد.  
- لوسیفر اگر کماندار هنوز تیر آینده دارد، رأی او را می‌دزدد وگرنه اکشن شب.

---

## ۳.۳ `role_davina` — داوینا

### Reasoning
نقش روز تیم قاتل؛ یک‌بار می‌تواند روز بعد را کوتاه/قفل کند تا فشار رأی کم شود.

### شناسنامه
- تیم: `qatel`  
- نوع: اخلال روز (یک‌بار)  
- اولویت: کیبورد روز در `DY`؛ اثر فوری در CM نه در CheckDay

### Workflow
روز: دکمه بله/خیر → بله: `DavinaOkUse`, `DavinaOk = Day_no+1`, `NotSendDay`, پیام گروهی؛ روز بعد تایمر/قفل طبق Handler.

### State
`GamePl:DavinaOkUse`, `DavinaOk`, `DavinaOk_in`, `NotSendDay`, `role_davina:notSend`

### Message keys
`AskDavina`, `DavinaYes`, `DavinaNo`, `DavinaGroupMessage`

### Edge cases
- فقط یک‌بار.  
- خارج از فاز day رد می‌شود.  
- در تنظیمات نقش وابسته به قاتل است (اگر قاتل off باشد داوینا هم حذف/همگام می‌شود).

---

# ۴. تیم آتش‌نشان (`Firefighter`)

## ۴.۱ `role_Firefighter` — آتش‌نشان / پادشاه آتش

### Reasoning
تهدید تأخیری: چند شب لیست می‌سازد، بعد یک‌جا می‌سوزاند؛ باید بعد از روز اول فعال شود تا استارت بازی منفجر نشود.

### شناسنامه
- تیم: `Firefighter`  
- نوع: تهاجمی تأخیری شب  
- اولویت: بعد از بمب‌گذار

### Workflow
- هر شب: افزودن یک نفر به `FirefighterList` + پیام `FireFighterOk`.  
- تأیید سوزاندن (`FighterFight` / `FirefighterOk`) وقتی `Day_no > 1`.  
- حل شب با فلگ: حلقه روی لیست → مجیک/گرگ‌سفید/فرشته/فرانک بلاک → مرگ + سوزاندن بازدیدکنندگان خانه.

### State
`GamePl:FirefighterList`, `FirefighterOk`, `Selected` آتش‌نشان

### Message keys
`FireFighterOk`, `ButtenFireFighter`, `FireFighterMessageForPlayer`, `FireFighterKillPlayerGroupMessage`, `FireFighterKillPlayerGroupMessageK`, `FireFighterPlayerInHomeDead`, `FireFighterPKIP`, `AngelInHomeForFireFighter`, `WhiteWolfGourdFireFighter`, `FireAttackMessage`, `FireAttackCult`, `KillAllTeamLilis` (غیرمستقیم)

### Edge cases
- اگر لیست ≥ ۳ نفر، پیام گروهی تجمیعی `...MessageK` است.  
- مجیک‌هیل روی یکی از لیست کل سوزاندن را `return false` می‌کند (حلقه قطع).  
- مرگ هم‌زمان آتش و یخ → لیلیس حالت کشتار آزاد (`DieFireAndIc`) می‌گیرد.

---

## ۴.۲ `role_IceQueen` — ملکه یخ

### Reasoning
کنترل تمپو: یک شب فریز (`NotSend` روز بعد)، شب دوم روی همان نفر = مرگ.

### شناسنامه
- تیم: `Firefighter`  
- نوع: کنترل/کشتن تأخیری  
- اولویت: بعد از فرشته

### Workflow
هدف زنده → بلاک محافظ‌ها → اگر قبلاً `IceQueenIced:{id}` دارد بمیرد → وگرنه یخ زدن + `NotSend = Night_no+1`.

### State
`GamePl:IceQueenIced`, `IceQueenIced:{user}`, `NotSend:{user}`؛ مرگ ملکه همه کلیدهای یخ را پاک می‌کند

### Message keys
`IceQueenIcDPlayer`, `IceQueenIcDPlayerOk`, `IceQueanDeadPlayer`, `IceQueenDeadPlayerTowNight`, `IceQueenDeadPlayerGroupMsg`, `IceQueenIcDPlayerInAngel`, `IceQueenIcDPlayerAngelMessagePL`, `IceQueenIcDPlayerAngelMessageANG`, `WhiteWolfGourdIceQueen*`, `IceAttackMessage`, `IceAttackCult`

### Edge cases
- لوسیفر روی ملکه یخ اکشن شب را می‌دزدد.  
- فرقه او را تبدیل نمی‌کند (`CultAttemp` صفر).

---

## ۴.۳ `role_Lilis` — لیلیس

### Reasoning
شکارچی لوسیفر داخل تیم آتش؛ وقتی آتش و یخ هر دو مرده باشند به قاتل آزاد تبدیل می‌شود؛ در دفاع ۶۰٪ مهاجم را می‌کشد.

### شناسنامه
- تیم: `Firefighter`  
- نوع: اطلاعاتی/ضد لوسیفر + ضدحمله  
- اولویت: بعد از ملکه یخ

### Workflow
- عادی: اگر هدف لوسیفر باشد می‌کشد (`FindLucifer*`)؛ وگرنه `NotFindLucifer`.  
- با `DieFireAndIc`: هر هدفی را می‌کشد.  
- در مسیرهای قاتل/کماندار/شوالیه/خون‌آشام: ۶۰٪ ضدحمله.

### State
`GamePl:DieFireAndIc`, `Selected` لیلیس

### Message keys
`FindLuciferMessage`, `YouFindLucifer`, `FindLuciferGroupMessage`, `NotFindLucifer`, `LilisKillPlayerGroupMessage`, `KillAllTeamLilis`, `LilisMessageGourd*`, `LilisMessageVampire*`, `LiLisKillPlayerInGurd`

### Edge cases
- پیدا کردن لوسیفر هم PV به لوسیفر می‌دهد هم گروه.

---

## ۴.۴ `role_Magento` — مگنتو

### Reasoning
بازو/آلودهٔ تیم آتش با مکانیک شبیه گرگ ولی تیم جدا: ۵۰٪ تبدیل به مگنتو، وگرنه قتل (مگر فرشته).

### شناسنامه
- تیم `GetRoleTeam`: `Firefighter`  
- آرایه عملیاتی: `PlayerByTeam['magento']`  
- نوع: تبدیل/قتل تیمی شب  
- اولویت: `MagentoTeam` بعد از آتش‌نشان

### Workflow
رأی تیمی `Selected:Magento:*` یا انتخاب تکی → تله/مجیک/ققنوس/فرانک/زندان → ۵۰٪ `ConvertPlayer(..., role_Magento)` وگرنه مرگ.

### State
`GamePl:Selected:Magento:*`, `UserInHome` برای آخرین رأی‌دهنده

### Message keys
`MagentoConvertPlayer`, `MagentoSuccess`, `MagentoSuccessTeam`, `MagentoDeadPlayer`, `DeadMsgPlayer`, `is_angelNagento`, `HarlotNotHome*`, `PrincessPrisonerWolfAttack` (کلید مشترک زندان), `MessageForWolfTeam` (ققنوس)

### Edge cases
- فقط `role_Magento` در آرایه magento است؛ آتش/یخ/لیلیس در رأی مگنتو نیستند.  
- همزاد می‌تواند آتش/یخ شود ولی شاخه ویژه مگنتو در ConvertHamzad جدا نیست (default).

---

# ۵. تیم خون‌آشام (`vampire`)

## ۵.۱ `role_Vampire` — خون‌آشام

### Reasoning
رشد تأخیری از طریق گاز؛ در تعادل با اصیل مخفی و کشف کلانتر طراحی شده.

### شناسنامه
- تیم: `vampire`  
- نوع: گاز/قتل تیمی شب  
- اولویت: `CheckVampire` بعد از چیانگ

### Workflow
انتخاب/رأی تیمی → مجیک → ققنوس → فرانک → سوئیچ نقش هدف → گاز (`VampireConvert` شانس) یا قتل یا فرار.

### State
`GamePl:VampireConvert`, `VampireBitten`, `VampireFinded`, `Bloodthirsty`, `Selected` / رأی تیم

### Message keys
`VampireConvertUser`, `VampireConvert`, `VampireConvertTeam`, `VampireConvertByBlood`, `VampireKillPlayer`, `VampireMessageNoKill*`, `eat_Vampire`, `VampireDeadByKiller*`, `VampireDeadWolf*`, `VampireDeadCH*`, `FindeVampire*`, `BittenTurnedVampire`, `MessageForVampire`, `MassageAttack`

### Edge cases
- گاز فقط لیست می‌کند؛ تبدیل واقعی بین رأی و شب بعد در `BittanCheck`.  
- روح (`qhost`) با حمله کشف می‌شود (`GostFinded`).  
- گرگ پایه: ۵۰٪ مرگ مهاجم، وگرنه عدم قتل.  
- شکارچی مهاجم را می‌کشد.

---

## ۵.۲ `role_Bloodthirsty` — اصیل / تشنه خون

### Reasoning
تا کشف مخفی است؛ پس از دیدن کلانتر وارد تیم عملیاتی می‌شود و گاز را تقویت می‌کند.

### شناسنامه
- تیم GetRoleTeam: `vampire`  
- در PlayerByTeam فقط اگر `GamePl:Bloodthirsty` ست باشد  
- نوع: مخفی → فعال

### Workflow
- قبل کشف: حمله به او اغلب «خانه خالی» است؛ فرشته ممکن است تبدیل/کشته شود فقط بعد `VampireFinded`.  
- کشف با حمله به کلانتر یا مرگ کلانتر قبل کشف.  
- مرگ اصیل: `DeadBloodthirsty`, `VampireConvert=20`, پاک کردن Bloodthirsty/VampireFinded، اطلاع چیانگ.

### State
`Bloodthirsty`, `BloodthirstyInGame`, `VampireFinded`, `DeadBloodthirsty`, `VampireConvert`

### Message keys
`FindVampireMessage*`, `FindeVampireBldMessage`, `DeadBldBeforeFinde`, `VampireDeadHunterBeforeFinde*`, `VampireMessageCultConvert`, `BloodthirstyCultMessageConvert`, `PlayerMessageConvertToVampire`, `bloodConvertFereshte`, `BloodKillAngel*`

### Edge cases
- دیدن خود اصیل توسط تیم = لو دادن نام کلانتر به تیم.  
- لوسیفر روی اصیل فعال شانس مرگ ۵۰٪ دارد؛ غیرفعال = دزدی رأی.

---

## ۵.۳ `role_kentvampire` — کنت ومپایر

### Reasoning
پشتیبان اطلاعاتی؛ وقتی همه vampireهای عملیاتی مردند به قاتل روز تبدیل می‌شود.

### شناسنامه
- تیم: `vampire`  
- در PlayerByTeam فقط با `KentVampireConvert`  
- شب: استعلام نقش‌های خاص؛ روز بعد از تبدیل: قتل

### Workflow
- شب `Checkkent`: اگر هدف در لیست نقش‌های مهم باشد `KentVampireFind` وگرنه `KentVampireNoFind`.  
- وقتی تیم vampire خالی شود: `CheckKentVampire` → فلگ تبدیل + پیام.  
- روز با فلگ: `CheckKent` قتل.

### State
`KentVampireConvert`, `Selected` کنت

### Message keys
`KentVampireFind`, `KentVampireNoFind`, `KentVampireKillAllVampire`, `AskDayKentVampire`, `KentVampireKillPlayer`

### Edge cases
- لوسیفر: اگر فلگ تبدیل باشد دزدی روز؛ وگرنه دزدی شب.

---

## ۵.۴ `role_Chiang` — چیانگ

### Reasoning
چشم تیم بعد از مرگ اصیل؛ هر شب یک دشمن تصادفی را نشان می‌دهد.

### شناسنامه
- تیم: `vampire`  
- در PlayerByTeam فقط بعد `DeadBloodthirsty`  
- اولویت: `CheckChiang` قبل از گاز تیم؛ اگر DeadBloodthirsty نباشد تابع زودبازده false است

### Workflow
`GetRoleEnemyVampire` → پیام موفقیت/شکست؛ در مرگ اصیل `CheckChiang` نام تیم را هم می‌دهد.

### State
وابسته به `DeadBloodthirsty`

### Message keys
`SendChiangSuccess`, `SendChiangFiled`, `ChiangDeadBlod`, `ChiangDeadBlodVampireGroup`

### Edge cases
- تنها بازمانده بودن چیانگ در پایان ۱ نفره = تساوی/هیچ (`nothing`) مثل منافق.

---

# ۶. تیم سیاه (`black`)

## ۶.۱ `role_BlackKnight` — شوالیه سیاه

### Reasoning
تیم سه‌نفره با ایمنی رأی محدود و قتل روز؛ ضد حملهٔ شب برای قاتل/شوالیه/خون‌آشام.

### شناسنامه
- تیم: `black`  
- نوع: دفاع رأی + قتل روز + ضدحمله شب  
- شروع: `BlackVoteNo = 2`

### Workflow
- رأی اعدام روی او با `BlackVoteNo > 0`: نمی‌میرد، شمارنده کم می‌شود، پیام `BlackKnightKillVote`.  
- روز: انتخاب هدف → `CheckBlackKnight` قتل.  
- شب وقتی هدف قاتل/شوالیه باشد مهاجم می‌میرد؛ در برابر vampire ۵۰٪.

### State
`BlackVoteNo`, `Selected` روز، `role_BlackKnight:InGame`

### Message keys
`BlackKnightAsk`, `BlackKnightDeadPlayerGroup`, `BlackKnightDeadPlayerMessage`, `BlackKnightKillVote`, `BlackKnightKillKillerMessage*`, `BlackKnightKillKnightMessage*`, `BlackKnightKillVampireMessage*`

### Edge cases
- مرگ او عروس مردگان زنده را هم می‌کشد.  
- در ۲ نفره اگر کسی از تیم black باشد، غیرblack کشته و black می‌برد.

---

## ۶.۲ `role_BrideTheDead` — عروس مردگان

### Reasoning
بازو قتل شب تیم سیاه؛ وابسته به زنده بودن شوالیه سیاه.

### شناسنامه
- تیم: `black`  
- نوع: قتل شب  
- اولویت: خیلی دیر در شب (`CheckBrideTheDead`)

### Workflow
انتخاب شب → اگر هدف زنده → پیام گروهی با نقش + مرگ. خنیاگر هدف را رندوم می‌کند.

### State
`Selected`, `role_BrideTheDead:InGame`

### Message keys
`BrideTheDeadKillPlayerGroup`, `BrideTheDeadKillPlayer`, `BrideTheDeadBlackDie`, `PlayerDead`

### Edge cases
- با مرگ شوالیه سیاه، عروس هم می‌میرد حتی اگر آن شب اکشن داشته باشد.

---

## ۶.۳ `role_dian` — دیان

### Reasoning
اطلاعات/نشان‌گذاری تیم سیاه در روز.

### شناسنامه
- تیم: `black`  
- نوع: اطلاعات روز + مارک ویژه روز ۲

### Workflow
- روز ۲: انتخاب هدف → اعلام گروهی + `DianSelectedPlayer` و ضرب‌الاجل Day_no+4.  
- روزهای دیگر: ۵۰٪ دیدن نقش واقعی.  
- اگر بازیکن مارک‌شده بمیرد یا خود دیان بمیرد، پیام‌های پاک‌سازی مارک.

### State
`DianSelectedPlayer`, `DianSelectedPlayerDayNo`

### Message keys
`AskDianTowDay`, `AskDianDay`, `DianSelectedPlayerGroupMessage`, `DianSelectedTowDayIsDie`, `DianSee`, `DianNotSee`, `DianAfterKillPlayer`, `dianKillBeforVoteSelect`

### Edge cases
- کیبورد روز هم‌تیمی‌های black را از لیست انتخاب حذف می‌کند.

---

# ۷. سولو / ویژه

## ۷.۱ `role_monafeq` — منافق

### Reasoning
برد فقط با اعدام شدن توسط رأی روستا؛ تنها ماندن برد نیست.

### شناسنامه
- تیم: `monafeq`  
- نوع: برد معکوس رأی  
- اکشن شب/روز ندارد (جز تبدیل‌پذیری فرقه قطعی)

### Workflow
در `VT` اگر هدف اعدام منافق باشد: مرگ + دستاورد `Masochist` + `GamedEnd('monafeq')`.

### State
بدون فلگ اختصاصی پایدار

### Message keys
`killed_user`, `TannerEnd` (اگر تنها بماند)

### Edge cases
- تنها بازمانده = `nothing` نه برد.  
- فرقه او را ۱۰۰٪ تبدیل می‌کند.

---

## ۷.۲ `role_lucifer` — لوسیفر

### Reasoning
نقش فریب متا: اول هم‌تیمی انتخاب می‌کند، بعد اکشن دیگران را می‌دزدد؛ لیلیس و چند نقش خطرناک او را شکار می‌کنند.

### شناسنامه
- تیم: `lucifer`  
- وزن بالانس ۱۷  
- شب صفر: `CheckLuciferTeam`؛ شب‌های بعد: `CheckLucifer` در شروع شب

### Workflow
- شب ۰: انتخاب `rosta|wolf|ferqeTeem|vampire|qatel` → `ChangeLuciferTeam` + اطلاع تیم مقصد.  
- شب ≥۱: انتخاب بازیکن → جدول نقش: دزدی شب / دزدی رأی / دزدی روز / مرگ لوسیفر.  
- `DodgeNightSelect`: کیبورد نقش هدف برای لوسیفر باز می‌شود (`NightSelect`).

### State
`role_lucifer:checkLucifer`, `NightSelect`, `DodgeVote`, `DodgeDay`, `ClearLasTLucifer`, `Selected`

### Message keys
`LuciferChangedToTeam`, `LuciferTeamInfo`, `LuciferChangeTeamToMessage`, `RostaTeam`, `WolfTeams`, `FerqeTeam`, `VampireTeams`, `QatelTeam`, `DodgeDeadPlayer`, `LuciferInCultHunter`, `LuciferCultHunterDodge`, `LuciferDodgeQatelGroupMessage`, `LuciferDodgeWolfGroupMessage`, `LuciferDodgeBloodGroupMessage`, `LuciferDodgeVote`, `LuciferDodgeDayRole`, `DodgePlayerNight*`, `LuciferGGD`, `FindLucifer*`

### Edge cases
- شکارچی فرقه فریب را کامل بلاک می‌کند.  
- آلفا همیشه لوسیفر را می‌کشد.  
- کلیدهای lucifer هر شب نسبت به `ClearLasTLucifer` پاک می‌شوند.  
- فرقه: `role_lucifer` در CultAttemp صفر است ولی `role_Lucifer` (حروف بزرگ) ۷۰٪ دارد — ناسازگاری نام در سورس.

---

## ۷.۳ `role_Joker` — جوکر

### Reasoning
برد از جمع کتاب، نه از اکثریت؛ هارلی هم محافظ حمله است هم کمک جستجو.

### شناسنامه
- تیم: `joker`  
- اولویت شب: اولین حل‌کننده‌ها

### Workflow
جستجوی کتاب؛ روی دشمنان خاص اگر هارلی نباشد قتل مستقیم؛ با هارلی فقط جستجو + محافظت حمله از مسیر `CheckAttack`.

### State
`BookIn:*`, `FindedBook`, `FindedBookIN:*`, `DiedJoker`, `DiedHarly`

### Message keys
`SuccessFindJoker`, `FiledFindJoker`, `PlayerMessageWhenKillByJoker`, `GroupMessageWhenKillEnemy`, `JokerMessageWhenAttack`, `JokerMessageWhenHalryDied`, `Harly3DayFindJokerMessage`

### Edge cases
- باگ احتمالی: در `CheckJoker` دو بار Kenyager رندوم می‌شود و بار دوم خود جوکر را از استخر حذف می‌کند.  
- مرگ جوکر به هارلی خبر می‌دهد.

---

## ۷.۴ `role_Harly` — هارلی

### Reasoning
جفت جوکر؛ محافظت در برابر حمله گرگ/قاتل/خون‌آشام و کمک به شمارش کتاب.

### شناسنامه
- تیم: `joker`  
- شب ۲: یک کتاب رایگان به شمارنده اضافه می‌شود (`Harly3DayFind`)

### Workflow
جستجوی کتاب مثل جوکر؛ `CheckAttack` مهاجم را متوقف می‌کند (گرگ تیمی ۵۰٪ شانس مرگ مهاجم).

### State
`HarlyNotSendFind`, `DiedHarly`, مشترک با کتاب‌ها

### Message keys
`SuccessHarlyFind`, `FiledHarlyFind`, `Harly3DayFind`, `HarlyWhenAttackJoker`, `HarlyWhenDiedJoker`, `WolfMessageWhenAttakJoker`, `GroupMessageWhenWolfAttack`, `OneWolfAttackJoker`, `KillerMessageWhenAttack`, `VampireAttack`

### Edge cases
- بدون هارلی، جوکر آسیب‌پذیر و قاتل دشمن می‌شود.

---

## ۷.۵ `role_Bomber` — بمب‌گذار

### Reasoning
برد با کاشت کافی یا برتری عددی؛ دینامیت پادزهر قطعات است.

### شناسنامه
- تیم: `Bomber`  
- نوع: کاشت شب  
- سقف بمب از تعداد بازیکن محاسبه می‌شود

### Workflow
شب انتخاب → `CheckBomber`: PV به هدف `BombPlanted`، به بمب‌گذار `BomberSuccess`، افزایش شمارنده.

### State
`BombPlanted`, `BombCount`, `BomberGet:{user}`, `FindBombCount`, `FindedBombCount`, `DinamitInGame`

### Message keys
`BombPlanted`, `BomberSuccess`, `BombPlantedMulti`, `DinamitFind_*`, `DinamitSuccessFind`, `DinamitFiledFind`, `DinamitLastFind`

### Edge cases
- افزایش `BombPlanted` در حل شب است نه در لحظهٔ کلیک CM.  
- چهار قطعه اول بازی روی چهار نفر تصادفی است.

---

## ۷.۶ `role_Hamzad` — همزاد

### Reasoning
کپی نقش در لحظه مرگ الگو؛ نباید توسط فرقه دزدیده شود.

### شناسنامه
- تیم: `hamzad`  
- شب: فقط انتخاب الگو (`GamePl:Hamzad`)  
- CultAttemp صفر

### Workflow
مرگ الگو → `ConvertHamzad` با شاخه‌های ویژه گرگ/فرقه/فراماسون/قاتل/کماندار/کلانتر/اصیل/آتش/یخ/وحشی/ناظر/پیش‌فرض.

### State
`GamePl:Hamzad`

### Message keys
`HamzadTabdilshode`, `HamzadToFerqe*`, `HamzadMeFerqe`, `HamzadToFeramason*`, `HamzadMeFeramason`, `DGTransToWolf`, `DGTransformToWolf`, `DGToWolf`, `HamzadMeKiller*`, `HamzadMeArcher`, `HamzadMeHunter*`, `HamzadMeBlood*`, `NewWCRoleModel`

### Edge cases
- اگر همزاد قبل از مرگ الگو بمیرد، فلگ پاک و تبدیل رخ نمی‌دهد.  
- در جدول برد نهایی، همزاد تبدیل‌نشده معمولاً باخت است.

---

## ۷.۷ `role_dinamit` — دینامیت

### Reasoning
پادزهر بمب‌گذار؛ ۳ قطعه = برد سولو.

### شناسنامه
- تیم: `dinamit`  
- اکشن شب و روز برای جستجوی قطعه

### Workflow
هدف اگر `BomberGet` داشته باشد و قبلاً همان خانه پیدا نشده باشد → شمارنده + لیست نام قطعات.

### State
`FindBombInHome:*`, `FindBombCount`, `FindedBombCount`, `DinamitInGame`

### Message keys
`AskDinamit_day`, `DinamitSuccessFind`, `DinamitFiledFind`, `DinamitLastFind`, `DinamitFind_timer`, `DinamitFind_Gunpowder`, `DinamitFind_Chassis`, `DinamitFind_Wicks`

### Edge cases
- تکرار روی همان خانه قبلاً یافته = `DinamitLastFind`.

---

## ۷.۸ `role_dozd` — دزد

### Reasoning
سولو اقتصادی: ۳ سکه از اعتبار بازیکنان؛ تقابل دزد-دزد ویژه است.

### شناسنامه
- تیم: `dozd`  
- اولویت شب: بعد از ققنوس

### Workflow
اگر هدف دزد: ۵۰٪ شکست یا انتقال ۳ سکه از دزد مهاجم به هدف.  
وگرنه اگر اعتبار >0: اولین سرقت قطعی + علامت `DozdIN`؛ سرقت‌های بعد ۵۰٪.

### State
`DozdIN:{user}`، credit در Mongo `Players`

### Message keys
`DozdSuccess`, `DozdSuccessPlayer`, `DozdFiled`, `DozdFiledMessage`, `DozdINDozd`, `DozdInDozdMessage`, `DozdInDozdFiled`

### Edge cases
- اعتبار ۰ = شکست.  
- سرقت روی دزد دیگر می‌تواند خلاف جهت باشد.

---

## ۷.۹ `role_khenyager` — خنیاگر

### Reasoning
اخلال انتخاب‌ها: یک‌بار در شب همه انتخاب‌ها را رندوم می‌کند.

### شناسنامه
- تیم: `khenyager`  
- اثر: فلگ `Kenyager` در طول همان شب

### Workflow
انتخاب شب → کاهش `KenyagerCount` + ست فلگ؛ تقریباً همه resolverها اگر فلگ باشد هدف را عوض می‌کنند؛ آخر شب `CheckKhenyager` فلگ را پاک می‌کند.

### State
`Kenyager`, `KenyagerCount`

### Message keys
کلید اختصاصی انتخاب نقش (از SendNight) + اثر غیرمستقیم روی همه پیام‌های «هدف اشتباه»

### Edge cases
- بعضی resolverها رندوم را بدون حذف کامل خود نقش انجام می‌دهند (ناسازگاری جزئی جوکر).

---

## ۷.۱۰ `role_hellboy` — هل‌بوی

### وضعیت وجود
- در لیست‌های نقش CM به‌صورت کامنت/`off` است.  
- در `join` فقط `CheckAllowGroup('role_hellboy')` دارد.  
- در `GetRoleTeam` تعریف نشده.  
- **نتیجه:** نقش در سورس فعلی عملاً غیرفعال/ناقص است؛ برای بازنویسی نباید رفتار کامل فرض شود مگر بعداً پیاده شود.

---

# ۸. نقش‌های روستایی باقی‌مانده (خارج از بچ ۱)

## ۸.۱ `role_Sweetheart` — معشوقه

### Reasoning
عشق اجباری با اولین مهاجم خاص؛ عشق قبلی می‌میرد؛ عاشق هم‌تیم برای حملات بعدی مصون/رفتار ویژه دارد.

### شناسنامه
تیم `rosta`؛ غیرفعال شب؛ واکنش در مسیر قاتل/گرگ/فرقه/خون‌آشام/شوالیه/کماندار/شکارچی

### Workflow
اولین حمله واجد شرایط → `LoverBYSweetheart` (کشتن عشق قبلی، ست `SweetheartLove:team`). حملات بعدی همان تیم رفتار متفاوت (قتل/تبدیل به‌جای عشق جدید).

### State
`SweetheartLove`, `SweetheartLove:team`, `SweetheartLove:name`, `love:{id}`

### Message keys
`MsgLoveSweetHeart`, `MsgPlayer*Loved`, `MsgSweetHeartLastLoveDead`, `MsgGroupDeadLastLove`, `MsgPlayerDeadLastLove`

### Edge cases
مرگ خود معشوقه کلیدهای عشق را پاک می‌کند؛ ۲ نفره با عشق فعال می‌تواند برد `lover` بدهد.

---

## ۸.۲ `role_Knight` — شوالیه

### Reasoning
قاتل شب روستا روی نقش‌های دشمن مشخص؛ روستایی عادی را نمی‌کشد.

### شناسنامه
تیم `rosta`؛ اولویت خیلی زود در شب؛ وزن ۸

### Workflow
فقط روی گرگ پایه/آلفا/ملکه فعال/قاتل/کماندار/خون‌آشام/ومپایر/بتا می‌کشد؛ بتا دوطرفه می‌کشد؛ شوالیه سیاه مهاجم را می‌کشد؛ لیلیس ۶۰٪ ضد؛ غیر دشمن = `KnightNoKillUser`.

### State
`KnightSendFor`, `Selected`

### Message keys
`KnightKillPlayer*`, `KnightNoKillUser`, `KnightPlayerIsDeadSee`, `MsgPlayerKNLoved`, `betaWolf_knight*`, `BlackKnightKillKnightMessage*`, `MessageForKnight`

---

## ۸.۳ `role_trouble` — دردسرساز

### Reasoning
یک‌بار در روز رأی دوم بدون شب ایجاد می‌کند.

### شناسنامه
تیم `rosta`؛ اثر فوری CM: `trouble` + `troubleOkUse`

### Message keys
`Asktrouble`, `troubleBtnYes`, `troubleBtnNo`, `troubleGroupMessage`

### Edge cases
فرقه ۴۰٪ (+باف) تبدیل می‌کند.

---

## ۸.۴ `role_Huntsman` — هانتسمن

### Reasoning
۲ تله شبانه؛ بازدیدکننده با ۵۰٪ می‌میرد. با مرگ شکارچی فرقه، هانتسمن زنده به شکارچی تبدیل می‌شود.

### شناسنامه
تیم `rosta`؛ `HuntsmanT=2` در شروع

### State
`HuntsmanTraps:{user}`, `HuntsmanT`

### Message keys
`SuccessHuntsmanG`, `SuccessHuntsmanGUserMessage`, `HuntsmanMessageKillPlayer`, `HuntsmanKillPlayerMessage`, `HuntsmanKillPlayerGroupMesssage`, `HuntsmanDeadCultHulter`

### Edge cases
لوسیفر وقتی تله تمام شده باشد رأی او را می‌دزدد.

---

## ۸.۵ `role_Chemist` — شیمیدان

### Reasoning
۵۰٪ قتل هدف / ۵۰٪ خودکشی؛ مقابل قاتل ۸۰٪ خودش می‌میرد؛ ریش‌سفید را به روستایی تبدیل می‌کند.

### شناسنامه
تیم `rosta`؛ اولویت بعد از قاتل؛ وزن ۱۰

### Message keys
`ChemistSuccess*`, `ChemistFail*`, `ChemistVisitYou*`, `ChemistTargetDead`, `ChemistTargetEmpty`, `ChemistSK*`, `ChemistKillWiseElder`, `ChemistKillWiseMessage`

### Edge cases
برای غیرگرگ اگر هدف بیرون خانه باشد `ChemistTargetEmpty`.

---

## ۸.۶ `role_Augur` — فالگیر

### Reasoning
هر شب یک نقش از نقش‌های مود که در بازی نیست می‌بیند (۳ نمونه تصادفی از اختلاف).

### Message keys
`AugurSees`, `AugurSeesNothing`

### Edge cases
فرقه ۴۰٪ (+باف) تبدیل.

---

## ۸.۷ `role_Princess` — شاهدخت

### Reasoning
از شب ۳ به بعد زندان روز؛ زندانی حملات شب قاتل/فرقه/مگنتو را بلاک می‌کند.

### State
`PrincessPrisoner:*`

### Message keys
`AskPrincess`, `PrincessPrisoner*`, `PrincessDead`, `PrincessPrisonerKillerAttack`, `PrincessPrisonerCultAttack`, `PrincessPrisonerWolfAttack`

### Edge cases
قاتل/شوالیه ممکن است فرار کنند (کلید شانس `EscapeKillerKnight` در جدول `_s` دیده نشد — باید در پورت با مقدار پیش‌فرض امن پیاده شود). آتش/یخ زندانی نمی‌شوند. مرگ شاهدخت همه زندان‌ها را آزاد می‌کند.

---

## ۸.۸ `role_qhost` — روح

### Reasoning
یک‌بار نقش یک نفر را می‌بیند تا کشف شود؛ کشف با حمله بعضی نقش‌ها (`GostFinded`).

### Message keys
`ghostSee` + پیام‌های کشف در HL

### Edge cases
اگر `FindGhost` ست باشد دیگر اکشن شب ندارد.

---

## ۸.۹ `role_Phoenix` — ققنوس

### Reasoning
فقط شب ۲ و ۴ شفا می‌دهد؛ سپر `PhoenixHealer` حملات را می‌بلعد؛ مرگ ققنوس سپرها را باطل و به اهداف خبر می‌دهد.

### Message keys
`MessagePhoenixForOne`, `MessagePhoenixSuccess`, `MassageAttack`, `MessageFor*`, `MessagePlayerPhoenixDead`

### Edge cases
لوسیفر در شب ۲/۴ اکشن شب ققنوس را می‌دزدد؛ در شب‌های دیگر رأی.

---

## ۸.۱۰ `role_babr` — ببر

### Reasoning
قتل شب روستا با بلاک فرشته/گرگ سفید/مورگانا.

### Message keys
`BabrKillGroupMessage`, `CowHiler`, `CowAngel`, `CowDPlayerAngelMessageANG`, `WolfMessageGourdWhiteWolf`, `WhiteWolfGourdIceQueenMessage`, `Morgana*`

---

## ۸.۱۱ `role_Cow` — گاو

### Reasoning
مشابه ببر با پیام‌های جدا؛ در بعضی لیست نقش مودها کامنت/غیرفعال است ولی resolver دارد.

### Message keys
`GroupMesageCowKill`, `CowHiler`, کلیدهای فرشته/گرگ سفید مشترک با ببر/یخ

---

## ۸.۱۲ `role_Botanist` — گیاه‌شناس

### Reasoning
در مسیر گاز گرگ/خون‌آشام می‌تواند تبدیل را لغو کند (تأیید روز).

### State
`role_Botanist:bittaned`, `bittaned:for`, `link`

### Message keys
`BotanistMessage`, `BotanistMessageOk`, `BotanistM`, `OkSendToBotanist`, `OkMessagePlayer`, `BotanistNo`, `btnOkUser`, `btnNoUser`

### Edge cases
فرقه ۷۰٪ (+باف) تبدیل.

---

## ۸.۱۳ `role_Watermelon` — هندوانه

### Reasoning
انتخاب شب صرفاً پیام اطلاع به طرفین؛ وزن بالانس ۰.

### Message keys
`WatermelonChoseUser`, `WatermelonChoseSuccess`

---

## ۸.۱۴ `role_Mouse` — موش

### Reasoning
استعلام منفی/دشمن؛ اگر شکارچی زنده باشد به او هم خبر می‌دهد؛ دستاورد با دو پیدا.

### Message keys
`MouseInD`, `MouseInNotD`, `CultHunterMessageS`, `CultHunterDead`

---

## ۸.۱۵ `role_clown` — دلقک

### Reasoning
در `GetRoleTeam` روستایی است و در `CultAttemp` تبدیل قطعی دارد؛ اکشن شب/روز اختصاصی در NG/DY دیده نشد (عمدتاً نقش پاسیو/تنظیمی).

### Message keys
عمدتاً `role_clown` / `role_clown_n` در پیام نقش

---

## ۸.۱۶ `role_javidShah` و `role_hipo`

### وضعیت
مثل هل‌بوی: در لیست‌های فعال CM کامنت شده‌اند؛ فقط گیت `CheckAllowGroup` در `join` دارند؛ تیم/resolver کامل در جریان شب/روز پیدا نشد. برای پورت: «وجود اسکلت، بدون منطق بازی کامل».

---

# ۹. جدول فشردهٔ تعامل‌های بحرانی

| سناریو | نتیجه غالب |
|--------|------------|
| فرقه → روستایی ضعیف | تبدیل قطعی |
| فرقه → قاتل/گرگ | مرگ بازدیدکننده (با شانس/خانه خالی) |
| فرقه → شکارچی | مرگ بازدیدکننده قطعی |
| قاتل → شوالیه سیاه | مرگ قاتل |
| قاتل → لیلیس | ۶۰٪ مرگ قاتل |
| قاتل → محافظ فرانک/مومیایی/فرشته/گرگ‌سفید | بلاک |
| خون‌آشام → کلانتر (اول) | کشف اصیل + مرگ کلانتر (+۳۰٪ مرگ مهاجم) |
| آتش‌نشان سوزاندن | مرگ لیست + بازدیدکنندگان خانه |
| جوکر ۳ کتاب یا ≤۳ بازیکن | برد joker |
| اعدام منافق | برد monafeq فوری |
| همزاد + مرگ الگو | کپی نقش همان شب |
| بمب‌گذار کاشت کافی | برد Bomber |
| دینامیت ۳ قطعه | برد dinamit |
| ۲ نفره با black | برد black |

---

# ۱۰. کلیدهای شانس مرتبط (`SE::_s`)

| کلید | مقدار |
|------|------|
| `VampireChangeWolfDU` | ۵۰ |
| `VampireChangeNotKill` | ۵۰ |
| `BVampireChangeConvet` | ۴۰ |
| `VampireChangeConvet` | ۲۰ |
| `KalanVampireDead` | ۳۰ |
| `DodgeQatelDead` | ۳۵ |
| `DodgeWolfDead` | ۳۵ |
| `DodgeBloodDead` | ۵۰ |
| `ChemistSuccessChance` | ۵۰ |
| ضدحمله لیلیس (هاردکد) | ۶۰ |
| تله هانتسمن | فعال اگر رندوم ≥ ۵۰ |
| شوالیه سیاه vs قاتل/شوالیه | عملاً ۱۰۰٪ |

---

# ۱۱. یادداشت بازنویسی پایتون

1. ترتیب `CheckNight`/`CheckDay` و محل جداگانه `CheckLucifer` را عیناً حفظ کنید.  
2. تفاوت `GetRoleTeam` با `PlayerByTeam` را مدل کنید (فرانک، مگنتو، اصیل، کنت، چیانگ).  
3. تبدیل‌ها: فرقه فوری؛ گاز خون‌آشام و گاز گرگ تأخیری تا `BittanCheck`.  
4. متن‌ها را فقط با کلید Lang پیاده کنید؛ iniهای Game_Mode بعداً پر شوند.  
5. نقش‌های `hellboy` / `javidShah` / `hipo` را فعلاً به‌عنوان stub علامت بزنید.  
6. ناسازگاری `role_lucifer` در برابر `role_Lucifer` داخل `CultAttemp` را آگاهانه تصمیم‌گیری کنید (باگ بالقوه سورس).
