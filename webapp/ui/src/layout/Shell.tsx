import { NavLink, Outlet } from "react-router-dom";
import {
  Home2,
  More,
  Profile,
  Rank,
  Shop,
} from "iconsax-reactjs";
import { useSession } from "../context/SessionContext";

const links = [
  { to: "/", label: "خانه", end: true, Icon: Home2 },
  { to: "/ranks", label: "رنک", end: false, Icon: Rank },
  { to: "/shop", label: "شاپ", end: false, Icon: Shop },
  { to: "/more", label: "بیشتر", end: false, Icon: More },
  { to: "/me", label: "من", end: false, Icon: Profile },
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
        {links.map(({ to, label, end, Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => (isActive ? "active" : undefined)}
          >
            <Icon size="22" variant="Linear" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
