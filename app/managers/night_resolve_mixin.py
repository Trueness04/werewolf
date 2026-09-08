"""Deaths + announcement mixin for NightResolver."""

from __future__ import annotations

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.database.models.player import PlayerRow
from app.database.session import session_scope


class NightResolveMixin:
    """Mixin: apply deaths + announce + to-day (uses
        self._bridge/_keys/_texts)."""

    async def _apply_deaths(
        self,
        ctx: dict,
    ) -> None:
        """Persist deaths and role conversions."""
        redis = await get_redis()
        chat_id = int(ctx["chat_id"])
        key = self._keys.game_hash(chat_id)
        game_id = int(
            await redis.hget(
                key,
                self._keys.field("game_id"),
            )
            or "0"
        )
        async with session_scope() as session:
            for prow in ctx["players"]:
                uid = int(prow["user_id"])
                stmt = (
                    select(PlayerRow)
                    .where(
                        PlayerRow.game_id == game_id,
                        PlayerRow.user_id == uid,
                    )
                )
                row = (
                    await session.execute(stmt)
                ).scalar_one_or_none()
                if row is None:
                    continue
                row.role = prow.get("role")
                row.team = prow.get("team")
                was_dead = not bool(
                    prow.get("alive", True)
                )
                dead = was_dead or uid in ctx["deaths"]
                row.alive = not dead
                row.state = (
                    "dead" if dead else "alive"
                )
                if dead and not was_dead:
                    if (
                        str(prow.get("role"))
                        == "role_Alpha"
                    ):
                        ctx.setdefault(
                            "flags_out",
                            {},
                        )["alpha_dead"] = "1"
                await redis.set(
                    self._keys.player_state(uid),
                    row.state,
                )
                await redis.set(
                    self._keys.player_role(uid),
                    str(prow.get("role") or ""),
                )
                if dead and not was_dead:
                    from app.managers.death_mute import (
                        maybe_mute_on_death,
                    )

                    await maybe_mute_on_death(
                        self._bridge,
                        chat_id,
                        uid,
                    )
                    from app.managers.role_links import (
                        process_death_links,
                    )

                    await process_death_links(
                        chat_id,
                        uid,
                        str(prow.get("role") or ""),
                        self._bridge,
                        self._texts,
                        self._keys,
                        lang=self._settings.default_lang,
                    )
        await redis.set(
            self._keys.game_roles(chat_id),
            json.dumps(ctx["roles"]),
        )

    async def _announce(
        self,
        chat_id: int,
        lang: str,
        ctx: dict,
    ) -> None:
        """Send night result messages to group."""
        from app.managers.night_announce import (
            announce_night_results,
        )

        await announce_night_results(
            chat_id,
            lang,
            ctx,
            bridge=self._bridge,
            texts=self._texts,
        )

    async def _to_day(
        self,
        chat_id: int,
        lang: str,
    ) -> None:
        """Enter day without bumping day_count."""
        _ = lang
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        from app.managers.day_manager import (
            DayManager,
        )

        await DayManager(
            self._bridge
        ).start_day(chat_id)
        await redis.hdel(
            flags,
            self._keys.field("no_night_kill"),
            self._keys.field("hunter_kill"),
            self._keys.field("send_wolf_cube_dead"),
            self._keys.field("royce_selectd2"),
            self._keys.field("check_night_done"),
        )
