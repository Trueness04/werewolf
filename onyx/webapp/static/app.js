/* Onyx WebApp client — Telegram Mini App */
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  view: "feed",
  me: null,
  followingOnly: false,
  isSudo: false,
  adminTab: "overview",
  adminUser: null,
};

function authHeaders() {
  const h = { "Content-Type": "application/json" };
  const init = tg?.initData || "";
  if (init) h["X-Telegram-Init-Data"] = init;
  return h;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { ...authHeaders(), ...(opts.headers || {}) },
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || res.statusText);
  }
  return res.json();
}

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstChild;
}

async function loadMe() {
  state.me = await api("/api/me");
  try {
    const adm = await api("/api/admin/me");
    state.isSudo = !!adm.is_sudo;
  } catch {
    state.isSudo = false;
  }
  const tab = document.getElementById("adminTab");
  if (tab) tab.hidden = !state.isSudo;
}

function renderTabs() {
  document.querySelectorAll(".tabs button").forEach((b) => {
    b.classList.toggle("active", b.dataset.view === state.view);
  });
}

async function showFeed() {
  const data = await api(
    `/api/feed?following_only=${state.followingOnly ? "true" : "false"}`
  );
  const root = document.getElementById("app");
  root.innerHTML = "";
  root.appendChild(
    el(`<div class="compose">
      <textarea id="postBody" rows="3" placeholder="چه خبر؟"></textarea>
      <div class="row" style="margin-top:.5rem">
        <button class="btn" id="postBtn">ارسال</button>
        <button class="btn ghost" id="toggleFollow">
          ${state.followingOnly ? "فید سراسری" : "فقط دنبال‌شونده‌ها"}
        </button>
      </div>
    </div>`)
  );
  document.getElementById("postBtn").onclick = async () => {
    const body = document.getElementById("postBody").value.trim();
    if (!body) return;
    await api("/api/posts", {
      method: "POST",
      body: JSON.stringify({ body }),
    });
    showFeed();
  };
  document.getElementById("toggleFollow").onclick = () => {
    state.followingOnly = !state.followingOnly;
    showFeed();
  };
  for (const item of data.items || []) {
    if (item.kind === "user_post") {
      const name = item.user?.fullname || item.user?.user_id;
      const node = el(`<article class="item">
        <div class="row">
          <strong>${esc(name)}</strong>
          <span class="meta">${esc(item.created_at || "")}</span>
        </div>
        <p>${esc(item.body)}</p>
        <div class="row">
          <button class="btn ghost like" data-id="${item.id}">پسند</button>
          <button class="btn ghost report" data-id="${item.id}">گزارش</button>
          <button class="btn ghost go-profile" data-uid="${item.user?.user_id}">پروفایل</button>
        </div>
      </article>`);
      root.appendChild(node);
    } else {
      root.appendChild(
        el(`<div class="item muted">
          <span class="badge">${esc(item.kind)}</span>
          کاربر ${esc(String(item.user_id))}
        </div>`)
      );
    }
  }
  root.querySelectorAll(".like").forEach((b) => {
    b.onclick = () =>
      api(`/api/posts/${b.dataset.id}/like`, { method: "POST" });
  });
  root.querySelectorAll(".report").forEach((b) => {
    b.onclick = () =>
      api("/api/report", {
        method: "POST",
        body: JSON.stringify({
          target_type: "post",
          target_id: Number(b.dataset.id),
          reason: "user_report",
        }),
      });
  });
  root.querySelectorAll(".go-profile").forEach((b) => {
    b.onclick = () => showProfile(Number(b.dataset.uid));
  });
}

async function showRanks() {
  const data = await api("/api/ranks");
  const root = document.getElementById("app");
  root.innerHTML = "";
  root.appendChild(el("<h2>لیست رنک — خاندان سلطنتی اونیکس</h2>"));
  if (data.governor) {
    root.appendChild(
      el(`<div class="panel">
        <span class="badge">حکمران</span>
        <strong> ${esc(data.governor.fullname)}</strong>
        <div class="muted">رنک ${data.governor.rank} · ${data.governor.coins} سکه</div>
      </div>`)
    );
  }
  for (const u of data.items || []) {
    const tag = u.governor
      ? "حکمران"
      : u.royal
        ? "خاندان سلطنتی"
        : "";
    root.appendChild(
      el(`<div class="item row">
        <strong>#${u.place}</strong>
        <span>${esc(u.fullname)}</span>
        ${tag ? `<span class="badge">${tag}</span>` : ""}
        <span class="muted">رنک ${u.rank} · XP ${u.xp}</span>
      </div>`)
    );
  }
}

