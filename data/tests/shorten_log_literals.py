"""Shorten the two remaining >40-char log literals by shortening the message text."""
import re

# main.py: shorten context suffix
p = "app/main.py"
s = open(p, encoding="utf-8").read()
old = '"phase_tick_failed"\n                " err={err}"\n                " step=end/nights/days/votes",'
new = '"phase_tick_failed"\n                " err={err}",'
assert old in s, "main anchor missing"
open(p, "w", encoding="utf-8").write(s.replace(old, new))

# night_announce: shorten message
p2 = "app/managers/night_announce.py"
s2 = open(p2, encoding="utf-8").read()
old2 = '"night_announce"\n        " group_keys={g} dm_count={d}",'
new2 = '"night_announce"\n        " g={g} dm={d}",'
assert old2 in s2, "announce anchor missing"
open(p2, "w", encoding="utf-8").write(s2.replace(old2, new2))
print("shortened both")
