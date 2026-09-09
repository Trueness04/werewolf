"""Player assignment mixin for role distribution."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.database.models.player import PlayerRow
from app.database.session import session_scope
from app.managers.game_event import log_game_event


class RoleAssignMixin:
    """Mixin: write roles to DB + Redis (uses self._keys/_registry)."""

    async def _assign(
        self,
        chat_id: int,
        players: list,
        roles: list,
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
        roles_map = {}
        async with session_scope() as session:
            for player, role_id in zip(
                players, roles, strict=True
            ):
                uid = int(player["user_id"])
                info = self._registry.definition(
                    role_id
                )
                team = str(info["team"])
                stmt = (
                    select(PlayerRow)
                    .where(
                        PlayerRow.game_id
                        == game_id,
                        PlayerRow.user_id
                        == uid,
                    )
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
                        row.fullname
                        if row is not None
                        else uid
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
                    self._keys.player_last_role(
                        uid
                    ),
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

            pool = [
                int(u) for u in roles_map
            ]
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
                    ): "1"
                    if "role_dynamite"
                    in role_vals
                    else "0",
                },
            )
        if "role_BlackKnight" in role_vals:
            await redis.hset(
                self._keys.game_flags(chat_id),
                self._keys.field(
                    "black_knight_hits"
                ),
                "0",
            )
        await redis.hset(
            self._keys.game_flags(chat_id),
            self._keys.field(
                "village_links_pending"
            ),
            "1",
        )
        log_game_event(
            "roles_assigned",
            chat_id=chat_id,
            game_id=game_id,
        )
