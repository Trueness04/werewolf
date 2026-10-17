# اسپرینت ۱۰ — کاتالوگ دستورات و کال‌بک‌های بازی

**وضعیت:** سند کاتالوگ (مرجع تعامل کاربر برای بازنویسی پایتون)  
**هدف اسپرینت:** فهرست کامل مسیرهای ورود کاربر مرتبط با بازی — دستورات تلگرام، متدهای `CM`، و پیشوندهای کال‌بک — بدون وابستگی به Notes_Mode  
**خروجی قابل قبول:** تیم پایتون می‌تواند هر دکمه/دستور بازی را به handler مشخص نگاشت کند؛ قالب data و اثر جانبی (Redis/فاز) مشخص است  
**مرجع سورس:** `bot/Commands/*`، `CallbackqueryCommand.php`، `CM.php` (+ تولید کیبورد در `NG.php` / `DY.php` / `VT.php` / `HL.php` / `join.php` / `GR.php`)  
**مرجع کلان:** `docs/werewolf-python-rewrite-master-fa.md`  
**هم‌خوانی نقص‌ها:** `docs/php-gaps-and-defects-fa.md`

---

# ۱. تحلیل و استدلال

لایهٔ Longman فقط نام فایل را به آپدیت تلگرام وصل می‌کند؛ منطق تقریباً همیشه در `CM` است. فیلد `protected $name` در بسیاری از Commandها کپی‌پیست اشتباه است؛ **منبع حقیقت برای مسیر عمومی، `protected $usage` است** (مثلاً `/startgame`).

کال‌بک‌ها در یک زنجیرهٔ `strpos` ترتیبی در `CallbackqueryCommand` parse می‌شوند. ترتیب مهم است: پیشوند کوتاه‌تر یا مبهم می‌تواند پیشوند دیگر را ببلعد (مثلاً `config_` قبل از `configRoles_` نیست، ولی `bst` می‌تواند داخل رشته‌های دیگر باشد اگر الگوی سستی استفاده شود). فرمت رایج بازی:

- `Prefix_Suffix/chatId[/userId|/extra]`
- یا `Prefix/chatId/extra`

انتخاب موفق معمولاً پیام خصوصی را به تأیید ادیت می‌کند؛ اگر `game_state` عوض شده باشد پیام `endTime` می‌آید.

---

# ۲. قرارداد عمومی کال‌بک

| جزء | معنی |
|-----|------|
| بخش ۰ | پیشوند + گاهی پسوند نقش/اکشن (با `_`) |
| بخش ۱ (پس از `/`) | معمولاً `chat_id` گروه |
| بخش ۲+ | هدف (`user_id`)، مقدار کانفیگ، تیم لوسیفر، و غیره |
| پاسخ فوری | اغلب `answerCallbackQuery`؛ گاهی فقط ادیت متن/کیبورد |
| قفل انتخاب | `GamePl:Selected:{userId}:user` برای جلوگیری از دوباره‌کلیک |

---

# ۳. دستورات مرتبط با بازی (کاتالوگ)

## ۳.۱ چرخهٔ لابی و فاز

