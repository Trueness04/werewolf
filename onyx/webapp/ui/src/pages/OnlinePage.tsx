import { useEffect, useState } from "react";
import { api } from "../api/client";

type Online = {
  status: string;
  message_fa: string;
  queue_size?: number;
  min_players?: number;
  in_queue?: boolean;
};

export function OnlinePage() {
  const [data, setData] = useState<Online | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    setData(await api<Online>("/api/online"));
  }

  useEffect(() => {
    void load().catch((e) =>
      setErr(e instanceof Error ? e.message : "خطا"),
    );
  }, []);

  return (
    <>
      <h1 className="page-title">بازی آنلاین</h1>
      {err ? <p className="error">{err}</p> : null}
      {data ? (
        <>
          <p>
            <span className="badge">{data.status}</span>
          </p>
          <p>{data.message_fa}</p>
          <p className="meta">
            صف: {data.queue_size ?? 0} نفر · حداقل{" "}
            {data.min_players ?? 5}
          </p>
          <p className="meta">
            {data.in_queue ? "شما در صف هستید." : "در صف نیستید."}
          </p>
          <button
            type="button"
            className="btn"
            onClick={() =>
              void api("/api/online/queue", { method: "POST" }).then(
                () => load(),
              )
            }
          >
            {data.in_queue ? "خروج از صف" : "ورود به صف"}
          </button>
        </>
      ) : null}
    </>
  );
}
