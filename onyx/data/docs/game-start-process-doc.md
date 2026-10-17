# داکیومنت جامع فرایند بازی در Onyx

## فرایند آغاز بازی ← ساخت (لابی) بازی ← شروع بازی

> این داکیومنت «مو‌به‌مو» و کامل، بر اساس کدهای واقعی مخزن نوشته شده است.
> همه مسیرها با ذکر فایل، تابع و شماره ارجاع مستقیم به سورس آمده است.
> تاریخ بازبینی: ۱۸ مهر ۱۴۰۵ (2026-10-18)

---

## فهرست محتوا

1. [نمای کلی و نقشه معماری](#۱-نمای-کلی-و-نقشه-معماری)
2. [پیش‌نیازها و راه‌اندازی سامانه (launcher)](#۲-پیشنیازها-و-راهاندازی-سامانه-launcher)
3. [ثبت هندلرها و حلقه تیک (app/main.py)](#۳-ثبت-هندلرها-و-حلقه-تیک-appmainpy)
4. [پیکربندی‌های دکلراتیو دخیل در فرایند](#۴-پیکربندیهای-دکلراتیو-دخیل-در-فرایند)
5. [مدل داده‌ای: PostgreSQL و Redis](#۵-مدل-دادهای-postgresql-و-redis)
6. [فاز A — فرمان آغاز (/startgame و خواهران)](#۶-فاز-a--فرمان-آغاز-startgame-و-خواهران)
7. [فاز B — ساخت لابی (LobbyManager.start_game_for_group)](#۷-فاز-b--ساخت-لابی)
8. [فاز C — اعلام لابی در گروه (پیام، کیبورد، گیف، لیست بازیکنان)](#۸-فاز-c--اعلام-لابی-در-گروه)
9. [فاز D — مرحله پیوستن (join) و ۱۲ گام اعتبارسنجی](#۹-فاز-d--مرحله-پیوستن-join-و-۱۲-گام-اعتبارسنجی)
10. [فاز E — حلقه تایمر لابی (TimerManager.tick)](#۱۰-فاز-e--حلقه-تایمر-لابی-timermanagertick)
11. [فاز F — پایان join و تصمیم سرنوشت لابی](#۱۱-فاز-f--پایان-join-و-تصمیم-سرنوشت-لابی)
12. [فاز G — جریان اولیه شروع بازی (InitialFlow)](#۱۲-فاز-g--جریان-اولیه-شروع-بازی-initialflow)
13. [فاز H — توزیع نقش‌ها (RoleDistributionManager)](#۱۳-فاز-h--توزیع-نقشها-roledistributionmanager)
14. [فاز I — آغاز اولین شب (NightManager)](#۱۴-فاز-i--آغاز-اولین-شب-nightmanager)
15. [مسیرهای فرعی و جایگزین شروع](#۱۵-مسیرهای-فرعی-و-جایگزین-شروع)
16. [خطاها، حالت‌های مرزی و رفتارهای سکوت](#۱۶-خطاها-حالت‌های-مرزی-و-رفتارهای-سکوت)
17. [رویدادهای ثبت‌شده (log_game_event)](#۱۷-رویدادهای-ثبت‌شده-log_game_event)
18. [جدول متغیرهای محیطی مؤثر](#۱۸-جدول-متغیرهای-محیطی-مؤثر)
19. [نمودار توالی کامل (ASCII)](#۱۹-نمودار-توالی-کامل-ascii)
20. [چک‌لیست تست دستی end-to-end](#۲۰-چک‌لیست-تست-دستی-end-to-end)

---

## ۱. نمای کلی و نقشه معماری

بازی در یک **گروه تلگرام** می‌چرخد و چرخه حیات آن چنین است:

```
NO_GAME ──(/startgame)──▶ JOINING ──(تایمر/forcestart/پرشدن ظرفیت)──▶ RUNNING
                              │                                          │
                              ▼                                    night → day → vote ...
                        (بازیکن ناکافی)──▶ close_lobby ──▶ NO_GAME
```

سه مفهوم کلیدی که کاربر پرسیده، دقیقاً به این اجزای کد نگاشت می‌شوند:

| مفهوم درخواستی | معادل در کد | فایل |
|---|---|---|
| **آغاز بازی** (زدن فرمان شروع توسط کاربر) | `start_game_entry` / `handle_start_game` (معادل `CM_StartGame` در PHP قدیم) | `app/handlers/start_game.py` |
| **ساخت بازی** (ایجاد لابی + پیام‌های آن) | `_start_new` + `LobbyManager.start_game_for_group` | `app/handlers/start_game.py`، `app/managers/lobby_manager.py` |
| **شروع بازی** (بستن join و ورود به گیم‌پلی) | `TimerManager._finish_body` → `InitialFlow.start_initial_flow` → `RoleDistributionManager.distribute_roles` → `NightManager.start_first_night` (معادل `GameStarted` در PHP قدیم) | `app/managers/timer_manager.py`, `initial_flow.py`, `role_distribution_manager.py`, `night_manager.py` |

لایه‌های درگیر:

- **Handlers** (`app/handlers/`): ورودی‌های تلگرام (command/callback).
- **Managers** (`app/managers/`): منطق بازی؛ تایمرها از JSONهای `data/config/` تغذیه می‌شوند.
- **Class** (`app/class/`): مدل‌های دامنه مثل `GameModeInfo`.
- **Database** (`app/database/`): SQLAlchemy async روی PostgreSQL (جداول `games`, `players`, `groups`).
- **Cache** (`app/cache/`): Redis برای state زندهٔ بازی (hash `game:{chat_id}` و ست‌های active).
- **Keyboards** (`app/keyboards/`): دکمه‌های inline عضویت.

---

## ۲. پیش‌نیازها و راه‌اندازی سامانه (launcher)

تنها entrypoint پروژه `onyx/launcher.py` است. ترتیب بوت (`main()` lines ~42-80):

1. `setup_loguru(...)` — لاگ‌گذاری.
2. `Gatekeeper().enforce()` — اعمال سخت‌گیرانه قوانین ساختار/استایل پروژه (mismatch ⇒ خطای بوت).
3. `get_settings()` — بارگذاری `.env` (`data/env/.env`) با pydantic و aliasهای UPPER_CASE.
4. `_ensure_db()` → `asyncio.run(app.database.bootstrap.ensure_schema())` — ساخت/مایگریشن اسکیمای PostgreSQL.
5. استارت FastAPI webapp در یک **ترید daemon** با uvicorn (`WEBAPP_HOST/WEBAPP_PORT`).
6. `run(settings)` در `app/main.py` — اجرای ربات تلگرام (polling) در ترد اصلی.

نکته: وب‌اپل فقط features اجتماعی/اقتصادی را دارد؛ **منطق بازی کاملاً داخل ربات است** و فرایند شروع بازی مستقل از وب‌اپ کار می‌کند.

---

## ۳. ثبت هندلرها و حلقه تیک (app/main.py)

### ۳.۱ ثبت فرمان‌های شروع

در `_register_handlers`:

```python
cmds = load_json(COMMANDS_JSON)          # data/config/commands.json
for command in cmds["start_commands"]:   # startgame, startmighty, ...
    app.add_handler(CommandHandler(command, start_game_entry))
app.add_handler(CommandHandler("start", start_payload_join))
```

یعنی هر ۸ فرمان حالتِ بازی به یک هندلر مشترک `start_game_entry` وصل‌اند و
`/start joinToGAME_<chat_id>` (دیپ‌لینک عضویت در PV) به `start_payload_join`.

سایر فرمان‌های مرتبط با لابی که همین‌جا ثبت می‌شوند:
`join`، `flee`، `forcestart`، `extend`، `players`، `killgame`، `modeinfo`،
`nextgame`، `startchallenge`، `challengeforce` (همه از `commands.json`).

### ۳.۲ post_init و حلقه تیک

`_post_init` پس از بالا آمدن ربات:

- `set_my_commands` (نام فرمان‌ها + forcestart/join/players/extend/killgame).
- ساخت تسک async `_tick_loop(app, TICK_INTERVAL_SECONDS)`.

`_tick_loop` هر دور (پیش‌فرض هر ۲ ثانیه):

```python
await _reconcile_legacy_ai(app)      # یک‌بار در ابتدای لوپ: تخلیه لابی‌های AI قدیمی
bridge = ChatBridge(app.bot)
await TimerManager(bridge).tick_all()   # ← موتور مرحله join (لابی)
await tick_end_checks(bridge)           # بررسی پایان بازی
await tick_active_nights(bridge)        # فاز شب
await tick_active_days(bridge)          # فاز روز
await tick_active_votes(bridge)         # فاز رأی
```

**«شروع بازی» یعنی همان رسیدن کنترل از `tick_all` به `InitialFlow`.**
خطاها در تیک لاگ می‌شوند (`phase_tick_failed`) و لوپ نمی‌میرد.

---

## ۴. پیکربندی‌های دکلراتیو دخیل در فرایند

| فایل | نقش در شروع بازی |
|---|---|
| `data/config/commands.json` | نگاشت `start_commands`: `/startgame→Normal`, `/startmighty→Mighty`, `/startwerewolf→WereWolf`, `/startmafia→Mafia`, `/starteasy→Easy`, `/startromantic→Romantic`, `/startvampire→Vampire`, `/startfoolish→Foolish`؛ نام فرمان‌های لابی؛ `start_payload_prefix = "joinToGAME_"` |
| `data/config/game_modes.json` | برای هر مود: `min_players` (پیش‌فرض ۶، Vampire=۷)، `command`، `start_text_key` (مثل `startAtGame_Normal`)، `needs_vampire_roles`، `skip_role_assign` |
| `data/config/game_phases.json` | کدهای عددی state (`NO_GAME=0, RUNNING=1, JOINING=2, CHALLENGE_JOINING=3`)، نام فازهای redis (`join/night/day/vote/challenge_join`)، `running_phases=[night,day,vote]`، `group_active_value="active"` |
| `data/config/redis_keys.json` | قالب کلیدها (`game:{chat_id}`, `active_join_chats`, `GamePl:join_user:{user_id}`, `GamePl:PlayerJoin:{user_id}` …) و **نام فیلدهای hash** (`timer`, `game_state`, `GamePl:Player_list`, `SetUpRoles`, `GamePl:Kill`, …) |
| `data/config/url_templates.json` | `join_deeplink` (دیپ‌لینک عضویت)، `user_mention_html`، `default_start_gif` |
| `data/config/warning_seconds.json` | پنجره‌های هشدار شمارش معکوس join (`min_left/max_left/seconds/unit_key/include_number`) |
| `data/config/roles.json`, `role_weights.json`, `role_fill.json`, poolهای مود | ورودی توزیع نقش (بخش ۱۳) |

`GameState` در زمان اجرا از JSON ساخته می‌شود:
`build_game_state_enum()` در `game_state_manager.py` — یعنی تغییر state‌ها فقط با config است.

---

## ۵. مدل داده‌ای: PostgreSQL و Redis

### ۵.۱ PostgreSQL (منبع هویت پایدار)

- `GameRow` (`app/database/models/game.py`): سطر هر بازی — `chat_id, mode, starter_id, created_at, status, started_at, day_count, night_count, state`. مقدار اولیه `status` = فاز `join`؛ `started_at` هنگام شروع واقعی ست می‌شود.
- `PlayerRow`: سطر هر بازیکن — `game_id, user_id, fullname, role=None` موقع join؛ هنگام توزیع نقش: `role, team, alive=True, state="alive"`.
- `GroupRow`: تنظیمات گروه — `status(active/inactive), lang, pin_player_message, allow_extend, allow_flee, vampire_role_on, bloodthirsty_role_on, sponsor_lock, settext_start, start_gif` و سقف بازیکن گروهی.

### ۵.۲ Redis (state زندهٔ لابی/بازی)

Hash مرکزی: `game:{chat_id}` با فیلدهایی که `RedisKeySpace.field()` نامشان را از config می‌خواند. مهم‌ترین‌ها در چرخه شروع:

| فیلد | معنا |
|---|---|
| `timer` | لحظه یونیکس پایان join (مطلق) |
| `game_state` | نام فاز فعلی (`join` → `night` → …) |
| `game_id` | شناسه سطر GameRow |
| `GamePl:gameModePlayer` | نام مود |
| `GamePl:StarterName` | نام نمایشی آغازگر |
| `GamePl:Player_list` / `GamePl:UserJoin` / `GamePl:NewUserJoin` | لیست JSON بازیکنان / uidها / اسامی تازه‌وارد (صف اطلاع‌رسانی) |
| `Player_ListMessage_ID` | message id پیام لیست بازیکنان (برای edit) |
| `EditMarkup` / `deleteMessage` | آرایه message idها برای ویرایش/پاکسازی پیام‌های موقت لابی |
| `GamePl:StartGameAt` | زمان ساخت لابی |
| `GamePl:SendStarterMessage` | پرچم «پیام آغازگر ارسال شد» |
| `SetUpRoles` | پرچم آنلاک نقش‌ها |
| `GamePl:StartNewGame` | قفل «join بسته شد» (ضد تکرار `_finish`) |
| `GamePl:time_update`, `GamePl:UserJoin` | هنگام finish حذف (hdel) می‌شوند |
| `GamePl:Kill` | kill_flag — شروع شدن بازی (سکوت killgame بعد از آن) |
| `GamePl:Challenge` | پرچم چالش |
| `day_count/night_count/timer_end` | شمارندها و تایمر فاز جاری |

کلیدهای مجاور: `active_join_chats` (SET چت‌های دارای لابی join — خوراک `tick_all`)،
`active_night_chats/day/vote`، `GamePl:join_user:{uid}` (کاربر در کدام لابی است)،
`GamePl:PlayerJoin:{uid}` (قفل ضددابل‌join با TTL ۱۵s)،
`game:{chat}:roles/players/flags/night_actions/night_sent/timer_end/night_count/day_count/next_game`.

---

## ۶. فاز A — فرمان آغاز (/startgame و خواهران)

فایل: `app/handlers/start_game.py`

### ۶.۱ `start_game_entry` (dispatch)

1. اگر `effective_user/effective_chat/message.text` نباشد ⇒ خروج بی‌صدا.
2. استخراج نام فرمان: `text.split()[0]`، حذف `/` و suffix بات (`@BotName`).
3. `mode = deps.mode_for_command(command)` — نگاشت از `commands.json["start_commands"]`.
4. فراخوانی `handle_start_game(update, context, mode)`.

### ۶.۲ `handle_start_game` — مراحل مرتب (معادل CM_StartGame)

این تابع **ترتیب دقیق گیت‌ها** را رعایت می‌کند؛ هر گیت در صورت رد، یا پیام می‌دهد یا بی‌صدا خارج می‌شود:

1. **State گروه**: `state_mgr().get_group_state(chat.id)`؛ اگر `GroupInactive` (گروه غیرفعال) ⇒ خروج بی‌صدا. سپس `ensure_group_active` — اگر رکورد گروه نیست، **خودکار با مقادیر پیش‌فرض ساخته می‌شود** (رویداد `group_auto_created`)؛ اگر inactive ⇒ خروج.
2. **زبان**: `deps.group_lang(group)` — عمداً زبان کلاینت تلگرام نادیده گرفته می‌شود تا پاسخ‌های EN به گروه FA نرود؛ همیشه `DEFAULT_LANG` (fa).
3. **Sponsor Lock**: اگر `group.sponsor_lock` ست باشد، فقط **sudo** یا دارندۀ `SponsorRow` فعال اجازه شروع دارد؛ وگرنه پیام `SponsorLockBlocked` (bundle lobby) و خروج.
4. **Ban**: `deps.ban_block` — اگر کاربر بن باشد، پیام بن در PV ارسال و خروج.
5. **PV ممنوع**: `game_filters.is_private` ⇒ پیام `GameStartOnGroup` (بازی فقط در گروه) و خروج.
6. **Dedupe بر اساس state**:
   - `RUNNING` ⇒ بی‌صدا return (بازی در جریان است).
   - `JOINING` ⇒ `_remind_join(challenge=False)`: دوباره پیام `startLastGame` + کیبورد عضویت در گروه، و id پیام در `deleteMessage` ثبت می‌شود.
   - `CHALLENGE_JOINING` ⇒ `_remind_join(challenge=True)` با متن `StartLastChallenge` و دکمه `JoinChallenge`.
7. در غیر این صورت (NO_GAME) ⇒ `_start_new(...)` — مسیر ساخت لابی (بخش ۷).

---

## ۷. فاز B — ساخت لابی

`_start_new` در `start_game.py` (branch کاربردیِ «ساخت بازی»):

1. **Setup نقش‌ها**: اگر `RoleSetupManager.is_setup_done(chat.id)` نباشد ⇒ `unlock_all_roles` (فیلد `SetUpRoles=1` در hash؛ رویداد `roles_unlocked`).
2. **گیت مود خون‌آشام**: اگر `info.needs_vampire_roles` (مود Vampire): `sync_role_toggles` روی فلگ‌های گروه (`vampire_role_on`, `bloodthirsty_role_on`, `kalantar`)؛ اگر همزمان روشن نبودند ⇒ پیام `DisabledVampireMode` و **بدون ساخت لابی** خروج.
3. **ساخت لابی**: `lobby.start_game_for_group(chat.id, mode, user.id, fullname)` → `game_id`.

### ۷.۱ `LobbyManager.start_game_for_group` (lobby_manager.py)

الف) در یک ترانزاکشن SQLAlchemy:
```python
row = GameRow(chat_id, mode, starter_id=user_id,
              created_at=now(UTC), status="join")   # phase از game_phases.json
session.add(row); await session.flush(); game_id = row.id
```

ب) در Redis — **پاک‌سازی و نو کردن hash**:
- `DELETE game:{chat_id}` (لابی قبلی) + `purge_legacy_ai_keys(chat_id)` (باقی‌مانده AI نسخه قبل).
- ست‌کردن mapping کامل hash:
  - `timer = now + JOIN_DURATION_SECONDS` (پیش‌فرض ۳۰۰ ثانیه)
  - `game_state = "join"`، `game_mode`، `game_id`، `GamePl:StarterName = fullname`
  - `GamePl:Player_list=[]`, `UserJoin=[]`, `NewUserJoin=[]`, `EditMarkup=[]`, `deleteMessage=[]`
  - `day_count=1`, `night_count=0` (هم‌زمان با keyهای جداگانه `game:{c}:day_count/night_count`)
- `SADD active_join_chats {chat_id}` ⇒ از این لحظه `tick_all` این چت را می‌بیند.
- رویداد `lobby_created`.

> توجه: سازندهٔ لابی هنوز به‌عنوان بازیکن **ثبت نشده است**؛ او هم باید مثل بقیه روی دکمه Join بزند (یا `/join` دیپ‌لینک را باز کند).

---

## ۸. فاز C — اعلام لابی در گروه

ادامهٔ `_start_new` بعد از ساخت لابی:

1. **صف Next Game**: `NextGameManager().announce_and_clear(...)` — اگر کاربرانی با `/nextgame` در صف `game:{c}:next_game` مانده باشند، پیام `NextGameList` (اسامی با کاما) ارسال و صف پاک می‌شود.
2. **دیپ‌لینک عضویت**: `deps.join_url(chat.id)` از قالب `url_templates.join_deeplink` + `BOT_USERNAME` + پیشوند `joinToGAME_`.
3. **کیبورد**: `build_join_keyboard` — یک دکمه URL با متن `joinToGame` (استایل `join_lobby`)؛ در حالت چالش متن `JoinChallenge`.
4. **کپشن شروع**:
   - mention سازنده با قالب `user_mention_html`.
   - متن `tm.get(info.start_text_key, lang, mention)` — مثلاً `startAtGame_Normal`.
   - الحاق `StartGameFooter` و در صورت وجود، `group.settext_start` (متن سفارشی گروه).
5. **ارسال گیف/انیمیشن**: `group.start_gif` یا `default_start_gif` از url_templates با `bridge.send_animation(caption, keyboard)`.
   - اگر بات اجازه گیف در گروه نداشته باشد (`BadRequest`) ⇒ پیام `NotBotEnableGifOnGroup` و fallback به متن ساده با همان کیبورد.
6. **ردیابی پیام**: id پیام انیمیشن/متن در فیلد `EditMarkup` hash ثبت می‌شود (`_track_edit`) — برای ویرایش‌های بعدی لابی.
7. **زمان شروع**: `GamePl:StartGameAt = int(time())`.
8. **پیام لیست بازیکنان**: متن `players_header_zero` («۰ بازیکن») ارسال و id آن در `Player_ListMessage_ID` ذخیره؛ اگر `group.pin_player_message` ⇒ pin (خطا نادیده).
9. رویداد `start_game` (با game_id، mode، phase=join).

از این لحظه لابی **JOINING** است و سه محرک می‌توانند آن را تمام کنند: تایمر، پرشدن ظرفیت، `/forcestart`.

---

## ۹. فاز D — مرحله پیوستن (join) و ۱۲ گام اعتبارسنجی

فایل: `app/handlers/join_game.py` — docstring صراحتاً می‌گوید «PHP joinToGAME_ 12 steps».

### ۹.۱ ورودی

- کاربر دکمه URL لابی را می‌زند → تلگرام در PV: `/start joinToGAME_<chat_id>`.
- `start_payload_join`: بدون args یا prefix نامعتبر ⇒ پیام `GameStartOnGroup`؛ وگرنه `chat_id` استخراج و `run_join_steps`.
- فرمان `/join` در گروه (`join_command`): فقط دیپ‌لینک را در PV کاربر می‌فرستد (راهنما، نه عضویت مستقیم).

### ۹.۲ گام‌های ترتیبی `run_join_steps`

| # | گام | شرط شکست | پیام/رفتار | رویداد |
|---|---|---|---|---|
| 1 | Ban | کاربر بن | پیام بن در PV | `join_fail_ban` |
| 2 | عضویت در گروه | `get_member_status ∈ {left,kicked}` ⇒ allow=0 | (مرحله ۴) | — |
| 3 | بازی موازی | `GamePl:join_user:{uid}` روی چت دیگری ست | `YouInGame` | `join_fail_other_game` |
| 4 | Allow | allow≤0 | `NotAllowToJoin` | `join_fail_allow` |
| 5 | نام تکراری | `name_taken` (casefold) در `Player_list` | `NotNameAllow` | `join_fail_name` |
| 6 | ظرفیت | count ≥ `max_players_of(group)` (limit گروهی یا `MAX_PLAYERS`) | `MaxPlayer(cap)` | `join_fail_max` |
| 7 | وجود بازی | hash `game:{c}` نیست | `NotFoundGameId` | `join_fail_missing` |
| 8 | زمان/فاز (silent) | `timer-now ≤ 0` یا state≠join | **بی‌صدا** return | — |
| 9 | قفل ضدتکرار | `SET GamePl:PlayerJoin:{uid} NX EX 15` نشد | بی‌صدا return | — |
| 10 | هزینه coin | (هوک فاز coin مود؛ `JOIN_COST_COINS` در settings تعریف شده ولی در این مسیر register فراخوانی نمی‌شود) | — | — |
| 11 | ثبت‌نام | `lobby.register_player` + `bump_if_late_join` | — | — |
| 12 | تأیید PV | `JoinTheGame(title گروه)` | — | `join_ok` |

### ۹.۳ `LobbyManager.register_player`

- در DB: `PlayerRow(game_id, user_id, fullname, role=None)`.
- در Redis hash: افزودن `{user_id, fullname}` به `GamePl:Player_list`، uid به `UserJoin`، نام به `NewUserJoin` (صف اطلاع‌رسانی که tick مصرف می‌کند).
- `SET GamePl:join_user:{uid} = chat_id`.
- رویداد `player_joined`.

### ۹.۴ تمدید اضطراری — `bump_if_late_join` (lobby_extend.py)

هر join موفق: اگر ≤۱۰ ثانیه به پایان timer مانده باشد ⇒ `apply_extend(+30s)`؛
`apply_extend` همیشه clamp می‌کند: حداقل `now+10` و سقف `JOIN_DURATION_SECONDS` جدید از now (و `delta` سقف `MAX_EXTEND_SECONDS` دارد).

### ۹.۵ سایر فرمان‌های لابی

- `/extend <ثانیه?>` (`handlers/extend.py`): تمدید با `EXTEND_DEFAULT_SECONDS` (۳۰) برای کاربران مجاز؛ همان clampها.
- `/flee` (`handlers/flee.py` + `lobby_unregister.unregister_lobby_player`): خروج از لابی join (حذف از Player_list/UserJoin، پاک‌کردن `join_user`).
- `/players`: لیست فعلی بازیکنان.
- `/killgame` (`handlers/kill_game.py`): لغو بازی — بعد از ست‌شدن `GamePl:Kill` (شروع بازی) دیگر اثر ندارد.
- `/config`: پنل تنظیمات گروه (pin player msg، gif شروع، vamp roles و…).

---

## ۱۰. فاز E — حلقه تایمر لابی (TimerManager.tick)

فایل: `app/managers/timer_manager.py` — معادل `join::Handel` در PHP.
`tick_all()` روی تک‌تک اعضای `active_join_chats` اجرا می‌شود (هر `TICK_INTERVAL_SECONDS`=۲s).

`tick(chat_id)`:

1. `hgetall game:{c}`؛ خالی ⇒ return.
2. اگر `GamePl:StartNewGame` ست باشد ⇒ return (لابی بسته/در حال شروع؛ ضد مسابقه).
3. `left = timer - now`؛ `log_debug_tick`.
4. **`_maybe_starter`**: اگر `GamePl:SendStarterMessage` ست نیست ⇒ پیام `StarterMessage(name آغازگر)` در گروه و ست‌کردن پرچم (یک‌بار).
5. **`_update_list_and_cap`**:
   - `update_player_list`: edit پیام `Player_ListMessage_ID` با `player_list_text` (هدر `player(count)` + mention HTML هر بازیکن).
   - `consume_new_joins` (خالی‌کردن `NewUserJoin`) ⇒ اگر تازه‌وارد هست:
     - `announce_player_joins`: پیام `PlayerJoined(name, count, min_players, max_players)` برای هر نفر؛ idها در `deleteMessage` ثبت (بعداً پاک می‌شوند).
     - `maybe_refresh_session_senior` (senior/ارشد نشست).
   - اگر `count >= cap` ⇒ `force_timer_end` (timer = now−5 ⇒ تیک بعدی finish می‌کند).
6. **`_warnings`**: `emit_join_warnings` — برای هر window در `warning_seconds.json` که `min_left ≤ left ≤ max_left` ⇒ پیام `OnlyJoinTheGameTime(unit)` + کیبورد join؛ پیام‌ها track-delete می‌شوند.
7. اگر `left <= 0` ⇒ **`_finish`**.

---

## ۱۱. فاز F — پایان join و تصمیم سرنوشت لابی

`_finish_body(chat_id, lang)` — قلب تصمیم‌گیری «شروع یا انصراف»:

1. **قفل**: `HSET GamePl:StartNewGame=1`؛ `HDEL time_update, UserJoin`.
2. خواندن `game_mode` و `GameModeInfo`.
3. `drop_ai_members` (پاکسازی AI legacy؛ در صورت وجود رویداد `ai_legacy_reconciled`).
4. **Debug fill**: اگر `DEBUG_MODE` و `0 < count < min_players` ⇒ `fill_debug_players` (بازیکنان شبح `DebugBotN` با uid منفی register می‌شوند).
5. `update_player_list` نهایی + `_flush_deletes` (پاک‌کردن همه پیام‌های tracked لابی: اطلاع‌رسانی join، هشدارها، یادآوری‌ها).
6. **شعبه کمبود بازیکن** (`count < info.min_players`):
   - `close_lobby(reason="join")`: DELETE hash + SREM از `active_join_chats` (رویداد `lobby_closed`).
   - پیام `NotStartGameForPlayer` در گروه.
   - رویداد `join_failed_count` ⇒ **بازی شروع نمی‌شود** و state به NO_GAME برمی‌گردد.
7. در غیر این صورت ⇒ `InitialFlow.start_initial_flow(chat_id, lang)` (بخش بعدی).

`/forcestart` (`handlers/force_start.py`): نیازمند `is_admin`؛ فقط در state `JOINING`؛
timer := now−1 و بلافاصله `TimerManager.finish_join` (همین `_finish_body`).
در حالت RUNNING بی‌صدا و در NO_GAME پیام `GameNotCreate`.

---

## ۱۲. فاز G — جریان اولیه شروع بازی (InitialFlow)

فایل: `app/managers/initial_flow.py` — معادل `GameStarted` در PHP.
`start_initial_flow(chat_id, lang)`:

1. خواندن `game_id` از hash.
2. **DB**: `GameRow.started_at = utcnow()` (مهر زمان رسمی شروع).
3. **Redis**: `GamePl:Kill = "1"` — از این لحظه `/killgame` بی‌اثر/خاموش است.
4. پیام گروه: `GameStart` («بازی آغاز شد»).
5. خواندن `game_mode` → `GameModeInfo`.
6. `SREM active_join_chats {chat_id}` — لابی از دید tick_all حذف می‌شود (دور بعدی tick دیگر وارد نمی‌شود).
7. اگر `not info.skip_role_assign`:
   ```python
   try: await self._roles.assign_roles(chat_id)
   except RoleBalanceError:
       پیام "ErrorStartGame_Balance" در گروه
       close_lobby(reason="balance_failed")   # بازی نمی‌چرخد
       return
   ```
8. پیام `GameStarted` (bundle night) و رویداد `initial_flow_done`.

** تزریق وابستگی (Wiring)**: سازنده `InitialFlow` در `__init__` تابع
`wire_role_assignment(bridge, roles)` (از `flow_wiring.py`) را صدا می‌زند که hook واقعی
`assign_roles` را می‌سازد:

```python
async def _assign(chat_id):
    mode  = hget game:{c} GamePl:gameModePlayer or "Normal"
    players = LobbyManager().list_players(chat_id)
    night = NightManager(bridge)
    dist = RoleDistributionManager()
    dist.set_night_starter(night.start_first_night)   # ← زنجیره شروع شب
    await dist.distribute_roles(chat_id, mode, players)
```

---

## ۱۳. فاز H — توزیع نقش‌ها (RoleDistributionManager)

فایل: `app/managers/role_distribution_manager.py` (+ `role_pool_filter`, `role_balance`,
`role_pairs`, `role_forced`, `role_pool_fillers`, `class/roles/registry`).

`distribute_roles(chat_id, mode, players)` — الگوریتم مرحله‌ای:

1. **مود Foolish**: مسیر ویژه — `foolish_roles(n)`، shuffle، assign، سپس `start_first_night` و خروج.
2. **انتخاب استخر**: `load_mode_pool(mode, n)` (pool نقش‌های مود متناسب با تعداد بازیکن) و `lookup_wolf_count(n)` (تعداد گرگ بر اساس جدول اندازه بازی).
3. **`_priority_select`**: اول تا `wolf_n` گرگ (رعایت unique)، سپس محاسبه سهم ویژه‌ها:
   `special_n = max(min_specials, n − wolf_n − max(min_villagers, n·max_villager_ratio))` از `role_fill.json`؛ کاندیداها (unique/support غیرگرگ) shuffle و پر کردن.
4. **`append_end_fillers` / `inject_vampires`**: نقش‌ انتهایی و خون‌آشام‌ها طبق مود/گروه.
5. **`_slice_roles`**: برش/پرکردن دقیقاً به `n` (گرگ‌ها اولویت؛ کمبود با `role_villager` پر می‌شود).
6. **`force_role_pairs`**: جفت‌های اجباری (مثلاً قفل‌های نقش‌ای `role_links`).
7. **`balance_roles`**: توازن تیمی با وزن‌های `role_weights.json` و سقف تلاش `ROLE_BALANCE_MAX_ATTEMPTS` (۵۵۰) و `BALANCE_TOLERANCE` (۵) — شکست ⇒ `RoleBalanceError` ⇒ لابی با `balance_failed` بسته می‌شود.
8. **shuffle نهایی** با `SystemRandom` و `_assign(players, roles)` (zip با `strict=True` — تعداد نقش باید دقیقاً برابر بازیکن باشد).

### ۱۳.۱ `_assign` — نوشتن نتایج

برای هر بازیکن:
- DB `PlayerRow`: `role, team, alive=True, state="alive"` (و تکمیل name).
- Redis: `player:{uid}:role`، `player:{uid}:state=alive`.
- سپس: `game:{c}:roles` (JSON map uid→role)، `game:{c}:players` (snapshot کامل).
- seed کتاب‌های جوکر؛ اگر `role_dynamite` در بازی ⇒ ست‌اپ `bomber_parts/dinamit_*` در flags؛ اگر `role_BlackKnight` ⇒ `black_knight_hits=0`.
- **`village_links_pending=1`** در flags (برای DM لینک‌های ماسون/ناظر در اولین شب).
- رویداد `roles_assigned`.

---

## ۱۴. فاز I — آغاز اولین شب (NightManager)

فایل: `app/managers/night_manager.py`.

### ۱۴.۱ `start_first_night(chat_id)`

- ریست شمارندها: `day_count=1`, `night_count=0` (هم keyهای جدا، هم فیلدهای hash، هم ستون‌های GameRow) — مستند: «doc: day_count=1, night_count=0 at game start».
- `gunner_bullets=2` در `game:{c}:flags`.
- فراخوانی `start_night(chat_id)`.

### ۱۴.۲ `start_night(chat_id)`

1. `GameStateManager.set_phase(chat_id, "night")` ⇒ `game_state="night"` (رویداد `phase_change`) — از این لحظه `get_group_state` مقدار **RUNNING** می‌دهد؛ دوباره `/startgame` زدن بی‌صدا رد می‌شود.
2. همگام‌سازی `GameRow.state/status = "night"`.
3. بررسی flags شب‌های قبل:
   - `sleep_next_night` ⇒ امشب **بدون DM/عملیات** (duration=0) مگر Blood Moon override (G17).
   - `silver_next_night` → فعال‌سازی `silver_active`؛ `mast_block_next` → `mast_block`.
4. `duration = NIGHT_DURATION_SECONDS` (۶۰) — یا ۰ در شب خواب.
5. پیام گروه: خلاصه فاز `MassgeFortypeSummery_night(duration)` + `announce_roster` (لیست بازیکنان زنده).
6. پاک‌سازی `night_sent` و `night_actions`؛ load players از snapshot.
7. `activate_blood_moon_night` (اگر برنامه‌ریزی شده باشد).
8. **DM نقش‌ها** (اگر شب خواب نیست): به‌صورت parallel `NightDmSender.send_role_dm` برای هر بازیکن زنده — هر بازیکن نقش خود را در PV می‌گیرد؛ سپس در صورت `village_links_pending`: `notify_mason_links` و `notify_nazer_seer` و حذف پرچم.
9. **آرم تایمر شب**: `SET game:{c}:timer_end = now+duration` (+ فیلد `timer_end` در hash) و `SADD active_night_chats {c}` — از دور بعدی `_tick_loop`، `tick_active_nights` رسیده بودن تایمر را چک و فاز شب را resolve می‌کند (`night_resolver`).
10. رویداد `night_started`.

**⇒ نقطه پایان سوال کاربر: بازی رسماً در فاز night (RUNNING) وارد گیم‌پلی می‌شود.**
از اینجا به بعد چرخه شب→روز→رأی توسط `phase_ticker` و resolverها اداره می‌شود (خارج از دامنه این داکیومنت).

---

## ۱۵. مسیرهای فرعی و جایگزین شروع

| مسیر | فایل | تفاوت کلیدی |
|---|---|---|
| **Challenge** | `handlers/challenge.py` (`/startchallenge`, `/challengeforce`) | لابی با state `challenge_join` + فیلد `GamePl:Challenge`؛ state=`CHALLENGE_JOINING`؛ دکمه `JoinChallenge`؛ force مشابه forcestart |
| **مود Vampire** | start_game.py گیت ۲ بخش ۷ | min_players=۷؛ نیازمند روشن‌بودن vampire+bloodthirsty در گروه |
| **مود Foolish** | role_distribution | بدون balance عادی؛ نقش‌های ویژه fool |
| **Debug mode** | `_finish_body` step 4 | پرکردن اتوماتیک با DebugBotهای شبح تا min_players |
| **AI legacy reconcile** | `ai_reconcile.py` + `_tick_loop` شروع | لابی‌های AI قدیمی هنگام بوت drain می‌شوند؛ `drop_ai_members` در finish |
| **Next Game queue** | `next_game_manager.py` | `/nextgame` بین دو بازی؛ announce در ساخت لابی بعدی |
| **Skip role assign** | `game_modes.json.skip_role_assign` | مودهایی که InitialFlow بدون توزیع نقش عبور می‌کند (در config فعلی همه false) |

---

## ۱۶. خطاها، حالت‌های مرزی و رفتارهای سکوت

- **GroupInactive** (استثنای `game_state_manager`): تقریباً همه هندلرها در این حالت **بی‌صدا** exit می‌کنند (رفتار عادت‌شده از PHP).
- **Race دو `/startgame` همزمان** روی NO_GAME: هر دو ممکن است `_start_new` بروند؛ دومی با `DELETE+rewrite hash` اولی را overwrite می‌کند (game_id دوم برنده؛ سطر GameRow اول orphan با status join می‌ماند).
- **Double join**: قفل `GamePl:PlayerJoin:{uid}` (NX/EX ۱۵s) + چک `join_user`.
- **Join بعد از اتمام timer**: گام ۸ silent return — هیچ پیامی داده نمی‌شود.
- **ضدتکرار finish**: فیلد `GamePl:StartNewGame` در ابتدای `_finish_body` و early-return در `tick`.
- **RoleBalanceError**: تنها خطای قابل‌مشاهده در شروع — پیام `ErrorStartGame_Balance` + `close_lobby(balance_failed)`.
- **BadRequest گیف**: fallback به متن + اطلاع‌رسانی `NotBotEnableGifOnGroup`.
- **Pin fail**: نادیده گرفته (try/except pass).
- **خطای edit لیست بازیکنان**: silent return در `update_player_list`.
- **`zip(strict=True)` در `_assign`**: اگر تعداد نقش≠بازیکن ⇒ `ValueError` (باید هرگز رخ ندهد؛ `_slice_roles` تضمین می‌کند).
- **Restart بات وسط لابی**: state در Redis زنده است؛ `tick_all` از `active_join_chats` ادامه می‌دهد؛ فقط پیام‌های trackشده ممکن است جا بمانند.

---

## ۱۷. رویدادهای ثبت‌شده (log_game_event)

ترتیب تقریبی در یک چرخه سالم (قابل‌ردیابی در لاگ):

```
group_auto_created? → roles_unlocked → lobby_created → start_game
→ player_joined (×N) → [join_ok ×N | join_fail_*]
→ StarterMessage-related: (none; flag only)
→ lobby lifecycle end:
   join_failed_count → lobby_closed            (شکست)
   یا: ai_legacy_reconciled? → roles_assigned → initial_flow_done
        → phase_change(night) → night_started   (موفق)
```

همچنین `log_debug_tick` برای هر تیک join (در debug)، و `debug_fill_players`.

---

## ۱۸. جدول متغیرهای محیطی مؤثر

(تعریف: `app/config/settings.py`؛ نمونه: `data/env/example.env`)

| متغیر | پیش‌فرض example | کاربرد در این فرایند |
|---|---|---|
| `JOIN_DURATION_SECONDS` | 300 | طول اولیه join + سقف apply_extend |
| `TICK_INTERVAL_SECONDS` | 2 | دوره تیک TimerManager |
| `MAX_PLAYERS` | 60 | سقف پیش‌فرض لابی (بدون limit گروهی) |
| `EXTEND_DEFAULT_SECONDS` | 30 | گام پیش‌فرض `/extend` و bump اضطراری |
| `MAX_EXTEND_SECONDS` | 300 | clamp delta تمدید |
| `JOIN_COST_COINS` | 10 | تعرفه coin (تعریف‌شده؛ در مسیر join فعلی charge نمی‌شود) |
| `DEBUG_MODE` | false | debug fill + لاگ verbose + هندلر cmd_seen |
| `NIGHT_DURATION_SECONDS` | 60 | طول اولین شب |
| `ROLE_BALANCE_MAX_ATTEMPTS` | 550 | سقف تلاش balance_roles |
| `BALANCE_TOLERANCE` | 5 | تلورانس توازن تیمی |
| `DEFAULT_LANG/FALLBACK_LANG` | fa/en | همه متن‌های این مسیر |
| `BOT_USERNAME` | — | ساخت دیپ‌لینک join |
| `SUDO_IDS` | — | دورزدن sponsor_lock |

---

## ۱۹. نمودار توالی کامل (ASCII)

```
User(group)      Bot Process(main.py/_tick_loop)        Redis                PostgreSQL
──────────       ───────────────────────────────        ─────                ──────────
/startgame ────▶ start_game_entry
                 handle_start_game: gates(sponsor/ban/PV/state)
                 _start_new:
                   unlock_all_roles ───────────────────▶ SetUpRoles=1
                   sync vampire toggles (Vampire mode)
                   start_game_for_group ───────────────▶ DEL+HMSET game:{c}(timer,state=join)
                                                   SADD active_join_chats   INSERT games(status=join)→id
                   NextGame announce/clear
                   send GIF+JoinBtn / text ── msg ids ─▶ EditMarkup
                   players-zero msg ───────────────────▶ Player_ListMessage_ID
◀── lobby messages ──┘                            log: lobby_created,start_game

JoinBtn(URL) ─▶ /start joinToGAME_c (PV)
                 run_join_steps 1..12
                 register_player ──────────────────▶ Player_list+=…, join_user
                                                   SET lock 15s      INSERT players(role=NULL)
◀── JoinTheGame(PV)                          log: player_joined, join_ok

(tick every 2s) TimerManager.tick_all:
                 StarterMessage(once) / edit list / joins announce / warnings
                 full-capacity → force_timer_end
                 left<=0 → _finish_body:
                   StartNewGame=1, flush deletes
                   count<min? ─yes→ close_lobby + NotStartGame ─▶ NO_GAME
                   no ↓
                 InitialFlow.start_initial_flow:
                   started_at=now ─────────────────────────────────UPDATE games
                   Kill=1, msg GameStart, SREM active_join_chats
                   wire→ distribute_roles:
                     pool→wolves→specials→fillers→pairs→balance→shuffle
                     _assign ─▶ game:c:roles/players, player:* keys  UPDATE players(role,team,alive)
                   start_first_night:
                     day=1,night=0, gunner=2
                     start_night: set_phase(night)──▶ game_state=night (RUNNING)
                       summary+roster(msg group)
                       role DMs(PV) + mason/nazer links
                       timer_end=now+60, SADD active_night_chats
                     ◀── night_started ── tick_active_nights continues the loop
```

---

## ۲۰. چک‌لیست تست دستی end-to-end

1. `.env` را با REDIS/PG بالا بیاور؛ `python -u launcher.py`؛ لاگ `bot_polling_start`.
2. ربات را ادمین گروه کن؛ `/startgame` → پیام گیف+دکمه Join، پیام «۰ بازیکن»، لاگ `lobby_created`.
3. چند اکانت/دیپ‌لینک join → پیام‌های PlayerJoined و edit لیست؛ `/players` درست است.
4. `/extend 60` و join دیرهنگام (≤10s) → bump خودکار؛ سقف JOIN_DURATION رعایت شود.
5. با ۵ بازیکن صبر تا تایمر → `NotStartGameForPlayer` + lobby_closed (min=6).
6. با ≥۶ بازیکن `/forcestart` → GameStart → GameStarted؛ DM نقش برای همه؛ پیام شب+تایمر ۶۰s؛ `get_group_state=RUNNING`؛ `/startgame` مجدد بی‌صدا.
7. `/killgame` بعد از شروع → بی‌اثر (Kill flag).
8. `DEBUG_MODE=true` با ۲ بازیکن forcestart → DebugBotها پر شوند و بازی شروع شود.
9. گروه با `sponsor_lock` → کاربر غیراسپانسر: `SponsorLockBlocked`.
10. `/startvampire` در گروهی با vampire_role_off → `DisabledVampireMode`.

---

### ارجاعات سریع به کد

- `app/handlers/start_game.py` (320 خط) — آغاز و ساخت لابی
- `app/managers/lobby_manager.py` (341) — ساخت/ثبت‌نام/تایمر لابی
- `app/handlers/join_game.py` (234) — ۱۲ گام join
- `app/managers/timer_manager.py` (346) — تیک join و finish
- `app/managers/initial_flow.py` (113) — GameStarted
- `app/managers/flow_wiring.py` — اتصال assign hook به شب
- `app/managers/role_distribution_manager.py` (335) — توزیع نقش
- `app/managers/night_manager.py` (350) — اولین شب
- `app/managers/game_state_manager.py` (184) — ماشین حالت گروه
- `app/main.py` (400) — ثبت هندلرها و `_tick_loop`
- `launcher.py` — بوت چهارمرحله‌ای

*پایان داکیومنت — تهیه‌شده از مطالعه مستقیم سورس مخزن، بدون فرضیات خارج از کد.*
