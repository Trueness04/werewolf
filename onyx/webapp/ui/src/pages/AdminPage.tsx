import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useSession } from "../context/SessionContext";

type Tab =
  | "overview"
  | "users"
  | "charges"
  | "ledger"
  | "reports"
  | "settings";

const tabs: [Tab, string][] = [
  ["overview", "نمای کلی"],
  ["users", "کاربر"],
  ["charges", "شارژ"],
  ["ledger", "لجر"],
  ["reports", "گزارش"],
  ["settings", "تنظیمات"],
];

export function AdminPage() {
  const { isSudo } = useSession();
  const [tab, setTab] = useState<Tab>("overview");

  if (!isSudo) return <p className="error">فقط سودو.</p>;

  return (
    <>
      <h1 className="page-title">مدیریت</h1>
      <p className="lede">پنل سودو اونیکس</p>
      <div className="admin-nav">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "active" : undefined}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "overview" ? <Overview /> : null}
      {tab === "users" ? <Users /> : null}
      {tab === "charges" ? <Charges /> : null}
      {tab === "ledger" ? <Ledger /> : null}
      {tab === "reports" ? <Reports /> : null}
      {tab === "settings" ? <Settings /> : null}
    </>
  );
}

function Overview() {
  const [d, setD] = useState<Record<string, number | boolean> | null>(
    null,
  );
  useEffect(() => {
    void api<Record<string, number | boolean>>(
      "/api/admin/overview",
    ).then(setD);
  }, []);
  if (!d) return <p>…</p>;
  const keys = [
    ["users", "کاربران"],
    ["coins_total", "سکه کل"],
    ["charges_pending", "شارژ pending"],
    ["reports_open", "گزارش باز"],
    ["charge_live", "درگاه زنده"],
  ] as const;
  return (
    <div className="stat-grid">
      {keys.map(([k, label]) => (
        <div className="stat" key={k}>
          <span className="meta">{label}</span>
          <b>
            {typeof d[k] === "boolean"
              ? d[k]
                ? "بله"
                : "خیر"
              : String(d[k] ?? "—")}
          </b>
        </div>
      ))}
    </div>
  );
}

