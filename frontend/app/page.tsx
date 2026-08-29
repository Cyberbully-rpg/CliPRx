import Link from "next/link";
import Nav from "@/components/landing/Nav";
import Reveal from "@/components/landing/Reveal";
import Faq from "@/components/landing/Faq";
import ParallaxClouds from "@/components/landing/ParallaxClouds";
import Button from "@/components/Button";

const ConflictIcon = ({ size = 12 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#e2544a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

export default function LandingPage() {
  return (
    <>
      <a id="top" aria-hidden="true" />
      <Nav />

      <header className="l-hero">
        <div style={{ position: "absolute", inset: 0, background: "#060806" }} />
        <video
          src="/assets/hero-bg.mp4"
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          poster="/assets/hero-poster.png"
          className="l-hero-video"
        />
        <div className="l-hero-scrim" />
        <div className="l-hero-fade" />

        <div className="l-hero-inner">
          <h1 className="l-hero-h1">
            Your cloud bill has an owner. <span style={{ color: "rgba(255,255,255,.5)" }}>This gives them a ranked plan.</span>
          </h1>
          <p className="l-hero-sub">Upload a CSV. Get ranked, risk-scored cost fixes as sprint tickets.</p>
          <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 32 }}>
            <Button as="a" href="#sample" variant="cream" style={{ height: 36 }}>
              See a sample report
            </Button>
            <Button as="a" href="/app" variant="glass" style={{ height: 36 }}>
              Upload your CSV
            </Button>
          </div>
          <div style={{ display: "flex", justifyContent: "center", gap: 18, marginTop: 24, fontFamily: "var(--font-mono)", fontSize: 12, letterSpacing: "0.04em", color: "rgba(255,255,255,.45)" }}>
            <span>AWS · Azure · GCP</span>
          </div>
        </div>
      </header>

      <Reveal as="section" id="mechanism" className="reveal l-section">
        <div style={{ maxWidth: 640, marginBottom: 52 }}>
          <div className="l-mono-label">the pipeline</div>
          <h2 className="l-section-head">
            CSV in, ranked tickets out. <span className="l-muted">No black box.</span>
          </h2>
        </div>
        <div className="stagger l-grid-3">
          <div className="card-lift l-card">
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 14 }}>
              <span className="l-card-num">01</span>
              <h3 className="l-card-title">Ingest</h3>
            </div>
            <p className="l-card-body">Isolation Forest scores every line item. Rows above threshold match against a per-provider pattern library.</p>
            <div className="l-sunken" style={{ fontFamily: "var(--font-mono)", fontSize: 12, overflow: "hidden" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 12px", color: "var(--text-subtle)", borderBottom: "1px solid var(--border-hairline)" }}>
                <span>service</span><span>cost</span><span>anomaly</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 12px", color: "var(--ink-700)", borderBottom: "1px solid var(--border-hairline)" }}>
                <span>ec2-web-asg</span><span>$4,210</span><span style={{ color: "#8a5a12" }}>0.87</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "9px 12px", color: "var(--ink-700)" }}>
                <span>s3-logs-cold</span><span>$180</span><span style={{ color: "var(--text-subtle)" }}>0.12</span>
              </div>
            </div>
          </div>

          <div className="card-lift l-card">
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 14 }}>
              <span className="l-card-num">02</span>
              <h3 className="l-card-title">Score</h3>
            </div>
            <p className="l-card-body">Risk and failure-cost reconciled through the tier safety model. Protected services flagged, never silently dropped.</p>
            <div className="l-sunken" style={{ padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink-700)" }}>rds-analytics</span>
                <span className="l-badge" style={{ marginLeft: "auto", background: "rgba(233,162,59,.14)", color: "#8a5a12" }}>Medium</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12, color: "#a23c34", background: "rgba(226,84,74,.1)", border: "1px solid rgba(226,84,74,.2)", borderRadius: 6, padding: "7px 10px" }}>
                <ConflictIcon size={13} />
                conflict: tier-2 touch, flagged
              </div>
            </div>
          </div>

          <div className="card-lift l-card">
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 14 }}>
              <span className="l-card-num">03</span>
              <h3 className="l-card-title">Ship</h3>
            </div>
            <p className="l-card-body">Ranked by ROI, each ticket carries a savings range and effort estimate. Drops straight into a sprint.</p>
            <div className="l-sunken" style={{ padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 9 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-subtle)" }}>CLIP-104</span>
                <span className="l-badge l-badge-low">Low risk</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "var(--ink-700)", lineHeight: 1.45, marginBottom: 12 }}>Right-size idle web ASG instances</div>
              <div style={{ display: "flex", gap: 16, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }}>
                <span style={{ color: "#2f7d59" }}>$1,200–1,800/mo</span><span>3–5 eng-hrs</span>
              </div>
            </div>
          </div>
        </div>
      </Reveal>

      <ParallaxClouds />

      <Reveal as="section" id="sample" className="reveal l-section">
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", justifyContent: "space-between", gap: 20, marginBottom: 44 }}>
          <div style={{ maxWidth: 640 }}>
            <div className="l-mono-label">sample report · no form, no gate</div>
            <h2 className="l-section-head">What a real report looks like.</h2>
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-muted)", textAlign: "right", lineHeight: 1.7 }}>
            3 prescriptions · 1 conflict<br /><span style={{ color: "#2f7d59" }}>$2,140–3,220</span> est. monthly savings
          </div>
        </div>
        <div className="stagger" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <article className="l-rx">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 15, color: "var(--text-subtle)", paddingTop: 2 }}>01</div>
            <div>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 15, fontWeight: 500, color: "var(--ink-700)" }}>ec2-prod-asg-web</span>
                <span className="l-badge l-badge-low">Low risk</span>
                <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 500, color: "#2f7d59" }}>$1,200–1,800/mo</span>
              </div>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "var(--text-body)", maxWidth: 760 }}>3 of 8 instances idle above 40% for 14 days. Right-size m5.2xlarge → m5.xlarge and enable target-tracking on the ASG. No tier-1 or tier-2 dependencies.</p>
              <div style={{ display: "flex", gap: 18, marginTop: 12, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }}>
                <span>effort 3–5 eng-hrs</span><span>anomaly 0.87</span><span>ROI rank 1</span>
              </div>
            </div>
          </article>

          <article className="l-rx">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 15, color: "var(--text-subtle)", paddingTop: 2 }}>02</div>
            <div>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 15, fontWeight: 500, color: "var(--ink-700)" }}>s3-analytics-exports</span>
                <span className="l-badge l-badge-low">Low risk</span>
                <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 500, color: "#2f7d59" }}>$640–900/mo</span>
              </div>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "var(--text-body)", maxWidth: 760 }}>2.4 TB in Standard untouched for 90+ days. Add a lifecycle rule to Glacier Instant Retrieval. Read pattern is archival, not hot.</p>
              <div style={{ display: "flex", gap: 18, marginTop: 12, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }}>
                <span>effort 1–2 eng-hrs</span><span>anomaly 0.71</span><span>ROI rank 2</span>
              </div>
            </div>
          </article>

          <article className="l-rx conflicted">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 15, color: "var(--text-subtle)", paddingTop: 2 }}>03</div>
            <div>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 15, fontWeight: 500, color: "var(--ink-700)" }}>elasticache-session-store</span>
                <span className="l-badge l-badge-high">High risk</span>
                <span className="l-conflict-chip"><ConflictIcon />conflict · tier-2</span>
                <span style={{ marginLeft: "auto", fontFamily: "var(--font-mono)", fontSize: 14, fontWeight: 500, color: "var(--text-muted)" }}>$300–520/mo</span>
              </div>
              <p style={{ fontSize: 15, lineHeight: 1.6, color: "var(--text-body)", maxWidth: 760 }}>Node type looks over-provisioned, but this is a tier-2 core service. Surfaced for manual review and sorted to the bottom of the ranked list — never applied automatically.</p>
              <div style={{ display: "flex", gap: 18, marginTop: 12, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)" }}>
                <span>effort 4–6 eng-hrs</span><span>anomaly 0.79</span><span style={{ color: "#a23c34" }}>ROI rank last</span>
              </div>
            </div>
          </article>
        </div>
      </Reveal>

      <Reveal as="section" className="reveal l-section">
        <div className="stagger l-grid-3" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <div className="l-card">
            <h3 style={{ fontSize: 24, fontWeight: 500, color: "var(--text-heading)", marginBottom: 22 }}>Built for</h3>
            <ul className="l-list">
              <li><span style={{ color: "#3fb87f", marginTop: 1 }}>✓</span>The hands-on infra owner who personally answers for the AWS/Azure/GCP bill.</li>
              <li><span style={{ color: "#3fb87f", marginTop: 1 }}>✓</span>Series A–C startups and mid-market teams, no dedicated FinOps hire.</li>
              <li><span style={{ color: "#3fb87f", marginTop: 1 }}>✓</span>$5K–150K/month spend, where 10–20% actually moves the number.</li>
              <li><span style={{ color: "#3fb87f", marginTop: 1 }}>✓</span>Primarily one cloud, with the domain knowledge to declare tiers.</li>
              <li><span style={{ color: "#3fb87f", marginTop: 1 }}>✓</span>An engineering team that can execute a ticket once it lands.</li>
            </ul>
          </div>
          <div className="l-sunken" style={{ padding: "36px 34px", borderRadius: "var(--radius-card)" }}>
            <h3 style={{ fontSize: 24, fontWeight: 500, color: "var(--text-muted)", marginBottom: 22 }}>Not built for</h3>
            <ul className="l-list" style={{ color: "var(--text-muted)" }}>
              <li><span style={{ color: "var(--text-subtle)", marginTop: 1 }}>—</span>Enterprises with a dedicated FinOps team running continuous governance.</li>
              <li><span style={{ color: "var(--text-subtle)", marginTop: 1 }}>—</span>Non-technical finance or procurement — the tier step assumes infra knowledge.</li>
              <li><span style={{ color: "var(--text-subtle)", marginTop: 1 }}>—</span>Heavy multi-cloud shops needing one unified cross-provider view.</li>
              <li><span style={{ color: "var(--text-subtle)", marginTop: 1 }}>—</span>Teams needing multi-seat review, comments, or ticket assignment.</li>
            </ul>
          </div>
        </div>
      </Reveal>

      <Reveal as="section" id="docs" className="reveal l-section" style={{ maxWidth: 900 }}>
        <div style={{ marginBottom: 40 }}>
          <div className="l-mono-label">the questions you'd actually ask</div>
          <h2 className="l-section-head">Objections, answered plainly.</h2>
        </div>
        <Faq />
      </Reveal>

      <Reveal as="section" id="start" className="reveal l-cta-video-wrap">
        <video autoPlay muted loop playsInline preload="auto" className="l-cta-video">
          <source src="/assets/footer-bg.mp4" type="video/mp4" />
        </video>
        <div className="l-cta-scrim" />
        <div className="l-cta-inner">
          <h2 style={{ fontFamily: "var(--font-serif-display)", fontSize: 52, lineHeight: 1.1, fontWeight: 400, color: "#fff", maxWidth: 580, margin: "0 auto" }}>Start now</h2>
          <p style={{ margin: "20px auto 0", maxWidth: 400, fontSize: 16, lineHeight: 1.6, color: "rgba(255,255,255,.65)" }}>One CSV. A few seconds. A ranked plan.</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center", marginTop: 38 }}>
            <span className="glow-btn">
              <Button as="a" href="/app" variant="cream" style={{ height: 36 }}>Start now →</Button>
            </span>
          </div>
          <Link href="#top" style={{ display: "inline-block", marginTop: 24, fontSize: 13, color: "rgba(255,255,255,.5)", borderBottom: "1px solid rgba(255,255,255,.2)", paddingBottom: 2 }}>
            Running this for clients? Talk to us →
          </Link>
        </div>
      </Reveal>

      <footer className="l-footer">
        <div className="l-footer-inner">
          <span style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--font-mono)", fontSize: 17, fontWeight: 500, color: "var(--ink-700)" }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: "var(--signal-running)" }} />CliPRx
          </span>
          <nav style={{ display: "flex", flexWrap: "wrap", gap: 22, fontSize: 14 }}>
            <Link className="footlink" href="#mechanism">Product</Link>
            <Link className="footlink" href="#sample">Sample report</Link>
            <Link className="footlink" href="#start">Start now</Link>
            <Link className="footlink" href="#docs">Docs</Link>
            <Link className="footlink" href="#docs">Privacy</Link>
          </nav>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginLeft: "auto" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)", border: "1px solid var(--border-hairline)", borderRadius: 6, padding: "5px 9px" }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>
              SOC 2
            </span>
            <span style={{ fontSize: 13, color: "var(--text-subtle)" }}>© 2026 CliPRx</span>
          </div>
        </div>
      </footer>
    </>
  );
}
