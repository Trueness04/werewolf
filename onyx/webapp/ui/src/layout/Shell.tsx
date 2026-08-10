import { NavLink, Outlet } from "react-router-dom";
import { useSession } from "../context/SessionContext";

const links = [
  { to: "/", label: "خانه", end: true },
  { to: "/ranks", label: "رنک", end: false },
  { to: "/shop", label: "شاپ", end: false },
  { to: "/more", label: "بیشتر", end: false },
  { to: "/me", label: "من", end: false },
];

export function Shell() {
  const { me, error } = useSession();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">اونیکس</div>
        <div className="top-meta">
          {me ? `${me.coins.toLocaleString("fa-IR")} سکه` : "…"}
        </div>
      </header>
      <main className="page">
        {error ? <p className="error">{error}</p> : null}
        <Outlet />
      </main>
      <nav className="rail" aria-label="ناوبری اصلی">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
