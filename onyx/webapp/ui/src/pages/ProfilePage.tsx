import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Profile } from "../api/types";
import { useSession } from "../context/SessionContext";

export function ProfilePage({ self = false }: { self?: boolean }) {
  const { userId } = useParams();
  const { me, refresh } = useSession();
  const id = self ? me?.user_id : Number(userId);
  const [p, setP] = useState<Profile | null>(null);
  const [to, setTo] = useState("");
  const [amount, setAmount] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    void api<Profile>(`/api/profile/${id}`)
      .then(setP)
      .catch((e) => setErr(e instanceof Error ? e.message : "خطا"));
  }, [id]);

  if (!id) return <p className="meta">در حال بارگذاری هویت…</p>;
  if (!p) return err ? <p className="error">{err}</p> : <p>…</p>;

  const mine = me && Number(me.user_id) === Number(id);

  async function onTransfer(e: FormEvent) {
    e.preventDefault();
    try {
      await api("/api/wallet/transfer", {
        method: "POST",
        body: JSON.stringify({
          to_user_id: Number(to),
          amount: Number(amount),
        }),
      });
      await refresh();
      setMsg("انتقال انجام شد");
      setP(await api<Profile>(`/api/profile/${id}`));
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "خطا");
    }
  }

  return (
    <>
      <div className="profile-head">
        <div className="meta">@{p.username || "—"}</div>
        <h1>{p.name}</h1>
        <p className="lede" style={{ marginBottom: 0 }}>
          رنک {p.rank} · XP {p.xp} ·{" "}
          {p.coins.toLocaleString("fa-IR")} سکه
        </p>
        <p className="meta">
          بازی {p.games_played} · برد {p.wins}
        </p>
        <p>{p.bio || "بدون بیو"}</p>
        <div className="icons">
          {(p.icons || []).map((ic) => (
            <div
              className="icon-chip"
              key={`${ic.rank}-${ic.title_fa}`}
              title={ic.title_fa}
            >
              {ic.rank}
            </div>
          ))}
        </div>
        <div className="row" style={{ marginTop: "0.85rem" }}>
          {mine ? (
            <>
              <Link className="btn ghost" to="/hero">
                هیرو
              </Link>
              <Link className="btn ghost" to="/achievements">
                دستاورد
              </Link>
            </>
          ) : (
            <button
              type="button"
              className="btn"
              onClick={() =>
                void api(`/api/follow/${id}`, { method: "POST" }).then(
                  () => setMsg("دنبال شد"),
                )
              }
            >
              دنبال کردن
            </button>
          )}
        </div>
      </div>

      {err ? <p className="error">{err}</p> : null}
      {msg ? <p className="ok">{msg}</p> : null}

      {mine ? (
        <form onSubmit={onTransfer}>
          <p className="section-label">انتقال سکه</p>
          <div className="row">
            <input
              className="field"
              style={{ flex: 1 }}
              placeholder="user id مقصد"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
            <input
              className="field"
              style={{ width: "5.5rem" }}
              placeholder="مقدار"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <button className="btn" type="submit">
              انتقال
            </button>
          </div>
        </form>
      ) : null}
    </>
  );
}
