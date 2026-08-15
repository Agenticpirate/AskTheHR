import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { AccountabilityWidget } from "../components/AccountabilityWidget";
import { formatShortDate } from "../lib/dates";
import { useTracker } from "../lib/useTracker";

export function Me() {
  const tracker = useTracker();
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [url, setUrl] = useState("");

  const onManual = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    tracker.log({
      title: title.trim(),
      company: company.trim() || "Unlisted company",
      url: url.trim() || undefined,
    });
    setTitle("");
    setCompany("");
    setUrl("");
  };

  return (
    <>
      <div className="eyebrow">Accountability</div>
      <h1>My week</h1>
      <p className="lede">
        Set a weekly application target. Log roles from the board or add one by hand. This lives
        in localStorage today — same shape we will attach to a nickname + Cloudflare worker later.
      </p>

      <div className="me-grid" style={{ marginTop: 28 }}>
        <div style={{ display: "grid", gap: 16 }}>
          <AccountabilityWidget />
          <section className="card flat">
            <h3>Your setup</h3>
            <div className="field" style={{ marginBottom: 12 }}>
              <label htmlFor="nick">Nickname (optional)</label>
              <input
                id="nick"
                value={tracker.nickname}
                placeholder="What should we call you?"
                onChange={(e) => tracker.setNickname(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="target">Weekly target</label>
              <input
                id="target"
                type="number"
                min={1}
                max={40}
                value={tracker.target}
                onChange={(e) => tracker.setTarget(Number(e.target.value))}
              />
            </div>
            <p className="notice">
              A week runs Monday–Sunday. Hit the number and the streak holds. Auth comes later;
              do not treat this device log as a backup.
            </p>
          </section>
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          <section className="card flat">
            <h3>Log an application by hand</h3>
            <form onSubmit={onManual} style={{ display: "grid", gap: 10 }}>
              <div className="field">
                <label htmlFor="mtitle">Role</label>
                <input
                  id="mtitle"
                  value={title}
                  required
                  placeholder="Staff product designer"
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="mco">Company</label>
                <input
                  id="mco"
                  value={company}
                  placeholder="Notion"
                  onChange={(e) => setCompany(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="murl">Apply URL (optional)</label>
                <input
                  id="murl"
                  value={url}
                  placeholder="https://"
                  onChange={(e) => setUrl(e.target.value)}
                />
              </div>
              <button className="btn btn-primary" type="submit">
                Add to this week
              </button>
            </form>
          </section>

          <section>
            <div className="section-head">
              <h2>Application log</h2>
              <span className="notice">{tracker.state.applications.length} total</span>
            </div>
            {tracker.state.applications.length === 0 ? (
              <div className="empty">
                Nothing logged yet.{" "}
                <Link to="/jobs?work=remote">Pick a remote role</Link> and press “I applied”.
              </div>
            ) : (
              <div className="log">
                {tracker.state.applications.map((a) => (
                  <div className="log-item" key={a.id}>
                    <div>
                      <strong>{a.title}</strong>
                      <div className="notice">
                        {a.company}
                        {a.country ? ` · ${a.country}` : ""} · {formatShortDate(a.appliedAt)}
                        {a.url ? (
                          <>
                            {" · "}
                            <a href={a.url} target="_blank" rel="noreferrer">
                              listing
                            </a>
                          </>
                        ) : null}
                      </div>
                    </div>
                    <button type="button" onClick={() => tracker.remove(a.id)} aria-label="Remove">
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </>
  );
}