| دستور (usage) | لایه Command | متد CM | اثر خلاصه |
|---------------|--------------|--------|-----------|
| `/startgame` | StartGameCommand | `CM_StartGame('Normal')` | شروع لابی مود نرمال |
| `/startmighty` | StartMightyCommand | `CM_StartGame('Mighty')` | مود قدرتی |
| `/starteasy` | StartEasyCommand | `CM_StartGame('Easy')` | مود آسان |
| `/startvampire` | StartVampireCommand | `CM_StartGame('Vampire')` | مود ومپایر (نیاز on بودن Vampire/Blood) |
| `/startRomantic` | StartRomanticCommand | `CM_StartGame('Romantic')` | مود رمانتیک |
| `/startWereWolf` | StartWereWolfCommand | `CM_StartGame('WereWolf')` | مود ورولف |
| `/startFoolish` | StartFoolishCommand | `CM_StartGame('Foolish')` | مود Foolish |
| `/StartBomber` | StartBomberCommand | `CM_StartGame('Bomber')` | مود بمبر — **حذف محصولی؛ در پایتون پیاده نشود** (remediation §۱۶) |
| `/startcoin` | StartCoinGameCommand | `CM_StartGame('coin')` | مود سکه — **حذف محصولی؛ در پایتون پیاده نشود** (remediation §۱۷؛ نه حذف کیف پول `/coin`) |
| `/startmafia` | StartMafiaCommand | `CM_StartGame('Mafia')` | مود مافیا (نقش‌دهی خاص — نقص جداگانه) |
| `/join` | JoinCommand | `CM_Join` | ورود به لابی (لینک/دکمه نیز) |
| `/flee` | FleeCommand | `CM_Flee` | خروج؛ فقط در join اگر Flee فعال باشد |
| `/extend` | ExtendCommand | `CM_Extend` | تمدید تایمر لابی |
| `/forcestart` | ForceStartCommand | `CM_ForceStart` | ادمین: پایان زودهنگام تایمر join |
| `/players` | PlayersCommand | `CM_Players` | لیست بازیکنان لابی/بازی |
| `/nextgame` | NextGameCommand | `CM_Nextgame` | صف «بازی بعد» |
| `/killgame` | killGameCommand | `CM_KillGame` | ادمین: بستن بازی |
| `/modeinfo` | ModeInfoCommand | `CM_ModeInfo` | توضیح مود جاری |
| `/reset` | ResetCommand | `CM_Reset` | ریست وضعیت (ادمین/خاص) |
| `/getstatus` | GetStatusCommand | `CM_Getstatus` | وضعیت موتور/گروه |
| `/runinfo` | RunInfoCommand | `CM_RunInfo` | اطلاعات اجرا |
| `/live` | LiveCommand | `CM_Live` | بازی‌های زنده |
| `/groupStats` | GroupStatsCommand | `CM_GroupStats` | آمار گروه |
| `/normal` | NormalCommand | `CM_Normal` | مسیر مود/گروه نرمال |
| `/startchallenge` | StartChallengeCommand | **`CM_StartChallenge` — متد در CM وجود ندارد** | چالش؛ در PHP فعلی fatal/شکسته |

## ۳.۲ تنظیمات گروه و زبان

| دستور | متد CM | اثر |
|-------|--------|-----|
| `/config` | `CM_Config` | منوی تنظیمات ادمین (معمولاً PV) |
| `/setlang` | `CM_Setlang` | زبان کاربر |
| `/setlink` | `CM_SetLink` | ثبت لینک گروه |
| `/removelink` | `CM_RemoveLink` | حذف لینک |
| `/setcultmessage` | `CM_setcultmessage` | پیام سفارشی شکارچی/فرقه |
| `/addrole` | `CM_AddRoleToGroup` | افزودن نقش به کانفیگ گروه |
| `/addrole` (RemoveRoleCommand — usage اشتباه) | `CM_RemoveRoleGroup` | حذف نقش؛ usage باید جدا باشد |
| `/mygroupstate` | `CM_MyGroupState` | وضعیت گروه کاربر |
| `/changestate` | `CM_ChangeState` | مهاجرت شناسه کاربر (فقط ADMIN_ID) |
| `/sync` | `CM_Sync` | همگام‌سازی PV/گروه |
| `/chatid` | `CM_ChatId` | نمایش chat id |
| `/grouplist` | `CM_GroupList` | لیست گروه‌ها |
| `/help` | `CM_Help` | راهنما |

## ۳.۳ داخل بازی / ابزار بازیکن

| دستور | متد CM | اثر |
|-------|--------|-----|
| `/ping` | `CM_Ping` | تست پاسخ |
| `/smite` | `CM_Smite` | اخراج ادمین از بازی |
| `/stats` | `CM_Stats` | آمار بازیکن |
| `/score` | `CM_Score` | امتیاز |
| `/kill` | `CM_Killme` | خودکشی/خروج خاص |
| `/kills` | `CM_Kills` | آمار کشتار |
| `/myidles` | `CM_Myideals` | ایدل‌ها |
| `/rolelist` | `CM_RoleList` | لیست نقش‌های فعال |
| `/killlist` | `CM_KillList` | لیست کشت‌ها (روز/شب) |
| `/myhero` | `CM_MyHero` | هیرو |
| `/achievement` | `CM_Achievement` | دستاورد (لایه ناقص) |
| `/banme` | `CM_BAnme` | خود-بن |
| `/banplayer` | `CM_BanPlayer` | بن توسط ادمین گلوبال |
| `/rban` | `RemoveAsBanList` | برداشتن بن |
| `/report` | `CM_Report` | گزارش بازیکن |
| `/admins` | `CM_AdminSetting` | تنظیم ادمین |
| `/addtestplayer` | `CM_Addtest` | تست جوین مصنوعی |
| `/pga` | `PromateGlobalAdmin` | ارتقای ادمین گلوبال |
| `/ip` | `CM_IP` | IP |
| `/setgif` | `CM_SetGif` | گیف نقش/رویداد |
| `/game` | `CM_Game` | منوی بازی PV |
| `/account` | `CM_Account` | حساب |
| `/mysetting` | `CM_MySetting` | تنظیمات شخصی (گاهی به shop) |
| `/mylevel` | `CM_MyLevel` | سطح |
| `/gets` | `CM_Gets` | دریافت وضعیت خاص |

