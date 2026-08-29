"use client";

import { useRef } from "react";
import Button from "@/components/Button";
import ErrorBanner from "@/components/ErrorBanner";
import type { CloudProvider } from "@/lib/api";

interface UploadScreenProps {
  provider: CloudProvider;
  setProvider: (p: CloudProvider) => void;
  file: File | null;
  setFile: (f: File | null) => void;
  onContinue: () => void;
  loading: boolean;
  error: string | null;
}

const PROVIDERS: { key: CloudProvider; label: string }[] = [
  { key: "aws", label: "AWS" },
  { key: "azure", label: "Azure" },
  { key: "gcp", label: "GCP" },
  { key: "focus", label: "FOCUS" },
];

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadScreen({ provider, setProvider, file, setFile, onContinue, loading, error }: UploadScreenProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="screen-enter d-screen" style={{ maxWidth: 720 }}>
      <div style={{ marginBottom: 36 }}>
        <h1 className="d-h1">Upload billing CSV</h1>
        <p style={{ marginTop: 8, fontSize: 15, color: "var(--text-muted)" }}>
          Export from your cloud provider and drop it here. No live access needed.
        </p>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        style={{ display: "none" }}
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />

      <div
        className="d-dropzone"
        onClick={() => inputRef.current?.click()}
        style={{ animation: file ? "none" : "dropZonePulse 2.5s ease infinite" }}
      >
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-subtle)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 16 }}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <div style={{ fontSize: 16, fontWeight: 500, color: "var(--text-heading)" }}>Drop your CSV here</div>
        <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 6 }}>or click to browse · AWS, Azure, GCP, or FOCUS billing exports</div>
      </div>

      <div style={{ marginTop: 24 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-heading)", marginBottom: 10 }}>Cloud provider</div>
        <div style={{ display: "flex", gap: 8 }}>
          {PROVIDERS.map((p) => {
            const active = provider === p.key;
            return (
              <button
                key={p.key}
                className="d-provider-btn"
                onClick={() => setProvider(p.key)}
                style={{
                  border: `1px solid ${active ? "var(--ink-700)" : "var(--border-hairline)"}`,
                  background: active ? "var(--ink-700)" : "var(--surface-card)",
                  color: active ? "#fff" : "var(--text-muted)",
                }}
              >
                {p.label}
              </button>
            );
          })}
        </div>
      </div>

      {file && (
        <div className="d-file-chip">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3fb87f" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 6 9 17l-5-5" />
          </svg>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--ink-700)" }}>{file.name}</span>
          <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-muted)" }}>{formatSize(file.size)}</span>
        </div>
      )}

      {error && (
        <div style={{ marginTop: 20 }}>
          <ErrorBanner message={error} />
        </div>
      )}

      <div style={{ marginTop: 28, display: "flex", justifyContent: "flex-end" }}>
        <Button variant="dark" onClick={onContinue} disabled={!file || loading}>
          {loading ? "Uploading…" : "Continue to service tiers →"}
        </Button>
      </div>
    </div>
  );
}
