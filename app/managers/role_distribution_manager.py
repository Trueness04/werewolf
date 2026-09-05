"""Role distribution (PHP UserRole / balance)."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import (
    ROLE_FILL,
    ROLE_WEIGHTS,
)
from app.config.settings import Settings, get_settings
from app.database.models.player import PlayerRow
from app.database.session import session_scope
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.role_balance import balance_roles
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class RoleDistributionManager:
    """Build balanced role list and assign players."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
        settings: Settings | None = None,
        night_starter: Any | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()
        self._settings = settings or get_settings()
        self._registry = _Registry()
        self._rng = SystemRandom()
        self._night_starter = night_starter
        self._weights = {
            str(k): int(v)
            for k, v in load_json(ROLE_WEIGHTS).items()
        }

    def set_night_starter(self, starter: Any) -> None:
        """Inject night_manager.start_first_night."""
        self._night_starter = starter

    async def distribute_roles(
        self,
        chat_id: int,
        mode: str,
        players: list[dict[str, Any]],
    ) -> None:
        """Full distribution + first night start."""
        log_game_event(
            "role_dist_start",
            chat_id=chat_id,
            mode=mode,
            count=len(players),
        )
        if mode == "Foolish":
            from app.managers.role_mode_specials import (
                foolish_roles,
            )

            roles = foolish_roles(len(players))
            self._rng.shuffle(roles)
            await self._assign(chat_id, players, roles)
            if self._night_starter is not None:
                await self._night_starter(chat_id)
            return
        from app.managers.role_pool_filter import (
            load_mode_pool,
            lookup_wolf_count,
        )

        pool = load_mode_pool(mode, len(players))
        wolf_n = lookup_wolf_count(len(players))
        selected = self._priority_select(
            pool,
            wolf_n,
            len(players),
        )
        from app.managers.role_pool_fillers import (
            append_end_fillers,
            inject_vampires,
        )

        selected = append_end_fillers(
            selected,
            len(players),
            mode,
            feramason_on=False,
            rosta_on=False,
        )
        selected = inject_vampires(
            selected,
            len(players),
            mode,
        )
        roles = self._slice_roles(selected, len(players))
        from app.managers.role_forced import (
            force_role_pairs,
        )

        roles = force_role_pairs(roles, self._rng)
        roles = balance_roles(
            roles,
            defs=self._registry.all_definitions(),
            weights=self._weights,
            settings=self._settings,
        )
        roles = await self._avoid_repeats(
            players,
            roles,
        )
        self._rng.shuffle(roles)
        await self._assign(chat_id, players, roles)
        if mode == "Romantic":
            from app.managers.role_mode_specials import (
                romantic_pairs,
            )

            await romantic_pairs(
                chat_id,
                players,
                self._keys,
            )
        if self._night_starter is None:
            return
        await self._night_starter(chat_id)

    def _priority_select(
        self,
        pool: list[str],
        wolf_n: int,
        need: int,
    ) -> list[str]:
        """Select wolves, then shuffled specials."""
        defs = self._registry.all_definitions()
        fill = load_json(ROLE_FILL)
        chosen: list[str] = []
        used: set[str] = set()

        def wolves() -> int:
            return sum(
                1
                for r in chosen
                if defs[r]["team"] == "wolf"
            )

        for rid in pool:
            if wolves() >= wolf_n:
                break
            if defs[rid].get("team") != "wolf":
                continue
            if defs[rid].get("unique") and rid in used:
                continue
            chosen.append(rid)
            used.add(rid)
        while wolves() < wolf_n and "role_wolf" in pool:
            chosen.append("role_wolf")
        max_v = max(
            int(fill["min_villagers"]),
            int(need * float(fill["max_villager_ratio"])),
        )
        special_n = max(
            int(fill["min_specials"]),
            need - wolf_n - max_v,
        )
        special_n = min(special_n, need - len(chosen))
        candidates: list[str] = []
        for rid in pool:
            info = defs[rid]
            if info.get("team") == "wolf":
                continue
            if rid in used:
                continue
            if info.get("unique") or info.get(
                "support_role"
            ):
                candidates.append(rid)
                if info.get("unique"):
                    used.add(rid)
        self._rng.shuffle(candidates)
        for rid in candidates[: max(special_n, 0)]:
            if len(chosen) >= need:
                break
            chosen.append(rid)
        return chosen

    async def _avoid_repeats(
        self,
        players: list[dict[str, Any]],
        roles: list[str],
    ) -> list[str]:
        """Swap roles so fewer players repeat last role.

        Greedy: for each player whose assigned role equals
        their previous game role, find a swap partner whose
        role differs from both players' last roles.
        Wolves stay wolves (swap within same team).
        """
        redis = await get_redis()
        defs = self._registry.all_definitions()
        last: dict[int, str] = {}
        for player in players:
            uid = int(player["user_id"])
            raw = await redis.get(
                self._keys.player_last_role(uid)
            )
            if raw:
                last[uid] = str(raw)
        if not last:
            return roles
        for i, player in enumerate(players):
            uid = int(player["user_id"])
            if uid not in last or roles[i] != last[uid]:
                continue
            if self._try_pairwise_swap(
                i, players, roles, last, defs
            ):
                continue
            # Pairwise swap has a gap: if the only same-team
            # partner also can't take role[i] (or would hand
            # i back its own last role), the repeat survives.
            # A 3-way rotation covers that case.
            self._try_rotation_swap(
                i, players, roles, last, defs
            )
        return roles

    def _try_pairwise_swap(
        self,
        i: int,
        players: list[dict[str, Any]],
        roles: list[str],
        last: dict[int, str],
        defs: dict[str, Any],
    ) -> bool:
        """Try swapping player i's role with one later player."""
        uid = int(players[i]["user_id"])
        for j in range(i + 1, len(players)):
            other = int(players[j]["user_id"])
            ri, rj = roles[i], roles[j]
            if rj == last.get(other, rj):
                continue
            if rj == last[uid]:
                continue
            if defs[ri]["team"] != defs[rj]["team"]:
                continue
            roles[i], roles[j] = rj, ri
            return True
        return False

    def _try_rotation_swap(
        self,
        i: int,
        players: list[dict[str, Any]],
        roles: list[str],
        last: dict[int, str],
        defs: dict[str, Any],
    ) -> bool:
        """3-way rotation: i<-j<-k<-i, same team, no repeats.

        Used when pairwise swap fails because i's only
        same-team partner(s) would either hand i back its
        own last role or would themselves repeat.
        """
        uid = int(players[i]["user_id"])
        team = defs[roles[i]]["team"]
        same_team_idx = [
            idx
            for idx in range(len(roles))
            if idx != i and defs[roles[idx]]["team"] == team
        ]
        for j in same_team_idx:
            rj_uid = int(players[j]["user_id"])
            if roles[j] == last[uid]:
                continue
            for k in same_team_idx:
                if k == j:
                    continue
                rk_uid = int(players[k]["user_id"])
                if roles[i] == last.get(rk_uid, ""):
                    continue
                if roles[k] == last.get(rj_uid, ""):
                    continue
                roles[i], roles[j], roles[k] = (
                    roles[j],
                    roles[k],
                    roles[i],
                )
                return True
        return False

    def _slice_roles(
        self,
        selected: list[str],
        need: int,
    ) -> list[str]:
        """Trim/pad exactly; keep wolves first."""
        defs = self._registry.all_definitions()
        wolves = [
            r for r in selected
            if defs.get(r, {}).get("team") == "wolf"
        ]
        others = [
            r for r in selected
            if defs.get(r, {}).get("team") != "wolf"
        ]
        out: list[str] = []
        seen: set[str] = set()
        for rid in wolves + others:
            info = defs.get(rid, {})
            if info.get("unique") and rid in seen:
                continue
            out.append(rid)
            if info.get("unique"):
                seen.add(rid)
            if len(out) >= need:
                break
        while len(out) < need:
            out.append(self._pad_role(out))
        return out[:need]

    def _pad_role(self, current: list[str]) -> str:
        """Pick a low-weight rosta filler for an empty seat.

        Uses balance_fallback_roles, skipping uniques that
        are already picked; role_villager only as the very
        last resort if nothing usable remains.
        """
        defs = self._registry.all_definitions()
        fill = load_json(ROLE_FILL)
        pool = list(
            fill.get(
                "balance_fallback_roles",
                ["role_villager"],
            )
        )
        usable = [
            rid
            for rid in pool
            if rid in self._weights
            and defs.get(rid, {}).get("team")
            == "villager"
            and not (
                defs.get(rid, {}).get("unique")
                and rid in current
            )
        ]
        if usable:
            return self._rng.choice(usable)
        return "role_villager"

    async def _assign(
        self,
        chat_id: int,
        players: list[dict[str, Any]],
        roles: list[str],
    ) -> None:
        """Persist role assignment to DB + Redis."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        game_id = int(
            await redis.hget(
                key,
                self._keys.field("game_id"),
            )
            or "0"
        )
        roles_map: dict[str, str] = {}
        async with session_scope() as session:
            for player, role_id in zip(
                players,
                roles,
                strict=True,
            ):
                uid = int(player["user_id"])
                info = self._registry.definition(role_id)
                team = str(info["team"])
                stmt = select(PlayerRow).where(
                    PlayerRow.game_id == game_id,
                    PlayerRow.user_id == uid,
                )
                row = (
                    await session.execute(stmt)
                ).scalar_one_or_none()
                if row is not None:
                    row.role = role_id
                    row.team = team
                    row.alive = True
                    row.state = "alive"
                    if not player.get("name"):
                        player["name"] = str(
                            row.fullname or uid
                        )
                player["name"] = str(
                    player.get("name")
                    or player.get("fullname")
                    or uid
                )
                roles_map[str(uid)] = role_id
                await redis.set(
                    self._keys.player_role(uid),
                    role_id,
                )
                await redis.set(
                    self._keys.player_last_role(uid),
                    role_id,
                )
                await redis.set(
                    self._keys.player_state(uid),
                    "alive",
                )
        await redis.set(
            self._keys.game_roles(chat_id),
            json.dumps(roles_map),
        )
        await redis.set(
            self._keys.game_players(chat_id),
            json.dumps(players, ensure_ascii=False),
        )
        from app.managers.joker_books import (
            seed_joker_books,
        )

        await seed_joker_books(
            chat_id,
            players,
            roles_map,
            self._keys,
        )
        role_vals = set(roles_map.values())
        if "role_dynamite" in role_vals:
            from random import SystemRandom

            pool = [int(u) for u in roles_map]
            SystemRandom().shuffle(pool)
            parts = pool[: min(4, len(pool))]
            await redis.hset(
                self._keys.game_flags(chat_id),
                mapping={
                    self._keys.field(
                        "bomber_parts"
                    ): json.dumps(parts),
                    self._keys.field(
                        "dinamit_finds"
                    ): "0",
                    self._keys.field(
                        "dinamit_in_game"
                    ): (
                        "1"
                        if "role_dynamite" in role_vals
                        else "0"
                    ),
                },
            )
        if "role_BlackKnight" in role_vals:
            await redis.hset(
                self._keys.game_flags(chat_id),
                self._keys.field("black_knight_hits"),
                "0",
            )
        await redis.hset(
            self._keys.game_flags(chat_id),
            self._keys.field("village_links_pending"),
            "1",
        )
        log_game_event(
            "roles_assigned",
            chat_id=chat_id,
            game_id=game_id,
        )
