import { useEffect, useState } from "react";
import { api } from "../api/client";

type Ach = {
  title_fa: string;
  desc_fa?: string;
  unlocked?: boolean;
};

export function AchievementsPage() {
  const [items, setItems] = useState<Ach[]>([]);
  const [count, setCount] = useState(0);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    void api<{ items: Ach[]; unlocked_count?: number }>(
      "/api/achievements",
    )
      .then((d) => {
        setItems(d.items || []);
        setCount(d.unlocked_count || 0);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "خطا"));
  }, []);

  return (
    <>
      <h1 className="page-title">دستاوردها</h1>
      <p className="lede">{count} آنلاک‌شده</p>
      {err ? <p className="error">{err}</p> : null}
      {items.map((a) => (
        <div className="list-row" key={a.title_fa}>
          <div>
            <strong>{a.title_fa}</strong>
            <div className="meta">{a.desc_fa || ""}</div>
          </div>
          <span className="badge">{a.unlocked ? "باز" : "قفل"}</span>
        </div>
      ))}
    </>
  );
}
