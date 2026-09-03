#!/bin/bash
# اسنپ‌شات روزانه پروفایل + پروژه اونیکس
# خروجی: ~/Project/onyx/_textwork/snapshots/
set -u
OUT=~/Project/onyx/_textwork/snapshots
mkdir -p "$OUT"
STAMP=$(date +%Y%m%d-%H%M)

# 1) پروژه (بدون بیلدآرتیفکت و بدون خودِ اسنپ‌شات‌ها)
tar czf "$OUT/project-$STAMP.tar.gz" \
  --exclude=node_modules --exclude=__pycache__ --exclude=.venv \
  --exclude=_textwork/snapshots \
  -C ~/Project onyx

# 2) پروفایل (کانفیگ+سکرت+مهارت‌های واقعی+مموری+دیتابیس سشن؛ بدون کش و بک‌آپ curator)
tar czf "$OUT/profile-$STAMP.tar.gz" \
  --exclude=skills/.curator_backups --exclude=skills/.hub \
  --exclude='*-shm' --exclude='*-wal' --exclude='*.lock' \
  --exclude=cache --exclude=logs \
  -C ~ .hermes/config.yaml .hermes/.env .hermes/profile.yaml \
  .hermes/agent.md .hermes/SOUL.md .hermes/skills .hermes/memories \
  .hermes/profiles .hermes/state.db

# 3) هرت بیشتر از ۷ روز رو پاک کن
find "$OUT" -name '*.tar.gz' -mtime +7 -delete
ls -lh "$OUT"
