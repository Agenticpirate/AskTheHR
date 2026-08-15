import { Link } from "react-router-dom";
import { formatWeekLabel, weekKey } from "../lib/dates";
import { useTracker } from "../lib/useTracker";

export function AccountabilityWidget({ compact = false }: { compact?: boolean }) {
  const { thisWeek, target, streak, nickname } = useTracker();
  const pct = Math.min(100, Math.round((thisWeek / target) * 100));
  const remaining = Math.max(0, target - thisWeek);

  return (
    <section className="card acct" aria-label="Weekly accountability">
      <div className="acct-top">
        <div>
          <div className="eyebrow">This week</div>
          <h2 style={{ marginBottom: 4 }}>{formatWeekLabel(weekKey(new Date()))}</h2>
          <p className="notice" style={{ margin: 0 }}>
            {nickname ? `${nickname} · ` : ""}
            {thisWeek >= target
              ? "Target hit. Keep going if you want."
              : `${remaining} more ${remaining === 1 ? "application" : "applications"} to hit the target.`}
          </p>
        </div>
      </div>
      <div className="progress" aria-hidden>
        <i style={{ width: `${pct}%` }} />
      </div>
      <div className="stat-row">
        <div className="stat">
          <div className="n">
            {thisWeek}/{target}
          </div>
          <div className="l">Applications</div>
        </div>
        <div className="stat">
          <div className="n">{streak}</div>
          <div className="l">{streak === 1 ? "Week streak" : "Week streak"}</div>
        </div>
        <div className="stat">
          <div className="n">{pct}%</div>
          <div className="l">Of target</div>
        </div>
      </div>
      {!compact && (
        <div className="btn-row">
          <Link className="btn btn-primary" to="/me">
            Open my dashboard
          </Link>
          <Link className="btn btn-ghost" to="/jobs?work=remote">
            Find a role
          </Link>
        </div>
      )}
    </section>
  );
}
