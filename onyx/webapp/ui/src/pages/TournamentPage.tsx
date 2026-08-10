import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useSession } from "../context/SessionContext";

type Tour = {
  id: number;
  title: string;
  status: string;
  stake: number;
  members: number;
};

export function TournamentPage() {
  const { refresh } = useSession();
  const [items, setItems] = useState<Tour[]>([]);
  const [stakeDefault, setStakeDefault] = useState(10);
  const [title, setTitle] = useState("");
  const [stake, setStake] = useState("10");
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const d = await api<{
      items: Tour[];
      defaults?: { stake?: number };
    }>("/api/tournaments");
    setItems(d.items || []);
    const s = d.defaults?.stake ?? 10;
    setStakeDefault(s);
    setStake(String(s));
  }

  useEffect(() => {
    void load().catch((e) =>
      setErr(e instanceof Error ? e.message : "خطا"),
    );
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    const s = Number(stake);
    await api("/api/tournaments", {
      method: "POST",
      body: JSON.stringify({
        title: title.trim() || null,
        stake: Number.isFinite(s) ? s : stakeDefault,
      }),
    });
    await refresh();
    setTitle("");
    await load();
  }

  return (
    <>
      <h1 className="page-title">تورنمنت</h1>
      <p className="lede">ورود با استیک سکه (پیش‌فرض {stakeDefault})</p>
      {err ? <p className="error">{err}</p> : null}
      <form className="compose" onSubmit={onCreate}>
        <input
          className="field"
          placeholder="عنوان تورنمنت"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <input
          className="field"
          type="number"
          style={{ marginTop: "0.55rem" }}
          value={stake}
          onChange={(e) => setStake(e.target.value)}
        />
        <div className="row" style={{ marginTop: "0.55rem" }}>
          <button className="btn" type="submit">
            ایجاد
          </button>
        </div>
      </form>
      {items.map((t) => (
        <div className="list-row" key={t.id}>
          <div>
            <strong>{t.title}</strong>
            <div className="meta">
              {t.status} · stake {t.stake} · {t.members} نفر
            </div>
          </div>
          <button
            type="button"
            className="btn ghost"
            onClick={() =>
              void api(`/api/tournaments/${t.id}/join`, {
                method: "POST",
              })
                .then(() => refresh())
                .then(() => load())
            }
          >
            عضویت
          </button>
        </div>
      ))}
    </>
  );
}