async function showShop() {
  const data = await api("/api/shop");
  let orders = { items: [] };
  try {
    orders = await api("/api/shop/charges");
  } catch {
    /* unauth / empty */
  }
  const root = document.getElementById("app");
  root.innerHTML = "";
  root.appendChild(
    el(`<div class="panel">
      <h2>فروشگاه</h2>
      <p>موجودی شما: <strong>${state.me?.coins ?? "—"}</strong> سکه</p>
    </div>`)
  );
  if (data.charge_enabled && (data.charge_packages || []).length) {
    const label = data.currency_label || "تومان";
    root.appendChild(
      el(`<div class="panel">
        <h3>شارژ سکه</h3>
        <p class="muted">${
          data.charge_live
            ? "پرداخت از درگاه بانک (تا اتصال کلید واقعی، سفارش pending می‌ماند)."
            : "بسته‌ها ثبت می‌شوند؛ درگاه هنوز زنده نیست — سفارش در انتظار بررسی."
        }</p>
        <p class="muted">مبالغ به ${esc(label)} نمایش داده می‌شوند.</p>
      </div>`)
    );
    for (const pk of data.charge_packages) {
      const btnLabel = data.charge_live
        ? "پرداخت"
        : "ثبت سفارش (در انتظار درگاه)";
      const node = el(`<div class="item row">
        <div>
          <strong>${esc(pk.title_fa)}</strong>
          <div class="muted">${Number(pk.price_toman).toLocaleString("fa-IR")} تومان</div>
        </div>
        <button class="btn charge" data-id="${esc(pk.id)}">${btnLabel}</button>
      </div>`);
      root.appendChild(node);
    }
    const pending = (orders.items || []).filter(
      (o) => o.status === "pending"
    );
    if (pending.length) {
      root.appendChild(
        el(`<div class="panel"><h3>سفارش‌های در انتظار</h3></div>`)
      );
      for (const o of pending) {
        const canSandbox = data.sandbox_pay_allowed;
        const row = el(`<div class="item row">
          <div>
            <strong>#${o.id}</strong> · ${esc(o.package_id)}
            <div class="muted">${Number(o.price_toman).toLocaleString("fa-IR")} تومان · ${o.coins} سکه · ${esc(o.note || o.status)}</div>
          </div>
          ${
            canSandbox
              ? `<button class="btn ghost sandbox" data-id="${o.id}">پرداخت آزمایشی</button>`
              : `<span class="badge">pending</span>`
          }
        </div>`);
        root.appendChild(row);
      }
    }
  }
  root.appendChild(el(`<div class="panel"><h3>خرید با سکه</h3></div>`));
  for (const it of data.items || []) {
    const node = el(`<div class="item row">
      <div>
        <strong>${esc(it.title_fa)}</strong>
        <div class="muted">${it.price} سکه · ${esc(it.kind)}</div>
      </div>
      <button class="btn buy" data-id="${esc(it.id)}">خرید</button>
    </div>`);
    root.appendChild(node);
  }
  root.querySelectorAll(".buy").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/shop/buy/${b.dataset.id}`, { method: "POST" });
      await loadMe();
      showShop();
    };
  });
  root.querySelectorAll(".charge").forEach((b) => {
    b.onclick = async () => {
      const res = await api(`/api/shop/charge/${b.dataset.id}`, {
        method: "POST",
      });
      flash(
        res.charge_live
          ? `سفارش #${res.order?.id} ثبت شد — در انتظار درگاه`
          : `سفارش #${res.order?.id} ثبت شد (در انتظار درگاه)`
      );
      showShop();
    };
  });
  root.querySelectorAll(".sandbox").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/shop/charge/${b.dataset.id}/sandbox-pay`, {
        method: "POST",
      });
      await loadMe();
      flash("پرداخت آزمایشی انجام شد");
      showShop();
    };
  });
}

async function showChallenge() {
  const data = await api("/api/challenges");
  const root = document.getElementById("app");
  root.innerHTML = "";
  root.appendChild(
    el(`<div class="compose">
      <h2>چالش (فقط وب)</h2>
      <input id="chalTitle" placeholder="عنوان چالش" />
      <div class="row" style="margin-top:.5rem">
        <button class="btn" id="chalCreate">ایجاد</button>
      </div>
    </div>`)
  );
  document.getElementById("chalCreate").onclick = async () => {
    const title = document.getElementById("chalTitle").value.trim();
    if (!title) return;
    await api("/api/challenges", {
      method: "POST",
      body: JSON.stringify({ title, stake: 0 }),
    });
    showChallenge();
  };
  for (const c of data.items || []) {
    const node = el(`<div class="item row">
      <div>
        <strong>${esc(c.title)}</strong>
        <div class="muted">${esc(c.status)} · stake ${c.stake}</div>
      </div>
      <button class="btn ghost join" data-id="${c.id}">عضویت</button>
    </div>`);
    root.appendChild(node);
  }
  root.querySelectorAll(".join").forEach((b) => {
    b.onclick = () =>
      api(`/api/challenges/${b.dataset.id}/join`, { method: "POST" });
  });
}

async function showHero() {
  const data = await api("/api/hero");
  const root = document.getElementById("app");
  root.innerHTML = "";
  if (data.hero) {
    root.appendChild(
      el(`<div class="panel">
        <h2>هیرو شما</h2>
        <p><strong>${esc(data.hero.name)}</strong></p>
        <p class="muted">شخصیت: ${esc(data.hero.kind)}</p>
      </div>`)
    );
    return;
  }
  const opts = (data.kinds || [])
    .map(
      (k) =>
        `<option value="${esc(k.id)}">${esc(k.title_fa)}</option>`
    )
    .join("");
  root.appendChild(
    el(`<div class="compose">
      <h2>ساخت هیرو</h2>
      <p class="muted">قیمت: <strong>${data.price}</strong> سکه · موجودی ${data.coins}</p>
      <input id="heroName" placeholder="نام هیرو" />
      <select id="heroKind" style="margin-top:.5rem;width:100%">${opts}</select>
      <div class="row" style="margin-top:.5rem">
        <button class="btn" id="heroCreate">ساخت</button>
      </div>
    </div>`)
  );
  document.getElementById("heroCreate").onclick = async () => {
    const name = document.getElementById("heroName").value.trim();
    const kind = document.getElementById("heroKind").value;
    if (!name) return;
    await api("/api/hero", {
      method: "POST",
      body: JSON.stringify({ name, kind }),
    });
    await loadMe();
    flash("هیرو ساخته شد");
    showHero();
  };
}

async function showAchievements() {
  const data = await api("/api/achievements");
  const root = document.getElementById("app");
  root.innerHTML = "";
  root.appendChild(
    el(`<div class="panel">
      <h2>دستاوردها</h2>
      <p class="muted">${data.unlocked_count || 0} آنلاک‌شده</p>
    </div>`)
  );
  for (const a of data.items || []) {
    root.appendChild(
      el(`<div class="item row">
        <div>
          <strong>${esc(a.title_fa)}</strong>
          <div class="muted">${esc(a.desc_fa || "")}</div>
        </div>
        <span class="badge">${a.unlocked ? "باز" : "قفل"}</span>
      </div>`)
    );
  }
}

async function showTournament() {
  const data = await api("/api/tournaments");
  const root = document.getElementById("app");
  root.innerHTML = "";
  const stake = data.defaults?.stake ?? 10;
  root.appendChild(
    el(`<div class="compose">
      <h2>تورنمنت</h2>
      <p class="muted">ورود با استیک سکه (پیش‌فرض ${stake})</p>
      <input id="tourTitle" placeholder="عنوان تورنمنت" />
      <input id="tourStake" type="number" value="${stake}" style="margin-top:.5rem;width:100%" />
      <div class="row" style="margin-top:.5rem">
        <button class="btn" id="tourCreate">ایجاد</button>
      </div>
    </div>`)
  );
  document.getElementById("tourCreate").onclick = async () => {
    const title = document.getElementById("tourTitle").value.trim();
    const s = Number(document.getElementById("tourStake").value);
    await api("/api/tournaments", {
      method: "POST",
      body: JSON.stringify({
        title: title || null,
        stake: Number.isFinite(s) ? s : stake,
      }),
    });
    await loadMe();
    showTournament();
  };
  for (const t of data.items || []) {
    const node = el(`<div class="item row">
      <div>
        <strong>${esc(t.title)}</strong>
        <div class="muted">${esc(t.status)} · stake ${t.stake} سکه · ${t.members} نفر</div>
      </div>
      <button class="btn ghost tjoin" data-id="${t.id}">عضویت</button>
    </div>`);
    root.appendChild(node);
  }
  root.querySelectorAll(".tjoin").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/tournaments/${b.dataset.id}/join`, {
        method: "POST",
      });
      await loadMe();
      flash("عضو شدید");
      showTournament();
    };
  });
}

