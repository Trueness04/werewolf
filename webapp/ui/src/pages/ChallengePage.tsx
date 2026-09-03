import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";

type Chal = { id: number; title: string; status: string; stake: number };

export function ChallengePage() {
  const [items, setItems] = useState<Chal[]>([]);
  const [title, setTitle] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const d = await api<{ items: Chal[] }>("/api/challenges");
    setItems(d.items || []);
  }

  useEffect(() => {
    void load().catch((e) =>
      setErr(e instanceof Error ? e.message : "خطا"),
    );
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await api("/api/challenges", {
      method: "POST",
      body: JSON.stringify({ title: title.trim(), stake: 0 }),
    });
    setTitle("");
    await load();
  }

  return (
    <>
      <h1 className="page-title">چالش</h1>
      <p className="lede">چالش فقط در وب‌اپ است</p>
      {err ? <p className="error">{err}</p> : null}
      <form className="compose" onSubmit={onCreate}>
        <input
          className="field"
          placeholder="عنوان چالش"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div className="row" style={{ marginTop: "0.55rem" }}>
          <button className="btn" type="submit">
            ایجاد
          </button>
        </div>
      </form>
      {items.map((c) => (
        <div className="list-row" key={c.id}>
          <div>
            <strong>{c.title}</strong>
            <div className="meta">
              {c.status} · stake {c.stake}
            </div>
          </div>
          <button
            type="button"
            className="btn ghost"
            onClick={() =>
              void api(`/api/challenges/${c.id}/join`, {
                method: "POST",
              })
            }
          >
            عضویت
          </button>
        </div>
      ))}
    </>
  );
}
