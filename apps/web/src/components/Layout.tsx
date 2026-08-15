import { NavLink, Outlet } from "react-router-dom";
import { useTracker } from "../lib/useTracker";

const links = [
  { to: "/jobs", label: "Jobs" },
  { to: "/countries", label: "Countries" },
  { to: "/me", label: "My week" },
];

function Mark() {
  return (
    <svg className="mark" viewBox="0 0 28 28" width="28" height="28" aria-hidden>
      <path
        d="M6 20c4-1 7-4.4 7.8-8.4C14.2 14 15.6 16.2 18 17.4c1 .6 2.2 1 3.4 1.1"
        fill="none"
        stroke="#E8A017"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="14" cy="9.2" r="1.8" fill="#E8A017" />
    </svg>
  );
}

export function Layout() {
  const { thisWeek, target } = useTracker();
  const pct = Math.min(100, Math.round((thisWeek / target) * 100));

  return (
    <>
      <header className="header">
        <div className="wrap header-inner">
          <NavLink to="/" className="wordmark">
            <Mark />
            0pening
          </NavLink>
          <nav className="nav" aria-label="Primary">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? "active" : "")}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <NavLink to="/me" className="header-week" title="This week's applications">
            <span className="hide-sm">This week</span>
            <strong>
              {thisWeek}/{target}
            </strong>
            <span className="mini-bar" aria-hidden>
              <i style={{ width: `${pct}%` }} />
            </span>
          </NavLink>
        </div>
      </header>
      <main className="site-main">
        <div className="wrap">
          <Outlet />
        </div>
      </main>
      <nav className="mobile-nav" aria-label="Mobile">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Home
        </NavLink>
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} className={({ isActive }) => (isActive ? "active" : "")}>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <footer className="footer">
        <div className="wrap footer-inner">
          <div>
            0pening · August 2026 openings · remote-first across 10 countries.
            <br />
            No account required. Your target and log stay on this device until we add auth.
          </div>
          <div>
            <NavLink to="/jobs">Browse jobs</NavLink>
            {" · "}
            <NavLink to="/me">Accountability</NavLink>
          </div>
        </div>
      </footer>
    </>
  );
}
