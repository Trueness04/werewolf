import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useSession } from "../context/SessionContext";

type HeroRes = {
  hero?: { name: string; kind: string } | null;
  kinds?: { id: string; title_fa: string }[];
  price?: number;
  coins?: number;
};

export function HeroPage() {
  const { refresh } = useSession();
  const [data, setData] = useState<HeroRes | null>(null);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const d = await api<HeroRes>("/api/hero");
    setData(d);
    if (d.kinds?.[0] && !kind) setKind(d.kinds[0].id);
  }

  useEffect(() => {
    void load().catch((e) =>
      setErr(e instanceof Error ? e.message : "خطا"),
    );
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      await api("/api/hero", {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), kind }),
      });
      await refresh();
      await load();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "خطا");
    }
  }

  if (data?.hero) {
    return (
      <>
        <h1 className="page-title">هیرو شما</h1>
        <p>
          <strong>{data.hero.name}</strong>
        </p>
        <p className="meta">شخصیت: {data.hero.kind}</p>
      </>
    );
  }

  return (
    <>
      <h1 className="page-title">ساخت هیرو</h1>
      <p className="lede">
        قیمت: <strong>{data?.price ?? "—"}</strong> سکه · موجودی{" "}
        {data?.coins ?? "—"}
      </p>
      {err ? <p className="error">{err}</p> : null}
      <form onSubmit={onCreate}>
        <input
          className="field"
          placeholder="نام هیرو"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select
          className="field"
          style={{ marginTop: "0.55rem" }}
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          {(data?.kinds || []).map((k) => (
            <option key={k.id} value={k.id}>
              {k.title_fa}
            </option>
          ))}
        </select>
        <div className="row" style={{ marginTop: "0.55rem" }}>
          <button className="btn" type="submit">
            ساخت
          </button>
        </div>
      </form>
    </>
  );
}