async function showOnline() {
  const data = await api("/api/online");
  const root = document.getElementById("app");
  root.innerHTML = "";
  root.appendChild(
    el(`<div class="panel">
      <h2>بازی آنلاین</h2>
      <p><span class="badge">${esc(data.status)}</span></p>
      <p>${esc(data.message_fa)}</p>
      <p class="muted">صف: ${data.queue_size ?? 0} نفر · حداقل ${data.min_players ?? 5}</p>
      <p class="muted">${data.in_queue ? "شما در صف هستید." : "در صف نیستید."}</p>
      <button class="btn" id="qBtn">${data.in_queue ? "خروج از صف" : "ورود به صف"}</button>
    </div>`)
  );
  document.getElementById("qBtn").onclick = async () => {
    await api("/api/online/queue", { method: "POST" });
    showOnline();
  };
}

async function showProfile(uid) {
  const id = uid || state.me?.user_id;
  if (!id) return;
  const p = await api(`/api/profile/${id}`);
  const root = document.getElementById("app");
  root.innerHTML = "";
  const mine = state.me && Number(state.me.user_id) === Number(id);
  root.appendChild(
    el(`<div class="panel">
      <h2>${esc(p.fullname)}</h2>
      <div class="muted">@${esc(p.username || "—")}</div>
      <p>رنک ${p.rank} · XP ${p.xp} · ${p.coins} سکه</p>
      <p class="muted">بازی ${p.games_played} · برد ${p.wins}</p>
      <p>${esc(p.bio || "بدون بیو")}</p>
      <div class="icons" id="icons"></div>
      <div class="row" style="margin-top:.6rem">
        ${
          mine
            ? `<button class="btn ghost" id="goHero">هیرو</button>
               <button class="btn ghost" id="goAch">دستاورد</button>
               <button class="btn ghost" id="goTour">تورنمنت</button>`
            : ""
        }
        ${
          mine
            ? ""
            : `<button class="btn" id="followBtn">دنبال کردن</button>`
        }
        ${
          mine
            ? `<input id="xferTo" placeholder="user id مقصد" style="flex:1" />
               <input id="xferAmt" placeholder="مقدار" style="width:5rem" />
               <button class="btn" id="xferBtn">انتقال سکه</button>`
            : ""
        }
      </div>
    </div>`)
  );
  const icons = document.getElementById("icons");
  for (const ic of p.icons || []) {
    icons.appendChild(
      el(`<div class="icon-chip" title="${esc(ic.title_fa)}">${ic.rank}</div>`)
    );
  }
  const fb = document.getElementById("followBtn");
  if (fb) {
    fb.onclick = () =>
      api(`/api/follow/${id}`, { method: "POST" });
  }
  const gh = document.getElementById("goHero");
  if (gh) gh.onclick = () => {
    state.view = "hero";
    route();
  };
  const ga = document.getElementById("goAch");
  if (ga) ga.onclick = () => {
    state.view = "achievements";
    route();
  };
  const gt = document.getElementById("goTour");
  if (gt) gt.onclick = () => {
    state.view = "tournament";
    route();
  };
  const xb = document.getElementById("xferBtn");
  if (xb) {
    xb.onclick = async () => {
      const to = Number(document.getElementById("xferTo").value);
      const amount = Number(document.getElementById("xferAmt").value);
      await api("/api/wallet/transfer", {
        method: "POST",
        body: JSON.stringify({ to_user_id: to, amount }),
      });
      await loadMe();
      showProfile(id);
    };
  }
}

