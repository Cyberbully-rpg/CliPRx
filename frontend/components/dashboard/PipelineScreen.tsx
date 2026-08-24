"use client";

const STAGES = [
  { label: "Data ingestion", desc: "Parsing CSV → normalized DataFrame" },
  { label: "Isolation Forest", desc: "Anomaly scoring (0.0–1.0)" },
  { label: "Pattern matching", desc: "Checking against provider pattern library" },
  { label: "Failure scoring", desc: "Risk level assignment" },
  { label: "Conflict resolution", desc: "Tier safety model" },
  { label: "ROI ranking", desc: "Sorting by savings-to-effort ratio" },
  { label: "Gemini authoring", desc: "Sprint ticket text generation" },
];

interface PipelineScreenProps {
  serviceCount: number;
  provider: string;
  done: boolean;
}

/**
 * The backend runs the whole pipeline in one synchronous call (no job queue,
 * no per-stage progress to poll), so this can't show real granular progress.
 * It shows the same 7-stage checklist as decoration around one real request:
 * all "pending" while the request is in flight, all flip to "done" together
 * once it resolves.
 */
export default function PipelineScreen({ serviceCount, provider, done }: PipelineScreenProps) {
  return (
    <div className="screen-enter d-screen" style={{ maxWidth: 580, textAlign: "center" }}>
      {!done && <div className="d-pipeline-spinner" />}
      <h1 style={{ fontFamily: "var(--font-serif-display)", fontSize: 28, fontWeight: 400, color: "var(--text-heading)" }}>
        {done ? "Analysis complete" : "Running DIPPA pipeline"}
      </h1>
      <p style={{ marginTop: 8, fontSize: 14, color: "var(--text-muted)" }}>
        Analyzing {serviceCount} services · {provider.toUpperCase()}
      </p>

      <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 0, textAlign: "left" }}>
        {STAGES.map((stage, i) => {
          const running = !done && i === 0;
          const bg = done ? "#3fb87f" : running ? "var(--ink-700)" : "var(--surface-sunken)";
          const labelColor = done || running ? "var(--ink-700)" : "var(--text-subtle)";
          return (
            <div className="d-stage-row" key={stage.label}>
              <div className="d-stage-icon" style={{ background: bg }}>
                {done ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                ) : running ? (
                  <div style={{ width: 10, height: 10, borderRadius: 999, background: "#fff", animation: "pipelinePulse 1.2s ease infinite" }} />
                ) : (
                  <div style={{ width: 6, height: 6, borderRadius: 999, background: "var(--text-subtle)" }} />
                )}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 500, color: labelColor }}>{stage.label}</div>
                <div style={{ fontSize: 12, color: "var(--text-subtle)", marginTop: 1 }}>{stage.desc}</div>
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-subtle)" }}>
                {done ? "✓" : running ? "…" : ""}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
