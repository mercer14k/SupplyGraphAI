import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Box,
  ChevronDown,
  CircleHelp,
  Database,
  Download,
  Expand,
  GitBranch,
  Globe2,
  Layers3,
  Menu,
  Network,
  Play,
  Search,
  Settings2,
  ShieldCheck,
  Waypoints,
  X,
  Zap,
} from "lucide-react";
import { api, download, money, number } from "./api";
import type {
  Config,
  GraphData,
  Impact,
  NodePage,
  Overview,
  Scenario,
  Snapshot,
} from "./types";
import EvidenceDrawer from "./EvidenceDrawer";
import QueryPanel from "./QueryPanel";
import DataPage from "./DataPage";
import Explorer from "./Explorer";
import About from "./About";
const NetworkCanvas = lazy(() => import("./NetworkCanvas"));
const navigation = [
  { id: "network", label: "Network overview", icon: Network },
  { id: "scenarios", label: "Disruption lab", icon: Zap },
  { id: "evidence", label: "Evidence explorer", icon: Layers3 },
  { id: "data", label: "Data & snapshots", icon: Database },
  { id: "about", label: "Architecture", icon: GitBranch },
];

function ImpactTable({
  impacts,
  onEvidence,
}: {
  impacts: Impact[];
  onEvidence: (id: string) => void;
}) {
  const [search, setSearch] = useState(""),
    [productsOnly, setProductsOnly] = useState(true),
    [page, setPage] = useState(0);
  const rows = impacts
    .filter(
      (i) =>
        (!productsOnly || i.kind === "product") &&
        (i.name + i.node_id).toLowerCase().includes(search.toLowerCase()),
    )
    .sort(
      (a, b) =>
        b.exposure_value - a.exposure_value || a.shortage_day - b.shortage_day,
    );
  const currentPage = Math.min(
    page,
    Math.max(0, Math.ceil(rows.length / 8) - 1),
  );
  return (
    <section className="panel impact-table">
      <div className="section-heading">
        <div>
          <span className="eyebrow">COMPUTED EXPOSURE</span>
          <h3>Follow the impact</h3>
        </div>
        <div className="table-actions">
          <button
            className={`filter-chip ${productsOnly ? "active" : ""}`}
            onClick={() => {
              setProductsOnly(!productsOnly);
              setPage(0);
            }}
          >
            {productsOnly ? "Products" : "All affected nodes"}
            <ChevronDown size={13} />
          </button>
          <button
            className="icon-button"
            aria-label="Export impact results"
            onClick={() => download("supplygraph-impacts.json", rows)}
          >
            <Download size={16} />
          </button>
        </div>
      </div>
      <div className="search-field table-search">
        <Search size={15} />
        <input
          aria-label="Filter impacted nodes"
          placeholder="Filter impacted nodes…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
        />
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Impacted entity</th>
              <th>Time to shortage</th>
              <th>Units at risk</th>
              <th>Value exposure</th>
              <th>Dependency path</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(currentPage * 8, currentPage * 8 + 8).map((i) => (
              <tr key={i.node_id}>
                <td>
                  <button
                    className="text-link entity"
                    onClick={() => onEvidence(i.node_id)}
                  >
                    {i.name}
                    <small>
                      {i.node_id} <span>· {i.kind}</span>
                    </small>
                  </button>
                </td>
                <td>
                  <span
                    className={`shortage ${i.shortage_day < 4 ? "warning" : ""}`}
                  >
                    {number(i.shortage_day)} days
                  </span>
                </td>
                <td>{i.kind === "product" ? number(i.lost_units) : "—"}</td>
                <td className={i.exposure_value ? "exposure" : ""}>
                  {i.exposure_value ? money(i.exposure_value) : "—"}
                </td>
                <td>
                  <div className="path-chips">
                    {i.path.slice(0, 2).map((id) => (
                      <button key={id} onClick={() => onEvidence(id)}>
                        {id}
                      </button>
                    ))}
                    {i.path.length > 2 && (
                      <details>
                        <summary>+{i.path.length - 2} nodes</summary>
                        <div>
                          {i.path.slice(2).map((id) => (
                            <button key={id} onClick={() => onEvidence(id)}>
                              {id}
                            </button>
                          ))}
                        </div>
                      </details>
                    )}
                  </div>
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`Evidence for ${i.node_id}`}
                    onClick={() => onEvidence(i.evidence_ids[0])}
                  >
                    <ArrowUpRight size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && (
          <div className="empty">
            No affected nodes match this view. Try all nodes or a longer
            disruption.
          </div>
        )}
      </div>
      <div className="table-footer">
        <span>
          {rows.length} results · {impacts.length} affected nodes in the
          scenario
        </span>
        <div>
          <button
            className="text-link"
            disabled={!currentPage}
            onClick={() => setPage(currentPage - 1)}
          >
            Previous
          </button>
          <span>
            {currentPage + 1} / {Math.max(1, Math.ceil(rows.length / 8))}
          </span>
          <button
            className="text-link"
            disabled={(currentPage + 1) * 8 >= rows.length}
            onClick={() => setPage(currentPage + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [page, setPage] = useState("network"),
    [navOpen, setNavOpen] = useState(false),
    [snapshots, setSnapshots] = useState<Snapshot[]>([]),
    [snapshot, setSnapshot] = useState(""),
    [config, setConfig] = useState<Config | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null),
    [graph, setGraph] = useState<GraphData | null>(null),
    [scenario, setScenario] = useState<Scenario | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(true);
  const [draftFocus, setDraftFocus] = useState("PORT-0001"),
    [duration, setDuration] = useState(14),
    [request, setRequest] = useState({ focus: "PORT-0001", duration: 14 }),
    [mode, setMode] = useState<"graph" | "globe">("graph"),
    [evidence, setEvidence] = useState<string | null>(null),
    [expanded, setExpanded] = useState(false),
    [sourceOptions, setSourceOptions] = useState<NodePage | null>(null),
    [reload, setReload] = useState(0);
  useEffect(() => {
    const ctrl = new AbortController();
    Promise.all([
      api<Snapshot[]>("/snapshots", { signal: ctrl.signal }),
      api<Config>("/config", { signal: ctrl.signal }),
    ])
      .then(([s, c]) => {
        setSnapshots(s);
        setSnapshot((current) => current || s[0]?.id || "");
        setConfig(c);
        if (!s.length) {
          setError(
            "No snapshots available. Import a dataset or enable demo mode.",
          );
          setBusy(false);
        }
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(e.message);
          setBusy(false);
        }
      });
    return () => ctrl.abort();
  }, [reload]);
  useEffect(() => {
    if (!snapshot) return;
    const ctrl = new AbortController();
    setBusy(true);
    setError("");
    setScenario(null);
    setGraph(null);
    setOverview(null);
    Promise.all([
      api<Overview>(`/overview?snapshot_id=${encodeURIComponent(snapshot)}`, {
        signal: ctrl.signal,
      }),
      api<GraphData>(
        `/graph?${new URLSearchParams({ snapshot_id: snapshot, focus: request.focus, limit: "200" })}`,
        { signal: ctrl.signal },
      ),
      api<Scenario>("/analysis/scenarios", {
        method: "POST",
        signal: ctrl.signal,
        body: JSON.stringify({
          snapshot_id: snapshot,
          disrupted_ids: [request.focus],
          duration_days: request.duration,
        }),
      }),
    ])
      .then(([o, g, s]) => {
        setOverview(o);
        setGraph(g);
        setScenario(s);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setBusy(false);
      });
    return () => ctrl.abort();
  }, [snapshot, request, reload]);
  useEffect(() => {
    if (!snapshot) return;
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      api<NodePage>(
        `/nodes?${new URLSearchParams({ snapshot_id: snapshot, search: draftFocus, limit: "25" })}`,
        { signal: ctrl.signal },
      )
        .then(setSourceOptions)
        .catch(() => {});
    }, 200);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [draftFocus, snapshot]);
  const impacted = useMemo(
    () => scenario?.impacts.map((i) => i.node_id) || [],
    [scenario],
  );
  const selectedNode = graph?.nodes.find((n) => n.id === request.focus);
  function changeSnapshot(id: string) {
    setSnapshot(id);
    setEvidence(null);
  }
  function focusNode(id: string) {
    setDraftFocus(id);
    setRequest({ focus: id, duration });
    setPage("scenarios");
  }
  function run(e: React.FormEvent) {
    e.preventDefault();
    setRequest({ focus: draftFocus.trim().toUpperCase(), duration });
  }
  const validResult = scenario?.snapshot_id === snapshot;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar ${navOpen ? "open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("network");
          }}
        >
          <span className="brand-mark">
            <Waypoints size={26} strokeWidth={1.6} />
          </span>
          <span>
            SupplyGraph<span className="brand-ai">AI</span>
          </span>
        </a>
        <div className="workspace-switch">
          <span className="workspace-icon">SG</span>
          <div>
            <strong>Supply network</strong>
            <small>Demo workspace</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <span className="nav-caption">WORKSPACE</span>
        <nav aria-label="Main navigation">
          {navigation.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "active" : ""}
              onClick={() => {
                setPage(item.id);
                setNavOpen(false);
              }}
            >
              <item.icon size={18} />
              {item.label}
              {page === item.id && <span className="nav-active-mark" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <div>
              <ShieldCheck size={17} />
              <strong>Local by design</strong>
            </div>
            <p>
              Your graph. Your machine.
              <br />
              No cloud AI required.
            </p>
            <span>
              OPEN SOURCE <ArrowUpRight size={13} />
            </span>
          </div>
          <button className="help-link" onClick={() => setPage("about")}>
            <CircleHelp size={17} /> How it works
            <ArrowUpRight size={15} />
          </button>
          <div className="profile">
            <span className="avatar">SG</span>
            <div>
              <strong>SupplyGraph demo</strong>
              <small>Synthetic electronics network</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button menu-toggle"
              aria-label="Toggle navigation"
              onClick={() => setNavOpen(!navOpen)}
            >
              <Menu size={19} />
            </button>
            <span>Workspace</span>
            <span className="slash">/</span>
            <strong>{navigation.find((n) => n.id === page)?.label}</strong>
          </div>
          <div className="topbar-right">
            <span className="connection">
              <span /> {config ? "Local engine ready" : "Connecting"}
            </span>
            <span className="topbar-divider" />
            <a
              href="/docs"
              target="_blank"
              rel="noreferrer"
              className="api-link"
            >
              API docs <ArrowUpRight size={13} />
            </a>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          <div className="snapshot-bar">
            <span>
              <span className="tiny-square" /> SYNTHETIC NETWORK{" "}
              <span className="snapshot-dot">/</span> SEED{" "}
              {snapshots.find((s) => s.id === snapshot)?.seed ?? "—"}
            </span>
            <label>
              <Layers3 size={14} />
              <select
                aria-label="Active snapshot"
                value={snapshot}
                onChange={(e) => changeSnapshot(e.target.value)}
              >
                {snapshots.map((s) => (
                  <option key={s.id} value={s.id}>
                    {new Date(s.effective_at).toLocaleDateString("en-US", {
                      timeZone: "UTC",
                      month: "short",
                      day: "2-digit",
                      year: "numeric",
                    })}{" "}
                    snapshot
                  </option>
                ))}
              </select>
            </label>
          </div>
          {error && (
            <div className="error global-error" role="alert">
              <strong>Unable to load this view.</strong> {error}
              <button
                className="text-link"
                onClick={() => setReload((r) => r + 1)}
              >
                Retry
              </button>
            </div>
          )}
          {page === "data" ? (
            <DataPage
              snapshots={snapshots}
              current={snapshot}
              config={config}
              onChange={changeSnapshot}
              onImported={() => setReload((r) => r + 1)}
            />
          ) : page === "evidence" ? (
            <Explorer
              key={snapshot}
              snapshot={snapshot}
              onEvidence={setEvidence}
            />
          ) : page === "about" ? (
            <About />
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <div className="heading-kicker">
                    <span className="eyebrow">
                      {page === "scenarios"
                        ? "DISRUPTION INTELLIGENCE"
                        : "CONNECTED. TRACEABLE. RESILIENT."}
                    </span>
                    <span className="pill small-pill">v0.1</span>
                  </div>
                  <h1>
                    {page === "scenarios"
                      ? "One disruption. The whole picture."
                      : "Your network, beyond tier one."}
                  </h1>
                  <p className="muted">
                    Trace dependencies. Model disruption. Act with evidence.
                  </p>
                </div>
                <button
                  className="secondary"
                  onClick={() =>
                    scenario && download("supplygraph-scenario.json", scenario)
                  }
                  disabled={!scenario || busy}
                >
                  <Download size={16} /> Export analysis
                </button>
              </div>
              <div className={`stats-grid ${busy ? "pending" : ""}`}>
                <div className="stat-card">
                  <span className="stat-label">
                    Suppliers in snapshot <GitBranch size={16} />
                  </span>
                  <strong>
                    {overview ? number(overview.counts.supplier) : "—"}
                    <small>
                      across {overview?.supplier_tiers ?? "—"} tiers
                    </small>
                  </strong>
                  <span className="stat-detail">
                    <span className="green-text">
                      {overview?.countries || "—"} countries
                    </span>{" "}
                    · synthetic locations
                  </span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">
                    Component dependencies <Box size={16} />
                  </span>
                  <strong>
                    {overview ? number(overview.counts.component) : "—"}
                    <small>components</small>
                  </strong>
                  <span className="stat-detail">
                    {overview ? number(overview.edges) : "—"} traceable
                    relationships
                  </span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">
                    Products exposed <Activity size={16} />
                  </span>
                  <strong>
                    {validResult ? scenario.affected_products : "—"}
                    <small>of {overview?.counts.product || "—"} products</small>
                  </strong>
                  <span className="stat-detail">
                    <span className="orange-text">Current scenario</span> ·{" "}
                    {scenario?.duration_days || 14}-day outage
                  </span>
                </div>
                <div className="stat-card accent-stat">
                  <span className="stat-label">
                    Modeled value at risk <ArrowDownRight size={16} />
                  </span>
                  <strong>
                    {validResult ? money(scenario.product_exposure_value) : "—"}
                  </strong>
                  <span className="stat-detail">
                    {validResult ? number(scenario.lost_product_units) : "—"}{" "}
                    product units · computed
                  </span>
                </div>
              </div>
              <div className={`analysis-grid ${expanded ? "expanded" : ""}`}>
                <section className="panel network-panel">
                  <div className="graph-heading">
                    <div>
                      <h3>
                        Dependency landscape <span className="pill">3D</span>
                      </h3>
                      <p>
                        {graph
                          ? `${number(graph.nodes.length)} visible / ${number(graph.total_nodes)} total nodes`
                          : "Loading network…"}{" "}
                        <span>· analytics use the full graph</span>
                      </p>
                    </div>
                    <div className="graph-buttons">
                      <div className="segmented">
                        <button
                          aria-label="Dependency map"
                          aria-pressed={mode === "graph"}
                          className={mode === "graph" ? "active" : ""}
                          onClick={() => setMode("graph")}
                        >
                          <Network size={15} />
                        </button>
                        <button
                          aria-label="Global network"
                          aria-pressed={mode === "globe"}
                          className={mode === "globe" ? "active" : ""}
                          onClick={() => setMode("globe")}
                        >
                          <Globe2 size={15} />
                        </button>
                      </div>
                      <button
                        className="icon-button"
                        aria-label={
                          expanded ? "Collapse graph" : "Expand graph"
                        }
                        onClick={() => setExpanded(!expanded)}
                      >
                        {expanded ? <X size={16} /> : <Expand size={16} />}
                      </button>
                    </div>
                  </div>
                  <div className="graph-stage">
                    <div className="graph-caption">
                      <span className="eyebrow">
                        {mode === "graph"
                          ? "SUPPLY DEPENDENCY MAP"
                          : "GEOGRAPHIC NETWORK"}
                      </span>
                      <div>
                        <span className="scenario-dot" />
                        {selectedNode?.name || request.focus}
                      </div>
                    </div>
                    {graph && (
                      <Suspense
                        fallback={
                          <div className="loading-state">
                            Preparing 3D renderer…
                          </div>
                        }
                      >
                        <NetworkCanvas
                          data={graph}
                          impacted={impacted}
                          focus={request.focus}
                          mode={mode}
                          onSelect={setEvidence}
                        />
                      </Suspense>
                    )}
                    {busy && (
                      <div className="graph-loading" role="status">
                        <span className="spinner" /> Computing graph…
                      </div>
                    )}
                    <div className="graph-bottom">
                      <div className="legend">
                        <span>
                          <i className="dot lime" />
                          Selected node
                        </span>
                        <span>
                          <i className="dot amber" />
                          Affected
                        </span>
                        <span>
                          <i className="dot slate" />
                          Connected
                        </span>
                      </div>
                      <span>Drag to orbit · scroll to zoom</span>
                    </div>
                  </div>
                  <div className="graph-footer">
                    <span>
                      <ShieldCheck size={14} /> Source-backed relationships
                    </span>
                    <button
                      className="text-link"
                      onClick={() => setPage("evidence")}
                    >
                      Explore evidence <ArrowRight size={14} />
                    </button>
                  </div>
                </section>
                <aside className="panel scenario-panel">
                  <div className="section-heading">
                    <h3>
                      <Zap size={17} /> Scenario builder
                    </h3>
                    <span className="subtle-badge">WHAT IF</span>
                  </div>
                  <p className="muted">Test a disruption before it happens.</p>
                  <form onSubmit={run}>
                    <label className="field-label" htmlFor="disrupted-node">
                      Disrupted node
                    </label>
                    <div className="source-input">
                      <Globe2 size={17} />
                      <input
                        id="disrupted-node"
                        list="source-options"
                        value={draftFocus}
                        onChange={(e) => setDraftFocus(e.target.value)}
                        required
                        maxLength={96}
                      />
                    </div>
                    <datalist id="source-options">
                      {sourceOptions?.items.map((n) => (
                        <option key={n.id} value={n.id}>
                          {n.name}
                        </option>
                      ))}
                    </datalist>
                    <p className="field-hint">
                      Search a name or enter an evidence ID.
                    </p>
                    <div className="duration-heading">
                      <label htmlFor="duration">Disruption duration</label>
                      <strong>
                        {duration}
                        <span> days</span>
                      </strong>
                    </div>
                    <input
                      id="duration"
                      type="range"
                      min="1"
                      max="60"
                      value={duration}
                      onChange={(e) => setDuration(Number(e.target.value))}
                    />
                    <div className="range-labels">
                      <span>1 day</span>
                      <span>30 days</span>
                      <span>60 days</span>
                    </div>
                    <div className="scenario-assumption">
                      <Settings2 size={15} />
                      <div>
                        Complete outage
                        <small>Inventory & approved alternates included</small>
                      </div>
                    </div>
                    <button
                      className="primary run-button"
                      disabled={busy || !snapshot}
                    >
                      <Play size={15} fill="currentColor" />
                      {busy ? "Computing…" : "Run disruption analysis"}
                      <ArrowRight size={16} />
                    </button>
                  </form>
                  <div className="scenario-summary">
                    <div>
                      <span className="eyebrow">
                        {scenario ? "SCENARIO RESULT" : "READY TO ANALYZE"}
                      </span>
                      <span className="pill orange">COMPUTED</span>
                    </div>
                    <p>
                      <strong>{scenario?.affected_count ?? "—"}</strong>{" "}
                      affected nodes{" "}
                      <span>
                        / {scenario?.candidate_count ?? "—"} downstream
                        candidates
                      </span>
                    </p>
                    <div className="exposure-bar">
                      <span
                        style={{
                          width: `${scenario ? Math.max(1, (scenario.affected_count / scenario.candidate_count) * 100) : 0}%`,
                        }}
                      />
                    </div>
                    <div className="alternate-note">
                      <ShieldCheck size={16} />
                      <span>
                        <strong>
                          {scenario?.alternates.length ?? "—"} dependency groups
                        </strong>{" "}
                        protected by qualified alternates
                      </span>
                    </div>
                  </div>
                </aside>
              </div>
              {page === "scenarios" && scenario && (
                <section className="panel assumptions-panel">
                  <h3>Model assumptions</h3>
                  <ul>
                    {scenario.assumptions.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                  {scenario.alternates.length > 0 && (
                    <details>
                      <summary>
                        Inspect protected dependency groups (
                        {scenario.alternates.length})
                      </summary>
                      <div className="alternate-list">
                        {scenario.alternates.map((a) => (
                          <div key={a.target_id + a.group}>
                            <button
                              className="text-link"
                              onClick={() => setEvidence(a.source_id)}
                            >
                              {a.source_id}
                            </button>
                            <ArrowRight size={14} />
                            <button
                              className="text-link"
                              onClick={() => setEvidence(a.target_id)}
                            >
                              {a.target_id}
                            </button>
                            <span>{a.group}</span>
                            <button
                              className="text-link"
                              onClick={() => setEvidence(a.evidence_ids[2])}
                            >
                              Approval & capacity evidence
                            </button>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </section>
              )}
              <div className="lower-grid">
                <section className="panel critical-panel">
                  <div className="section-heading">
                    <h3>Critical dependencies</h3>
                    <span className="subtle-badge">TOPOLOGY</span>
                  </div>
                  {overview?.critical.slice(0, 4).map((r, i) => (
                    <button
                      className="critical-row"
                      key={r.node_id}
                      onClick={() => setEvidence(r.node_id)}
                    >
                      <span className="rank">0{i + 1}</span>
                      <span>
                        <strong>{r.name}</strong>
                        <small>
                          {r.node_id} · {r.out_degree} direct dependents
                        </small>
                      </span>
                      <div className="critical-meter">
                        <span
                          style={{
                            width: `${Math.max(5, (r.betweenness / (overview.critical[0].betweenness || 1)) * 100)}%`,
                          }}
                        />
                      </div>
                      <ArrowUpRight size={14} />
                    </button>
                  ))}
                  <p className="tiny-note">
                    Ranked by sampled betweenness · seed 42 · 32 pivots
                  </p>
                </section>
                <QueryPanel
                  key={snapshot}
                  snapshot={snapshot}
                  config={config}
                  onEvidence={setEvidence}
                />
              </div>
              {scenario && (
                <ImpactTable
                  impacts={scenario.impacts}
                  onEvidence={setEvidence}
                />
              )}
            </>
          )}
          <footer className="main-footer">
            <span>
              <Waypoints size={13} /> SupplyGraph AI <span>·</span> Evidence
              over assumptions.
            </span>
            <span>Synthetic data · Local computation · Open source</span>
          </footer>
        </main>
      </div>
      {evidence && (
        <EvidenceDrawer
          key={evidence + snapshot}
          id={evidence}
          snapshot={snapshot}
          onClose={() => setEvidence(null)}
          onFocus={focusNode}
        />
      )}
    </div>
  );
}