function Users() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<
    { user_id: number; name: string; coins: number; rank: number }[]
  >([]);
  const [uid, setUid] = useState<number | null>(null);
  const [detail, setDetail] = useState<{
    user: { name: string; coins: number; xp: number; rank: number };
    shop_catalog: { id: string; title_fa: string }[];
  } | null>(null);
  const [delta, setDelta] = useState("");
  const [note, setNote] = useState("");
  const [itemId, setItemId] = useState("");

  async function search(e?: FormEvent) {
    e?.preventDefault();
    const d = await api<{ items: typeof items }>(
      `/api/admin/users?q=${encodeURIComponent(q)}`,
    );
    setItems(d.items || []);
  }

  async function openUser(id: number) {
    setUid(id);
    const d = await api<{
      user: { name: string; coins: number; xp: number; rank: number };
      shop_catalog: { id: string; title_fa: string }[];
    }>(`/api/admin/users/${id}`);
    setDetail(d);
    setItemId(d.shop_catalog?.[0]?.id || "");
  }

  return (
    <>
      <form className="row" onSubmit={search}>
        <input
          className="field"
          style={{ flex: 1 }}
          placeholder="آیدی / یوزرنیم / نام"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button className="btn" type="submit">
          جستجو
        </button>
      </form>
      {items.map((u) => (
        <div className="list-row" key={u.user_id}>
          <div>
            <strong>{u.name}</strong>
            <div className="meta">
              {u.user_id} · {u.coins} سکه · رنک {u.rank}
            </div>
          </div>
          <button
            type="button"
            className="btn ghost"
            onClick={() => void openUser(u.user_id)}
          >
            مدیریت
          </button>
        </div>
      ))}
      {detail && uid ? (
        <div style={{ marginTop: "1rem" }}>
          <h2 className="page-title" style={{ fontSize: "1.3rem" }}>
            {detail.user.name} #{uid}
          </h2>
          <p className="meta">
            {detail.user.coins} سکه · XP {detail.user.xp} · رنک{" "}
            {detail.user.rank}
          </p>
          <div className="row">
            <input
              className="field"
              style={{ width: "6rem" }}
              placeholder="+100"
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
            />
            <input
              className="field"
              style={{ flex: 1 }}
              placeholder="یادداشت"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <button
              type="button"
              className="btn"
              onClick={() =>
                void api(`/api/admin/users/${uid}/coins`, {
                  method: "POST",
                  body: JSON.stringify({
                    delta: Number(delta),
                    note,
                  }),
                }).then(() => openUser(uid))
              }
            >
              اعمال سکه
            </button>
          </div>
          <div className="row" style={{ marginTop: "0.55rem" }}>
            <select
              className="field"
              style={{ flex: 1 }}
              value={itemId}
              onChange={(e) => setItemId(e.target.value)}
            >
              {(detail.shop_catalog || []).map((i) => (
                <option key={i.id} value={i.id}>
                  {i.title_fa}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn"
              onClick={() =>
                void api(`/api/admin/users/${uid}/grant-item`, {
                  method: "POST",
                  body: JSON.stringify({ item_id: itemId, qty: 1 }),
                })
              }
            >
              اعطای آیتم
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}

function Charges() {
  const [items, setItems] = useState<
    { id: number; package_id: string; status: string; price_toman: number }[]
  >([]);
  useEffect(() => {
    void api<{ items: typeof items }>("/api/admin/charges").then((d) =>
      setItems(d.items || []),
    );
  }, []);
  return (
    <>
      {items.map((o) => (
        <div className="list-row" key={o.id}>
          <div>
            <strong>#{o.id}</strong>
            <div className="meta">
              {o.package_id} · {o.status} ·{" "}
              {o.price_toman.toLocaleString("fa-IR")}
            </div>
          </div>
          {o.status === "pending" ? (
            <button
              type="button"
              className="btn"
              onClick={() =>
                void api(`/api/admin/charges/${o.id}/fix`, {
                  method: "POST",
                  body: JSON.stringify({ action: "approve" }),
                }).then(() =>
                  api<{ items: typeof items }>(
                    "/api/admin/charges",
                  ).then((d) => setItems(d.items || [])),
                )
              }
            >
              تأیید
            </button>
          ) : null}
        </div>
      ))}
    </>
  );
}

function Ledger() {
  const [items, setItems] = useState<
    { id: number; delta: number; reason: string }[]
  >([]);
  useEffect(() => {
    void api<{ items: typeof items }>("/api/admin/ledger?limit=60").then(
      (d) => setItems(d.items || []),
    );
  }, []);
  return (
    <>
      {items.map((x) => (
        <div className="list-row" key={x.id}>
          <span>
            #{x.id} {x.delta > 0 ? "+" : ""}
            {x.delta} · {x.reason}
          </span>
          <button
            type="button"
            className="btn danger ghost"
            onClick={() =>
              void api(`/api/admin/ledger/${x.id}/reverse`, {
                method: "POST",
              })
            }
          >
            برگشت
          </button>
        </div>
      ))}
    </>
  );
}

function Reports() {
  const [items, setItems] = useState<
    { id: number; reason: string; status: string }[]
  >([]);
  useEffect(() => {
    void api<{ items: typeof items }>("/api/admin/reports").then((d) =>
      setItems(d.items || []),
    );
  }, []);
  return (
    <>
      {items.map((r) => (
        <div className="list-row" key={r.id}>
          <div>
            <strong>#{r.id}</strong>
            <div className="meta">
              {r.reason} · {r.status}
            </div>
          </div>
          <button
            type="button"
            className="btn ghost"
            onClick={() =>
              void api(`/api/admin/reports/${r.id}/resolve`, {
                method: "POST",
              }).then(() =>
                api<{ items: typeof items }>("/api/admin/reports").then(
                  (d) => setItems(d.items || []),
                ),
              )
            }
          >
            بستن
          </button>
        </div>
      ))}
    </>
  );
}

function Settings() {
  const [raw, setRaw] = useState("");
  useEffect(() => {
    void api<Record<string, unknown>>("/api/admin/settings").then((d) =>
      setRaw(JSON.stringify(d, null, 2)),
    );
  }, []);
  return (
    <>
      <textarea
        className="field"
        rows={12}
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
      />
      <div className="row" style={{ marginTop: "0.55rem" }}>
        <button
          type="button"
          className="btn"
          onClick={() =>
            void api("/api/admin/settings", {
              method: "POST",
              body: raw,
            })
          }
        >
          ذخیره
        </button>
      </div>
    </>
  );
}
