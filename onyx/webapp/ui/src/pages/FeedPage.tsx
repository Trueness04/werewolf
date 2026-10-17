import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { FeedItem } from "../api/types";

export function FeedPage() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [body, setBody] = useState("");
  const [followingOnly, setFollowingOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const data = await api<{ items: FeedItem[] }>(
      `/api/feed?following_only=${followingOnly ? "true" : "false"}`,
    );
    setItems(data.items || []);
  }

  useEffect(() => {
    void load().catch((e) =>
      setErr(e instanceof Error ? e.message : "خطا"),
    );
  }, [followingOnly]);

  async function onPost(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    try {
      await api("/api/posts", {
        method: "POST",
        body: JSON.stringify({ body: body.trim() }),
      });
      setBody("");
      await load();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "خطا");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="page-title">فید</h1>
      <p className="lede">خانهٔ اونیکس — فعالیت‌ها و پست‌ها</p>

      <form className="compose" onSubmit={onPost}>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="چه خبر؟"
          maxLength={280}
        />
        <div className="row">
          <button className="btn" disabled={busy} type="submit">
            ارسال
          </button>
          <button
            type="button"
            className="btn ghost"
            onClick={() => setFollowingOnly((v) => !v)}
          >
            {followingOnly ? "فید سراسری" : "فقط دنبال‌شونده‌ها"}
          </button>
        </div>
      </form>

      {err ? <p className="error">{err}</p> : null}

      {items.map((item, i) =>
        item.kind === "user_post" ? (
          <article className="feed-item" key={item.id ?? i}>
            <div className="row">
              <strong>{item.user?.name || item.user?.user_id}</strong>
              <span className="meta">{item.created_at || ""}</span>
            </div>
            <p>{item.body}</p>
            <div className="row">
              <button
                type="button"
                className="btn link"
                onClick={() =>
                  void api(`/api/posts/${item.id}/like`, {
                    method: "POST",
                  })
                }
              >
                پسند
              </button>
              <button
                type="button"
                className="btn link"
                onClick={() =>
                  void api("/api/report", {
                    method: "POST",
                    body: JSON.stringify({
                      target_type: "post",
                      target_id: item.id,
                      reason: "user_report",
                    }),
                  })
                }
              >
                گزارش
              </button>
              {item.user?.user_id ? (
                <Link
                  className="btn link"
                  to={`/u/${item.user.user_id}`}
                >
                  پروفایل
                </Link>
              ) : null}
            </div>
          </article>
        ) : (
          <div className="feed-item" key={`${item.kind}-${i}`}>
            <span className="badge">{item.kind}</span>
            <span className="meta"> کاربر {item.user_id}</span>
          </div>
        ),
      )}
    </>
  );
}
