import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ChargeOrder, ChargePackage, ShopItem } from "../api/types";
import { useSession } from "../context/SessionContext";

type ShopRes = {
  items: ShopItem[];
  charge_enabled?: boolean;
  charge_live?: boolean;
  charge_packages?: ChargePackage[];
  currency_label?: string;
  sandbox_pay_allowed?: boolean;
};

export function ShopPage() {
  const { me, refresh } = useSession();
  const [shop, setShop] = useState<ShopRes | null>(null);
  const [orders, setOrders] = useState<ChargeOrder[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const s = await api<ShopRes>("/api/shop");
    setShop(s);
    try {
      const o = await api<{ items: ChargeOrder[] }>("/api/shop/charges");
      setOrders(o.items || []);
    } catch {
      setOrders([]);
    }
  }

  useEffect(() => {
    void load().catch((e) =>
      setErr(e instanceof Error ? e.message : "خطا"),
    );
  }, []);

  return (
    <>
      <h1 className="page-title">فروشگاه</h1>
      <p className="lede">
        موجودی:{" "}
        <strong>
          {(me?.coins ?? 0).toLocaleString("fa-IR")} سکه
        </strong>
      </p>
      {err ? <p className="error">{err}</p> : null}
      {msg ? <p className="ok">{msg}</p> : null}

      {shop?.charge_enabled && (shop.charge_packages || []).length ? (
        <>
          <p className="section-label">شارژ سکه</p>
          <p className="meta">
            {shop.charge_live
              ? "پرداخت از درگاه بانک"
              : "بسته‌ها ثبت می‌شوند؛ درگاه هنوز زنده نیست"}
            {" · "}
            مبالغ به {shop.currency_label || "تومان"}
          </p>
          {(shop.charge_packages || []).map((pk) => (
            <div className="list-row" key={pk.id}>
              <div>
                <strong>{pk.title_fa}</strong>
                <div className="meta">
                  {Number(pk.price_toman).toLocaleString("fa-IR")} تومان
                </div>
              </div>
              <button
                type="button"
                className="btn"
                onClick={() =>
                  void api<{ order?: { id: number } }>(
                    `/api/shop/charge/${pk.id}`,
                    { method: "POST" },
                  )
                    .then((res) => {
                      setMsg(`سفارش #${res.order?.id} ثبت شد`);
                      return load();
                    })
                    .catch((e) =>
                      setErr(e instanceof Error ? e.message : "خطا"),
                    )
                }
              >
                {shop.charge_live ? "پرداخت" : "ثبت سفارش"}
              </button>
            </div>
          ))}
          {orders
            .filter((o) => o.status === "pending")
            .map((o) => (
              <div className="list-row" key={o.id}>
                <div>
                  <strong>#{o.id}</strong>
                  <div className="meta">
                    {o.package_id} ·{" "}
                    {Number(o.price_toman).toLocaleString("fa-IR")} تومان
                  </div>
                </div>
                {shop.sandbox_pay_allowed ? (
                  <button
                    type="button"
                    className="btn ghost"
                    onClick={() =>
                      void api(
                        `/api/shop/charge/${o.id}/sandbox-pay`,
                        { method: "POST" },
                      )
                        .then(() => refresh())
                        .then(() => load())
                        .then(() => setMsg("پرداخت آزمایشی انجام شد"))
                    }
                  >
                    پرداخت آزمایشی
                  </button>
                ) : (
                  <span className="badge">pending</span>
                )}
              </div>
            ))}
        </>
      ) : null}

      <p className="section-label">خرید با سکه</p>
      {(shop?.items || []).map((it) => (
        <div className="list-row" key={it.id}>
          <div>
            <strong>{it.title_fa}</strong>
            <div className="meta">
              {it.price} سکه · {it.kind}
            </div>
          </div>
          <button
            type="button"
            className="btn"
            onClick={() =>
              void api(`/api/shop/buy/${it.id}`, { method: "POST" })
                .then(() => refresh())
                .then(() => load())
                .then(() => setMsg("خرید انجام شد"))
                .catch((e) =>
                  setErr(e instanceof Error ? e.message : "خطا"),
                )
            }
          >
            خرید
          </button>
        </div>
      ))}
    </>
  );
}