## ۳.۴ اقتصاد / لیگ / اجتماعی (حاشیهٔ بازی)

| دستور | متد CM | یادداشت |
|-------|--------|---------|
| `/coin` | `CM_Coin` | فروشگاه سکه |
| `/shop` | `CM_Shop` | فروشگاه |
| `/helpShop` | `CM_HelpShop` | راهنمای فروشگاه |
| `/getcoin` | `CM_GetCoin` | دریافت سکه |
| `/getfree` | `CM_FreeCoin` | سکه رایگان |
| `/mycoin` | `CM_MyCoin` | موجودی |
| `/addcoin` | `CM_AddCoin` | افزودن سکه (ادمین) |
| `/sendcoin` | `SendCoin` | انتقال سکه |
| `/donate` | `CM_Dontate` | دونیت |
| `/league` | `CM_GetLeague` | لیگ |
| `/myleaguescore` | `CM_MyLeagueScore` | امتیاز لیگ |
| `/addfriend` | `CM_addfriend` | دوست |
| `/addgroup` | `CM_AddGroup` | ثبت گروه |
| `/jointournament` | `CM_JoinTornumet` | تورنمنت |
| `/sponsers` | `CM_Sponsers` | اسپانسر |
| `/bet` | BetCommand → **`return false`؛ `CM_bet` کامنت** | شرط‌بندی غیرفعال |

## ۳.۵ سیستم / پیام عمومی

| مسیر | اثر |
|------|-----|
| `/start` | `CM_Start` — خوش‌آمد PV؛ deep-linkهای خاص |
| Genericmessage | منوی متنی (گروه‌لیست، سکه، شاپ، اخبار، پشتیبانی، آکادمی، killlist) + `CM_Command` برای کلیدهای Lang |
| newchattitle | `CM_NewChatTitle` |
| inlinequery / choseninlineresult | جستجوی اینلاین (خارج از هستهٔ شب/روز) |

---

# ۴. پیشوندهای کال‌بک — هستهٔ بازی

## ۴.۱ انتخاب شب

| پیشوند / الگو | هندلر | معنی |
|---------------|--------|------|
| `NightSelect_{Role}/chatId[/userId]` | `CM::NightSelectedCheck` | انتخاب هدف شب |
| `NightSelect_LuciferSelectTeam/chatId/{team}` | همان | انتخاب تیم لوسیفر: `rosta` / `wolf` / `vampire` / `ferqeTeem` / `qatel` |
| `NightSelect_Cupe` سپس `NightSelect_Cupe2` | همان | دو مرحلهٔ الهه عشق |
| `NightSelect_khenyager/chatId` | همان | تأیید خنیاگر (بدون لیست بازیکن) |
| `NghddgDlec_{user_role}/…` | `CM::NightSelectDodge` | شب به‌جای لوسیفر (dodge) |
| `skip/…` | `CM::Skip` | رد انتخاب |
| `RoleFireFighterFight/chatId` | `CM::FighterFight` | دستور آتش‌زدن فوری پادشاه آتش |

### پسوندهای `NightSelect_*` شناخته‌شده (از NG + CM)

`babr`, `Hamzad`, `khenyager`, `Lucifer`, `Joker`, `Harly`, `KentVampire`, `Feranc`, `LuciferSelectTeam`, `Cupe`, `Cupe2`, `Phoenix`, `BrideTheDead`, `LiLis`, `Vahshi`, `Bomber`, `Firefighter`, `Honey`, `IceQueen`, `Shekar`, `IceWolf`, `Fool`, `Dozd`, `Negativ`, `Mouse`, `Natasha`, `Archer`, `Watermelon`, `qhost`, `dinamit`, `Knight`, `Killer`, `Angel`, `WhiteWolf`, `Mummy`, `Wolf`, `Magento`, `Vampire`, `Enchanter`, `Chemist`, `Ferqe`, `Sear`, `Cow`, `Huntsman`, `Jado`

## ۴.۲ انتخاب روز

| پیشوند | هندلر | معنی |
|--------|--------|------|
| `DaySelect_{Action}/chatId[/userId]` | `CM::DaySelectedCheck` | اکشن روز |
| `DySlDodge_{Type}/…` | `CM::DaySelectedDodge` | روز dodge |

