const tg = window.Telegram?.WebApp;

export function bootTelegram(): void {
  if (!tg) return;
  tg.ready();
  tg.expand();
}

function authHeaders(): HeadersInit {
  const h: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const init = tg?.initData || "";
  if (init) h["X-Telegram-Init-Data"] = init;
  return h;
}

export async function api<T>(
  path: string,
  opts: RequestInit = {},
): Promise<T> {
  const res = await fetch(path, {
    ...opts,
    headers: { ...authHeaders(), ...(opts.headers || {}) },
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json() as Promise<T>;
}