function esc(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function flash(msg) {
  const n = el(`<p class="ok-flash">${esc(msg)}</p>`);
  document.getElementById("app")?.prepend(n);
  setTimeout(() => n.remove(), 2500);
}

async function showAdmin() {
  if (!state.isSudo) {
    document.getElementById("app").innerHTML =
      `<p class="error">فقط سودو.</p>`;
    return;
  }
  const root = document.getElementById("app");
  root.innerHTML = "";
  const nav = el(`<div class="admin-nav" id="adminNav"></div>`);
  const tabs = [
    ["overview", "نمای کلی"],
    ["users", "کاربر / جادو"],
    ["charges", "شارژ"],
    ["ledger", "لجر"],
    ["sponsors", "اسپانسر"],
    ["groups", "قفل گروه"],
    ["reports", "گزارش"],
    ["bans", "بن"],
    ["challenges", "چالش"],
    ["settings", "تنظیمات"],
  ];
  for (const [id, label] of tabs) {
    const b = el(
      `<button data-tab="${id}" class="${
        state.adminTab === id ? "active" : ""
      }">${label}</button>`
    );
    b.onclick = () => {
      state.adminTab = id;
      showAdmin();
    };
    nav.appendChild(b);
  }
  root.appendChild(nav);
  const body = el(`<div id="adminBody"></div>`);
  root.appendChild(body);
  const map = {
    overview: adminOverview,
    users: adminUsers,
    charges: adminCharges,
    ledger: adminLedger,
    sponsors: adminSponsors,
    groups: adminGroups,
    reports: adminReports,
    bans: adminBans,
    challenges: adminChallenges,
    settings: adminSettings,
  };
  await (map[state.adminTab] || adminOverview)(body);
}

async function adminOverview(root) {
  const d = await api("/api/admin/overview");
  root.appendChild(
    el(`<div class="panel">
      <h2>پنل سودو</h2>
      <p class="muted">تا وقتی درگاه زنده نیست، اعطای دستی سکه/جادو از همین‌جاست. بعد از charge_live همه‌چیز خودکار می‌شود؛ سودو فقط تراکنش خراب را تعمیر می‌کند.</p>
      <div class="stat-grid" style="margin-top:.75rem">
        <div class="stat"><span class="muted">کاربران</span><b>${d.users}</b></div>
        <div class="stat"><span class="muted">سکه کل</span><b>${d.coins_total}</b></div>
        <div class="stat"><span class="muted">شارژ pending</span><b>${d.charges_pending}</b></div>
        <div class="stat"><span class="muted">شارژ failed</span><b>${d.charges_failed}</b></div>
        <div class="stat"><span class="muted">گزارش باز</span><b>${d.reports_open}</b></div>
        <div class="stat"><span class="muted">اسپانسر فعال</span><b>${d.sponsors_active}</b></div>
        <div class="stat"><span class="muted">گروه قفل‌اسپانسر</span><b>${d.groups_sponsor_locked}</b></div>
        <div class="stat"><span class="muted">درگاه زنده</span><b>${d.charge_live ? "بله" : "خیر"}</b></div>
      </div>
    </div>`)
  );
}

async function adminUsers(root) {
  root.appendChild(
    el(`<div class="panel">
      <h2>جستجوی کاربر</h2>
      <div class="row">
        <input id="uq" class="sm" placeholder="آیدی / یوزرنیم / نام" />
        <button class="btn" id="uSearch">جستجو</button>
      </div>
      <div id="uList"></div>
    </div>`)
  );
  const detail = el(`<div id="uDetail"></div>`);
  root.appendChild(detail);
  const run = async () => {
    const q = document.getElementById("uq").value.trim();
    const data = await api(`/api/admin/users?q=${encodeURIComponent(q)}`);
    const box = document.getElementById("uList");
    box.innerHTML = "";
    for (const u of data.items || []) {
      const row = el(`<div class="item row compact">
        <div>
          <strong>${esc(u.fullname)}</strong>
          <div class="muted">${u.user_id} · ${u.coins} سکه · رنک ${u.rank}</div>
        </div>
        <button class="btn ghost pick" data-id="${u.user_id}">مدیریت</button>
      </div>`);
      box.appendChild(row);
    }
    box.querySelectorAll(".pick").forEach((b) => {
      b.onclick = () => loadAdminUser(Number(b.dataset.id));
    });
  };
  document.getElementById("uSearch").onclick = run;
  if (state.adminUser) await loadAdminUser(state.adminUser);
  else await run();
}

async function loadAdminUser(uid) {
  state.adminUser = uid;
  const d = await api(`/api/admin/users/${uid}`);
  const root = document.getElementById("uDetail");
  if (!root) return;
  const inv = (d.inventory || [])
    .map((i) => `${esc(i.item_id)}×${i.qty}`)
    .join(" · ") || "خالی";
  const items = (d.shop_catalog || [])
    .map(
      (i) =>
        `<option value="${esc(i.id)}">${esc(i.title_fa)} (${esc(i.id)})</option>`
    )
    .join("");
  root.innerHTML = "";
  root.appendChild(
    el(`<div class="panel">
      <h2>${esc(d.user.fullname)} <span class="muted">#${uid}</span></h2>
      <p>${d.user.coins} سکه · XP ${d.user.xp} · رنک ${d.user.rank}</p>
      <p class="muted">موجودی آیتم: ${inv}</p>
      <h3>اعطای سکه (بدون درگاه)</h3>
      <div class="row">
        <input id="coinDelta" class="sm" placeholder="+100 یا -50" />
        <input id="coinNote" class="sm" placeholder="یادداشت" />
        <button class="btn" id="coinBtn">اعمال</button>
      </div>
      <h3 style="margin-top:1rem">اعطای جادو / آیتم شاپ</h3>
      <div class="row">
        <select id="grantItem">${items}</select>
        <input id="grantQty" class="sm" value="1" style="width:4rem" />
        <button class="btn" id="grantBtn">انتقال به کاربر</button>
      </div>
      <h3 style="margin-top:1rem">لجر اخیر</h3>
      <div id="uLed"></div>
    </div>`)
  );
  const led = document.getElementById("uLed");
  for (const x of d.ledger || []) {
    led.appendChild(
      el(`<div class="item row compact">
        <span>#${x.id} ${x.delta > 0 ? "+" : ""}${x.delta} · ${esc(x.reason)}</span>
        <button class="btn danger ghost rev" data-id="${x.id}">برگشت</button>
      </div>`)
    );
  }
  document.getElementById("coinBtn").onclick = async () => {
    const delta = Number(document.getElementById("coinDelta").value);
    const note = document.getElementById("coinNote").value;
    await api(`/api/admin/users/${uid}/coins`, {
      method: "POST",
      body: JSON.stringify({ delta, note }),
    });
    flash("سکه اعمال شد");
    loadAdminUser(uid);
  };
  document.getElementById("grantBtn").onclick = async () => {
    const item_id = document.getElementById("grantItem").value;
    const qty = Number(document.getElementById("grantQty").value) || 1;
    await api(`/api/admin/users/${uid}/grant-item`, {
      method: "POST",
      body: JSON.stringify({ item_id, qty, note: "sudo grant" }),
    });
    flash("آیتم منتقل شد");
    loadAdminUser(uid);
  };
  led.querySelectorAll(".rev").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/admin/ledger/${b.dataset.id}/reverse`, {
        method: "POST",
        body: JSON.stringify({ note: "sudo reverse" }),
      });
      flash("تراکنش برگشت خورد");
      loadAdminUser(uid);
    };
  });
}

async function adminCharges(root) {
  const data = await api("/api/admin/charges");
  root.appendChild(
    el(`<div class="panel">
      <h2>شارژ ریالی</h2>
      <p class="muted">درگاه زنده: <strong>${data.charge_live ? "بله" : "خیر"}</strong> — تا زنده نشود، اعطای دستی زیر.</p>
      <h3>اعطای دستی بسته سکه</h3>
      <div class="row">
        <input id="mcUid" class="sm" placeholder="user id" />
        <input id="mcCoins" class="sm" placeholder="سکه" />
        <input id="mcPrice" class="sm" placeholder="تومان" />
        <input id="mcNote" class="sm" placeholder="یادداشت" />
        <button class="btn" id="mcBtn">ثبت manual</button>
      </div>
    </div>`)
  );
  document.getElementById("mcBtn").onclick = async () => {
    await api("/api/admin/charges/manual", {
      method: "POST",
      body: JSON.stringify({
        user_id: Number(document.getElementById("mcUid").value),
        coins: Number(document.getElementById("mcCoins").value),
        price_toman: Number(document.getElementById("mcPrice").value) || 0,
        note: document.getElementById("mcNote").value || "sudo",
      }),
    });
    flash("شارژ دستی ثبت شد");
    showAdmin();
  };
  for (const c of data.items || []) {
    const node = el(`<div class="item row">
      <div>
        <strong>#${c.id}</strong> user ${c.user_id}
        <div class="muted">${c.coins} سکه · ${Number(c.price_toman).toLocaleString("fa-IR")} تومان · ${esc(c.status)}</div>
        <div class="muted">${esc(c.note || "")}</div>
      </div>
      <div class="row">
        <button class="btn fix" data-id="${c.id}" data-st="paid">paid</button>
        <button class="btn ghost fix" data-id="${c.id}" data-st="failed">failed</button>
        <button class="btn danger ghost fix" data-id="${c.id}" data-st="reversed">reverse</button>
      </div>
    </div>`);
    root.appendChild(node);
  }
  root.querySelectorAll(".fix").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/admin/charges/${b.dataset.id}/fix`, {
        method: "POST",
        body: JSON.stringify({
          status: b.dataset.st,
          note: "sudo panel",
        }),
      });
      flash("سفارش به‌روز شد");
      showAdmin();
    };
  });
}

