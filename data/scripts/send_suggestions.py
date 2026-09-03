import urllib.request, urllib.parse, json, sys
from pathlib import Path

env = Path.home() / "AppData/Local/hermes/profiles/nix/.env"
tok = None
for l in env.read_text("utf-8").splitlines():
    if l.startswith("TELEGRAM_BOT_TOKEN="):
        tok = l.split("=",1)[1].strip(); break
if not tok: print("NO TOKEN"); sys.exit(1)

CHAT = "-1002763212841"

msgs = [
"📋 پیشنهاد اصلاح پیام‌های بات (۱/۵)\n\n۱. startAtGame_*\n\n❌ الان:\nخب یه بازی توسط {0} ساخته شده فراموش نکنید که روی کادر زیر کلیک کنید تا بتونید وارد بازی شید\n\n✅ پیشنهاد:\n🐺 بازی ورولفی\nتوسط {0} ساخته شد\n\nروی دکمه زیر بزن تا وارد روستا بشی ⬇️\n\n📌 جمله بلند + تفاوت حالت‌ها محو شده",

"📋 پیشنهاد اصلاح پیام‌های بات (۲/۵)\n\n۲. PlayerJoined\n\n❌ الان:\nخب خوش اومدی {0} ما الان {1} نفر بازیکن داریم که حداقل باید {2} تا باشن و حداکثر {3} تا\n\n✅ پیشنهاد:\n🎮 خوش اومدی {0}!\nبازیکنان: {1}/{3}\nحداقل: {2} نفر\n\n📌 ۴ متغیر در یک خط → خوانایی پایین",

"📋 پیشنهاد اصلاح پیام‌های بات (۳/۵)\n\n۳. GameStart\n\n❌ الان:\nایول🤖 بازی شروع شد، نقشِتون رو توی پیوی براتون میفرستم\n\n✅ پیشنهاد:\n🌙 شب فرا رسید...\n🐺 بازی با {0} بازیکن شروع شد!\nنقش‌ها رو توی پیوی میفرستم...\n⏳ چند لحظه صبر کن...\n\n📌 هیجان + انتظار مدیریت شد",

"📋 پیشنهاد اصلاح پیام‌های بات (۴/۵)\n\n۴. NotStartGameForPlayer\n\n❌ الان:\nچقدر کمین! من با این تعداد بازیکن بازی رو شروع نمیکنم 😢\n\n✅ پیشنهاد:\n⚠️ بازیکن کمتر از حد نیازه!\nحداقل ۵ نفر لازمه.\nدوستاتونو دعوت کنید 🙋‍♂️\n\n📌 تعداد حداقل مشخص + فراخوان به اقدام",

"📋 پیشنهاد اصلاح پیام‌های بات (۵/۵)\n\n۵. ErrorStartGame_Balance\n\n❌ الان:\nمتاسفانه نتونستم بالانس بازی رو برقرار کردم، با عرض پوزش لطفا مجددا بازی جدید ایجاد کنید امیدوارم مشکلی پیش نیاد.\n\n✅ پیشنهاد:\n⚠️ بالانس نقش‌ها برقرار نشد.\nلطفاً بازی جدیدی شروع کنید.\n\n📌 کوتاه‌تر، واضح‌تر\n\n———\nکدوما رو اعمال کنم؟"
]

ok = 0
for i, m in enumerate(msgs):
    d = urllib.parse.urlencode({"chat_id": CHAT, "text": m}).encode()
    r = urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", d))
    j = json.loads(r.read())
    if j.get("ok"): ok += 1
    print(f"{'✅' if j.get('ok') else '❌'} {i+1}")

print(f"\n{ok}/5 sent")
