import { useEffect, useState } from "react";
import {
  Database,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Download,
} from "lucide-react";
import { api, ApiError } from "./api";
import type { Config, Report, Snapshot } from "./types";
export default function DataPage({
  snapshots,
  current,
  config,
  onChange,
  onImported,
}: {
  snapshots: Snapshot[];
  current: string;
  config: Config | null;
  onChange: (id: string) => void;
  onImported: () => void;
}) {
  const [reports, setReports] = useState<Report[]>([]),
    [token, setToken] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const loadReports = () =>
    api<Report[]>("/validation-reports")
      .then(setReports)
      .catch((e) => setError(e.message));
  useEffect(() => {
    void loadReports();
  }, []);
  async function ingest(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const form = new FormData();
      form.append("file", file);
      const result = await api<{ created: boolean; report: Report }>(
        "/ingestions",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Idempotency-Key": crypto.randomUUID(),
          },
          body: form,
        },
      );
      setMessage(
        result.created
          ? "Snapshot imported. All records passed validation."
          : "Identical snapshot already exists.",
      );
      onImported();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
      void loadReports();
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">DATA FOUNDATION</span>
          <h1>Trust starts at the source.</h1>
          <p className="muted">
            Versioned snapshots, explicit provenance, and visible validation.
          </p>
        </div>
        <Database size={34} className="accent" />
      </div>
      <div className="two-column">
        <section className="panel">
          <div className="section-heading">
            <h3>Temporal snapshots</h3>
            <span className="subtle-badge">IMMUTABLE</span>
          </div>
          {snapshots.map((s) => (
            <div
              className={`snapshot-row ${s.id === current ? "selected" : ""}`}
              key={s.id}
            >
              <div>
                <strong>{s.id}</strong>
                <p className="muted">
                  {new Date(s.effective_at).toLocaleDateString("en-US", {
                    timeZone: "UTC",
                    dateStyle: "long",
                  })}{" "}
                  · Seed {s.seed}
                </p>
                <code title={s.digest}>SHA256 {s.digest.slice(0, 16)}…</code>
              </div>
              <div className="snapshot-actions">
                <button className="secondary" onClick={() => onChange(s.id)}>
                  {s.id === current ? "Selected" : "Select"}
                </button>
                <a
                  className="icon-button"
                  aria-label={`Export ${s.id}`}
                  href={`/api/v1/snapshots/${encodeURIComponent(s.id)}/export`}
                >
                  <Download size={17} />
                </a>
              </div>
            </div>
          ))}
        </section>
        <section className="panel">
          <h3>
            <Upload size={17} /> Import a snapshot
          </h3>
          <p className="muted">
            Validated JSON · 25 MiB maximum · Atomic import
          </p>
          <form className="upload-form" onSubmit={ingest}>
            <label>
              Write token
              <input
                type="password"
                autoComplete="off"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Stored only in this form"
              />
            </label>
            <label>
              Dataset file
              <input
                type="file"
                accept="application/json,.json"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
            <button
              className="primary"
              disabled={!config?.mutation_enabled || !token || !file || busy}
            >
              {busy ? "Validating…" : "Validate & import"}
              <Upload size={15} />
            </button>
          </form>
          {!config?.mutation_enabled && (
            <p className="muted">
              Ingestion is disabled. Set WRITE_API_TOKEN on the server to enable
              imports.
            </p>
          )}
          {message && (
            <p className="success" role="status">
              {message}
            </p>
          )}
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </section>
      </div>
      <section className="panel report-panel">
        <div className="section-heading">
          <h3>Validation ledger</h3>
          <span className="muted">Latest available reports</span>
        </div>
        {reports.length === 0 ? (
          <p className="empty">No validation reports yet.</p>
        ) : (
          reports.map((r) => (
            <details key={r.id} className="report">
              <summary>
                <span className={r.valid ? "success" : "warning"}>
                  {r.valid ? (
                    <CheckCircle2 size={17} />
                  ) : (
                    <AlertTriangle size={17} />
                  )}
                </span>
                <strong>{r.filename}</strong>
                <span className="muted">
                  {r.node_count.toLocaleString()} nodes ·{" "}
                  {r.edge_count.toLocaleString()} edges
                </span>
                <span className={`pill ${r.valid ? "green" : "orange"}`}>
                  {r.valid ? "Accepted" : "Rejected"} · {r.warnings.length}{" "}
                  warnings
                </span>
              </summary>
              <p>
                <code>{r.id}</code>
              </p>
              {[...r.errors, ...r.warnings].map((issue, i) => (
                <p key={i}>
                  <code>{issue.code}</code> — {issue.message} {issue.record_id}
                </p>
              ))}
              {!r.errors.length && !r.warnings.length && (
                <p>All records passed validation.</p>
              )}
            </details>
          ))
        )}
      </section>
    </>
  );
}