async function adminLedger(root) {
  const data = await api("/api/admin/ledger?limit=60");
  root.appendChild(el(`<div class="panel"><h2>لجر سراسری</h2></div>`));
  for (const x of data.items || []) {
    root.appendChild(
      el(`<div class="item row">
        <span>#${x.id} u${x.user_id} ${x.delta > 0 ? "+" : ""}${x.delta} · ${esc(x.reason)}</span>
        <button class="btn danger ghost rev" data-id="${x.id}">برگشت</button>
      </div>`)
    );
  }
  root.querySelectorAll(".rev").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/admin/ledger/${b.dataset.id}/reverse`, {
        method: "POST",
        body: JSON.stringify({ note: "sudo" }),
      });
      flash("برگشت خورد");
      showAdmin();
    };
  });
}

async function adminSponsors(root) {
  const data = await api("/api/admin/sponsors");
  root.appendChild(
    el(`<div class="panel">
      <h2>اسپانسرها</h2>
      <div class="row">
        <input id="spUid" class="sm" placeholder="user id" />
        <input id="spTitle" class="sm" placeholder="عنوان" value="اسپانسر" />
        <input id="spAmt" class="sm" placeholder="تومان" />
        <button class="btn" id="spBtn">افزودن/به‌روز</button>
      </div>
    </div>`)
  );
  document.getElementById("spBtn").onclick = async () => {
    await api("/api/admin/sponsors", {
      method: "POST",
      body: JSON.stringify({
        user_id: Number(document.getElementById("spUid").value),
        title: document.getElementById("spTitle").value || "اسپانسر",
        amount_toman: Number(document.getElementById("spAmt").value) || 0,
        active: true,
      }),
    });
    flash("اسپانسر ذخیره شد");
    showAdmin();
  };
  for (const s of data.items || []) {
    root.appendChild(
      el(`<div class="item row">
        <div>
          <strong>${esc(s.title)}</strong> · user ${s.user_id}
          <div class="muted">${Number(s.amount_toman).toLocaleString("fa-IR")} تومان · ${s.active ? "فعال" : "خاموش"}</div>
        </div>
        <button class="btn ghost tog" data-id="${s.user_id}" data-on="${s.active ? "0" : "1"}">${s.active ? "خاموش" : "فعال"}</button>
      </div>`)
    );
  }
  root.querySelectorAll(".tog").forEach((b) => {
    b.onclick = async () => {
      await api("/api/admin/sponsors", {
        method: "POST",
        body: JSON.stringify({
          user_id: Number(b.dataset.id),
          active: b.dataset.on === "1",
        }),
      });
      showAdmin();
    };
  });
}

async function adminGroups(root) {
  const data = await api("/api/admin/groups");
  root.appendChild(
    el(`<div class="panel">
      <h2>قفل اسپانسر گروه</h2>
      <p class="muted">گروه قفل‌شده تا اسپانسر فعال / سودو باز نکند محدود می‌ماند.</p>
    </div>`)
  );
  for (const g of data.items || []) {
    root.appendChild(
      el(`<div class="item row">
        <div>
          <strong>${g.chat_id}</strong>
          <div class="muted">${esc(g.status)} · ${esc(g.lang)} · قفل: ${g.sponsor_lock ? "بله" : "خیر"}</div>
        </div>
        <button class="btn ${g.sponsor_lock ? "danger" : ""} lock" data-id="${g.chat_id}" data-on="${g.sponsor_lock ? "0" : "1"}">
          ${g.sponsor_lock ? "باز کردن قفل" : "قفل اسپانسر"}
        </button>
      </div>`)
    );
  }
  root.querySelectorAll(".lock").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/admin/groups/${b.dataset.id}/sponsor-lock`, {
        method: "POST",
        body: JSON.stringify({
          sponsor_lock: b.dataset.on === "1",
        }),
      });
      flash("قفل گروه به‌روز شد");
      showAdmin();
    };
  });
}