### اکشن‌های `DaySelect_*`

| پسوند | نقش / معنی |
|-------|------------|
| `Karagah` | کارآگاه |
| `Princess` | شاهدخت — زندان |
| `dinamit` | دینامیت |
| `BlackKnight` | شوالیه سیاه |
| `Dian` | دیان (تیم سیاه) |
| `KentVampire` | کنت ومپایر |
| `Spy` | جاسوس |
| `Tofangdar` | تفنگدار (شلیک) |
| `Solh` | صلح فوری (لغو لینچ) |
| `Kadkhoda` | افشای کدخدا |
| `Ruler` | حاکم — رأی انحصاری فردا |
| `Khabgozar_Yes` / `Khabgozar_No` | خواب‌گذار |
| `davina_Yes` / `davina_No` | داوینا |
| `Ahangar_Yes` / `Ahangar_no` | آهنگر |
| `trouble_yes` / `trouble_no` | دردسرساز — رأی دوم |
| `SendBittenYes` / `SendBittenNo` | تأیید/رد تبدیل گاز روز |
| `BotanistOk` / `BotanistNo` | گیاه‌شناس |

### `DySlDodge_*`

`Gunner`, `Princess`, `Karagah`, `KentVampire`, `Spy` (+ موارد نقش در NightSelectDodge برای شب)

## ۴.۳ رأی و مرگ معوق

| پیشوند | هندلر | معنی |
|--------|--------|------|
| `VoteSelect/…` | `CM::VoteUser` | رأی لینچ |
| `DdgSlVt/…` | `CM::DodgeVote` | رأی dodge (لوسیفر و مشابه) |
| `Kalantar_shot/…` | `CM::KalanShot` | شلیک مرگ کلانتر |

## ۴.۴ جادو / هیرو / لیست

| پیشوند | هندلر | معنی |
|--------|--------|------|
| `slectMajik/chatId/{type}` | `CM::UseMajik` | مصرف مجیک: `MajiKhabar`, `MajikSear`, `MajiKHil`, `MajiKGhost` |
| `todayList/…` | `CM::GetTodayList` | لیست امروز |
| `getKilllist/{type}` | `CM_KillList` | سوئیچ لیست کشت |
| `BfdHero/…` | `CM::CreateHero` | ساخت هیرو |

---

# ۵. پیشوندهای کال‌بک — تنظیمات گروه

| پیشوند | هندلر | معنی |
|--------|--------|------|
| `config_done` | `CM::configDone` | ذخیره/بستن کانفیگ |
| `setting_{panel}/chatId` | `CM::GetConfigKeyboard` | پنل: `time`, `role`, `game`, `group`, `viprole` |
| `backtoconfig/…` | `CM::BackToConfig` | بازگشت منوی اصلی کانفیگ |
| `configRoles_{Fool\|hypocrite\|Cult\|lucifer}/…` | `CM::ConfigRole` | زیرمنوی نقش ویژه |
| `configGroup_{…}/…` | `CM::ConfigGroup` | زیرمنوی گروه |
| `configTimer_{day\|night\|Vote\|SectetVote\|join\|Extend}/…` | `CM::ConfigTimer` | تایمرها |
| `configGame_{…}/…` | `CM::ConfigGame` | آپشن‌های گیم‌پلی |
| `configureGroup_{value}/chatId/{key}` | `CM::ChangeGroupConfig` | اعمال مقدار (`onr`/`offr`/`all`/عدد/مود) |
| `GroupLang/…/{lang}` | `CM::ChangeGroupLang` | زبان گروه |
| `ChangeGroupGameMode/…/{mode}` | `CM::ChangeGroupGameMode` | مود فایل Lang گروه |
| `OfOnStatusRo/…/{role}` | `CM::OfAndOnRoleGroup` | روشن/خاموش نقش VIP |
| `SGFDRol\|…` | `CM::ChangeRoleSetting` | تنظیم نقش خریداری‌شده |
| `NotAllow` | — | سقف بازیکن قفل‌شده |

کلیدهای رایج `configureGroup_…/{key}`: `role_*`, `type_mode`, `expose_role`, `expose_role_after_dead`, `PinMessage_on_group`, `Flee`, `show_user_id`, `allow_extend`, `max_player`, `*_timer`, `cultHunter_*`, `secret_vote*`, `mute_die`, `randome_mode`, و ده‌ها `role_*` از منوی VIP.

---

# ۶. پیشوندهای کال‌بک — کاربر / اقتصاد / ادمین

