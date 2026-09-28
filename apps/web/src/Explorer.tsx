import { useEffect, useState } from "react";
import { Search, ChevronLeft, ChevronRight, ArrowUpRight } from "lucide-react";
import { api, number } from "./api";
import type { NodePage } from "./types";
const kinds = [
  "supplier",
  "site",
  "component",
  "product",
  "facility",
  "port",
  "route",
  "customer",
];
export default function Explorer({
  snapshot,
  onEvidence,
}: {
  snapshot: string;
  onEvidence: (id: string) => void;
}) {
  const [search, setSearch] = useState(""),
    [kind, setKind] = useState(""),
    [offset, setOffset] = useState(0),
    [page, setPage] = useState<NodePage | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    const timer = setTimeout(() => {
      api<NodePage>(
        `/nodes?${new URLSearchParams({ snapshot_id: snapshot, search, kind, offset: String(offset), limit: "25" })}`,
        { signal: controller.signal },
      )
        .then((r) => {
          setPage(r);
          setError("");
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [snapshot, search, kind, offset]);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">EVIDENCE EXPLORER</span>
          <h1>Every node has a story.</h1>
          <p className="muted">
            Inspect the raw records behind every computed result.
          </p>
        </div>
        <span className="pill green">RAW DATA</span>
      </div>
      <section className="panel">
        <div className="table-toolbar">
          <div className="search-field">
            <Search size={16} />
            <input
              aria-label="Search evidence"
              placeholder="Search name, ID, or country…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setOffset(0);
              }}
            />
          </div>
          <select
            aria-label="Filter node kind"
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All node types</option>
            {kinds.map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className={`table-wrap ${loading ? "pending" : ""}`}>
          <table>
            <thead>
              <tr>
                <th>Entity</th>
                <th>Type</th>
                <th>Location</th>
                <th>Tier / demand</th>
                <th>Source</th>
                <th>
                  <span className="sr-only">Inspect</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {page?.items.map((n) => (
                <tr key={n.id}>
                  <td>
                    <button
                      className="text-link entity"
                      onClick={() => onEvidence(n.id)}
                    >
                      {n.name}
                      <small>{n.id}</small>
                    </button>
                  </td>
                  <td>
                    <span className="pill">{n.kind}</span>
                  </td>
                  <td>{n.country}</td>
                  <td>
                    {n.tier
                      ? `Tier ${n.tier}`
                      : n.daily_demand
                        ? `${number(n.daily_demand)} units/day`
                        : "—"}
                  </td>
                  <td>
                    <code className="muted">{n.source_id}</code>
                  </td>
                  <td>
                    <button
                      aria-label={`Inspect ${n.id}`}
                      className="icon-button"
                      onClick={() => onEvidence(n.id)}
                    >
                      <ArrowUpRight size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {page?.items.length === 0 && (
            <div className="empty">No records match this filter.</div>
          )}
        </div>
        <div className="table-footer">
          <span>
            {loading ? "Loading…" : `${number(page?.total || 0)} records`} ·
            Page {offset / 25 + 1}
          </span>
          <div>
            <button
              className="icon-button"
              disabled={!offset}
              onClick={() => setOffset((v) => v - 25)}
              aria-label="Previous page"
            >
              <ChevronLeft size={17} />
            </button>
            <button
              className="icon-button"
              disabled={offset + 25 >= (page?.total || 0)}
              onClick={() => setOffset((v) => v + 25)}
              aria-label="Next page"
            >
              <ChevronRight size={17} />
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