async function adminReports(root) {
  const data = await api("/api/admin/reports");
  root.appendChild(el(`<div class="panel"><h2>گزارش‌ها</h2></div>`));
  for (const r of data.items || []) {
    root.appendChild(
      el(`<div class="item row">
        <div>
          <strong>#${r.id}</strong> ${esc(r.target_type)}/${r.target_id}
          <div class="muted">${esc(r.reason)} · ${esc(r.status)}</div>
        </div>
        ${
          r.status === "open"
            ? `<button class="btn res" data-id="${r.id}">بستن</button>`
            : ""
        }
      </div>`)
    );
  }
  root.querySelectorAll(".res").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/admin/reports/${b.dataset.id}/resolve`, {
        method: "POST",
      });
      showAdmin();
    };
  });
}

async function adminBans(root) {
  const data = await api("/api/admin/bans");
  root.appendChild(
    el(`<div class="panel">
      <h2>بن</h2>
      <div class="row">
        <input id="banUid" class="sm" placeholder="user id" />
        <button class="btn danger" id="banBtn">بن دائم</button>
      </div>
    </div>`)
  );
  document.getElementById("banBtn").onclick = async () => {
    await api("/api/admin/bans", {
      method: "POST",
      body: JSON.stringify({
        user_id: Number(document.getElementById("banUid").value),
        forever: true,
      }),
    });
    flash("بن شد");
    showAdmin();
  };
  for (const b of data.items || []) {
    root.appendChild(
      el(`<div class="item row">
        <span>#${b.id} user ${b.user_id} ${b.forever ? "دائم" : ""}</span>
        <button class="btn ghost unban" data-id="${b.id}">حذف بن</button>
      </div>`)
    );
  }
  root.querySelectorAll(".unban").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/admin/bans/${b.dataset.id}`, { method: "DELETE" });
      showAdmin();
    };
  });
}

