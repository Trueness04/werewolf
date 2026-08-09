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
            out.append("role_villager")
        return out[:need]

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