| پیشوند | هندلر | معنی |
|--------|--------|------|
| `UserLang_{lang}` | `CM::GetGameMode` | بعد از انتخاب زبان → مود کاربر |
| `UserGameMode_{mode}` | `CM::ChangeGameMode` | ذخیره مود پیش‌فرض کاربر |
| `cancel_nextgame` | `CM::cancel_nextgame` | لغو صف nextgame |
| `BanPlayer_{action}/…` | `CM::BanPlayer` | `remove`/`No`/`30min`/`1d`/`1w`/`1m`/`1y`/`ban` |
| `AdminSetting` | `CM::AdminSetting` | پنل ادمین |
| `locked` | پاسخ ثابت | دستور قفل‌شده توسط مدیر اصلی |
| `closeBanList` | `CM::RemoveMarkUp` | بستن کیبورد بن |
| `Grouplist_{…}` | `CM::SelectGroupList` | انتخاب از لیست گروه |
| `GroupGameMode_{…}` | `CM::SendGroupList` | فیلتر مود لیست گروه |
| `SendMessage/…` | `CM::SendMessageToPV` | پیام PV |
| `AddFriend_* /…` | `CM::FriendR` | قبول/رد/حذف دوست |
| `gpgchplayer/chatId` | `CM::ChangeGroup` | تعویض گروه فعال بازیکن |
| `ReportResult/{section}/{reportId}` | `CM::ReportUserAdmin` | رأی ادمین روی گزارش |
| `GetCoin_{item}` | `CM::GetChargeItem` | آیتم شارژ |
| `ShopItem_{id}` | `CM::ShopItemSet` | انتخاب آیتم شاپ |
| `BTNSP_{…}` | `CM::ShopCheckout` | تسویه |
| `setLaqabToMe/{id}` | `CM::SetLaqab` | لقب |
| `BetGame/…` | `CM::CreateBet` | ساخت شرط (دستور /bet خاموش است) |
| `bst/…` | `CM::btsOnHou` | شرط ساعتی |
| `bls_reject` | `CM::btsReject` | رد شرط |
| `bgs_confirm` | `CM::btsConfirm` | تأیید شرط |
| `bghChangeBet` | `CM::ChangeBetCount` | تغییر مبلغ |
| `upAcc/{tier}` | `CM::upAcc` | ارتقای اکانت |
| `ugrade/{…}` | `CM::ugrade` | ارتقا |
| `asdopt/{…}` | `CM::asdopt` | آپشن اکانت |
| `setGifi` / `delGif` / `getMyGif` | گیف شخصی | |
| `settext` / `delTextPr` | متن شخصی نقش | |

---

# ۷. جریان نگاشت برای پایتون (قرارداد پیشنهادی)

1. Router دستور: `usage` → handler نام‌دار (نه کپی `$name`های خراب PHP).  
2. Router کال‌بک: جدول پیشوند با **longest-prefix match** تا باگ `strpos` ترتیبی تکرار نشود.  
3. هر `NightSelect`/`DaySelect` فقط بنویسد؛ resolve در کرون فاز بماند (هم‌ارز PHP).  
4. اکشن‌های فوری روز (`Solh`, `Kadkhoda`, `Ruler`, خواب‌گذار، داوینا، آهنگر، دردسرساز) اثر را همان لحظه اعمال کنند.  
5. `answerCallbackQuery` همیشه برگردد تا کلاینت تلگرام hang نکند (در PHP گاهی مسیر بدون answer تمام می‌شود).

---

# ۸. QA پیشنهادی این اسپرینت

- [ ] همهٔ `/start*` لابی با مود درست در Redis می‌گذارند  
- [ ] یک کال‌بک شب برای گرگ، فرقه، قاتل، ومپایر، لوسیفر‌تیم ذخیره می‌شود  
- [ ] `DaySelect_Solh` لینچ را قطع می‌کند  
- [ ] `VoteSelect` و `Kalantar_shot` در فاز درست کار می‌کنند  
- [ ] منوی `/config` همهٔ چهار پنل را باز می‌کند و `configureGroup_` مقدار می‌نویسد  
- [ ] `/bet` و `/startchallenge` رفتار صریح دارند (غیرفعال مستند یا پیاده‌سازی درست)  
- [ ] هیچ کال‌بک بازی بدون پاسخ callback_query نمی‌ماند  

---

# ۹. خارج از محدودهٔ این سند

- ترتیب resolve شب/روز/رأی (اسپرینت ۱، day/vote جدا)  
- متن کامل Lang (اسپرینت ۶)  
- فروشگاه/پرداخت به‌عنوان محصول کامل  
- Notes_Mode