async function adminChallenges(root) {
  const data = await api("/api/admin/challenges");
  root.appendChild(el(`<div class="panel"><h2>چالش‌ها</h2></div>`));
  for (const c of data.items || []) {
    root.appendChild(
      el(`<div class="item row">
        <div>
          <strong>${esc(c.title)}</strong>
          <div class="muted">#${c.id} · ${esc(c.status)} · stake ${c.stake}</div>
        </div>
        ${
          c.status === "open"
            ? `<button class="btn danger ghost close" data-id="${c.id}">بستن</button>`
            : ""
        }
      </div>`)
    );
  }
  root.querySelectorAll(".close").forEach((b) => {
    b.onclick = async () => {
      await api(`/api/admin/challenges/${b.dataset.id}/close`, {
        method: "POST",
      });
      showAdmin();
    };
  });
}

async function adminSettings(root) {
  const s = await api("/api/admin/settings");
  root.appendChild(
    el(`<div class="panel">
      <h2>تنظیمات سودو</h2>
      <label class="row"><input type="checkbox" id="chLive" ${s.charge_live ? "checked" : ""}/> درگاه زنده (charge_live)</label>
      <label class="row"><input type="checkbox" id="manGrant" ${s.manual_grants_enabled !== false ? "checked" : ""}/> اعطای دستی فعال</label>
      <label class="row"><input type="checkbox" id="spDef" ${s.sponsor_lock_default ? "checked" : ""}/> قفل اسپانسر پیش‌فرض</label>
      <button class="btn" id="saveSet" style="margin-top:.75rem">ذخیره</button>
      <p class="muted" style="margin-top:.75rem">وقتی درگاه تأیید شد charge_live را روشن کن؛ پرداخت‌ها خودکار می‌شوند و نقش سودو می‌شود تعمیر تراکنش خراب.</p>
    </div>`)
  );
  document.getElementById("saveSet").onclick = async () => {
    await api("/api/admin/settings", {
      method: "PATCH",
      body: JSON.stringify({
        charge_live: document.getElementById("chLive").checked,
        manual_grants_enabled: document.getElementById("manGrant").checked,
        sponsor_lock_default: document.getElementById("spDef").checked,
      }),
    });
    flash("تنظیمات ذخیره شد");
  };
}

