import { Link } from "react-router-dom";
import { useSession } from "../context/SessionContext";

const items = [
  { to: "/challenge", title: "چالش", desc: "فقط وب‌اپ" },
  { to: "/hero", title: "هیرو", desc: "ساخت و مدیریت هیرو" },
  { to: "/achievements", title: "دستاورد", desc: "مدال‌ها و آنلاک‌ها" },
  { to: "/tournament", title: "تورنمنت", desc: "ورود با استیک سکه" },
  { to: "/online", title: "آنلاین", desc: "صف بازی آنلاین" },
];

export function MorePage() {
  const { isSudo } = useSession();

  return (
    <>
      <h1 className="page-title">بیشتر</h1>
      <p className="lede">مسیرهای جدا از خانه — طبق پلن محصول</p>
      <div className="more-grid">
        {items.map((it) => (
          <Link className="more-link" key={it.to} to={it.to}>
            {it.title}
            <span>{it.desc}</span>
          </Link>
        ))}
        {isSudo ? (
          <Link className="more-link" to="/admin">
            مدیریت
            <span>پنل سودو</span>
          </Link>
        ) : null}
      </div>
    </>
  );
}
