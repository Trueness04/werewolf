import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { RankRow } from "../api/types";

type RanksRes = {
  governor?: RankRow | null;
  items: RankRow[];
};

export function RanksPage() {
  const [data, setData] = useState<RanksRes | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    void api<RanksRes>("/api/ranks")
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "خطا"));
  }, []);

  return (
    <>
      <h1 className="page-title">لیست رنک</h1>
      <p className="lede">خاندان سلطنتی اونیکس — نفر اول حکمران است</p>
      {err ? <p className="error">{err}</p> : null}
      {data?.governor ? (
        <div className="list-row">
          <div>
            <span className="badge">حکمران</span>
            <div>
              <strong>{data.governor.name}</strong>
            </div>
            <div className="meta">
              رنک {data.governor.rank} ·{" "}
              {data.governor.coins.toLocaleString("fa-IR")} سکه
            </div>
          </div>
        </div>
      ) : null}
      {(data?.items || []).map((u) => {
        const tag = u.governor
          ? "حکمران"
          : u.royal
            ? "خاندان سلطنتی"
            : "";
        return (
          <div className="list-row" key={`${u.place}-${u.name}`}>
            <div>
              <strong>
                #{u.place} {u.name}
              </strong>
              {tag ? (
                <>
                  {" "}
                  <span className="badge">{tag}</span>
                </>
              ) : null}
              <div className="meta">
                رنک {u.rank} · XP {u.xp}
              </div>
            </div>
            {u.user_id ? (
              <Link className="btn ghost" to={`/u/${u.user_id}`}>
                پروفایل
              </Link>
            ) : null}
          </div>
        );
      })}
    </>
  );
}