async function route() {
  renderTabs();
  try {
    if (!state.me) await loadMe();
    const params = new URLSearchParams(location.search);
    const v = params.get("view");
    if (!state._deepLinked && v) {
      state._deepLinked = true;
      if (v === "admin" && state.isSudo) {
        state.view = "admin";
      } else if (
        [
          "hero",
          "achievements",
          "tournament",
          "online",
          "shop",
          "challenge",
          "profile",
          "ranks",
          "feed",
        ].includes(v)
      ) {
        state.view = v;
      }
      renderTabs();
    }
    if (state.view === "feed") await showFeed();
    else if (state.view === "ranks") await showRanks();
    else if (state.view === "shop") await showShop();
    else if (state.view === "hero") await showHero();
    else if (state.view === "achievements")
      await showAchievements();
    else if (state.view === "tournament")
      await showTournament();
    else if (state.view === "online") await showOnline();
    else if (state.view === "challenge") await showChallenge();
    else if (state.view === "admin") await showAdmin();
    else await showProfile();
  } catch (e) {
    document.getElementById("app").innerHTML =
      `<p class="error">${esc(e.message)}</p>
       <p class="muted">در دیباگ بدون تلگرام، DEBUG_MODE=true و SUDO_IDS را در .env بگذارید.</p>`;
  }
}

document.querySelectorAll(".tabs button").forEach((b) => {
  b.onclick = () => {
    state.view = b.dataset.view;
    route();
  };
});

route();
