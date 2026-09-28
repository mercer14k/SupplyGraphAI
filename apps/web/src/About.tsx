import {
  Network,
  Database,
  ShieldCheck,
  Cpu,
  GitBranch,
  ArrowRight,
} from "lucide-react";
export default function About() {
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">BUILT TO BE INSPECTED</span>
          <h1>Intelligence with a paper trail.</h1>
          <p className="muted">
            A multi-tier supply-chain knowledge graph with disruption
            propagation and graph-grounded reasoning.
          </p>
        </div>
      </div>
      <div className="architecture-flow">
        {[
          [Database, "Versioned data", "Atomic validation + provenance"],
          [GitBranch, "Dependency graph", "Typed AND / OR relationships"],
          [Network, "Deterministic engine", "Time to shortage + alternates"],
          [Cpu, "Local reasoning", "Schema-constrained query plans"],
        ].map(([Icon, title, detail], i) => {
          const Glyph = Icon as typeof Cpu;
          return (
            <div className="architecture-step" key={String(title)}>
              <Glyph size={25} />
              <h3>{String(title)}</h3>
              <p>{String(detail)}</p>
              {i < 3 && <ArrowRight className="flow-arrow" size={18} />}
            </div>
          );
        })}
      </div>
      <div className="two-column">
        <section className="panel prose">
          <h3>How propagation works</h3>
          <p>
            Supply dependencies point from source to consumer. Separate incoming
            groups are all required. Sources within the same group are
            interchangeable, provided they are approved and have enough
            dedicated capacity.
          </p>
          <p>
            A source outage first consumes in-transit supply, then the receiving
            node’s inventory. A node reaches shortage when its earliest required
            group runs out. A qualified surviving alternate can preserve that
            group.
          </p>
          <p>
            Product exposure is constant daily demand × days in shortage ×
            synthetic unit value. It is a planning estimate, not a revenue
            forecast.
          </p>
          <span className="subtle-badge">TIME-TO-SHORTAGE-V1</span>
        </section>
        <section className="panel prose">
          <h3>
            <ShieldCheck size={19} /> Grounded by construction
          </h3>
          <p>
            The optional local model chooses a typed read-only operation. It
            cannot run SQL, execute commands, mutate records, or write free-form
            business claims.
          </p>
          <p>
            All answers are rendered from computed results and cite immutable
            graph records. Missing paths, invalid IDs, or failed model
            validation produce an explicit abstention.
          </p>
          <p>
            The complete workflow runs without an LLM. Ollama and llama.cpp are
            optional adapters; no paid service or proprietary AI is required.
          </p>
        </section>
      </div>
      <section className="panel prose">
        <h3>Boundaries & assumptions</h3>
        <p>
          This synthetic electronics network demonstrates dependency reasoning.
          It does not represent real companies or current disruptions. Buffers
          are aggregate; shared inventory allocation, partial capacity loss,
          stochastic demand, qualification delays, transport schedules, and
          post-recovery catch-up are outside the v1 model. Cyclic dependencies
          are rejected because they need a flow model.
        </p>
        <p>
          Three.js renders a bounded neighborhood. Analytics run across the
          complete selected snapshot. Centrality uses a reproducible sample of
          up to 32 pivots, and measures graph structure rather than disruption
          probability.
        </p>
        <div className="about-stack">
          Python · FastAPI · NetworkX · PostgreSQL / SQLite · React · Three.js ·
          Ollama / llama.cpp
        </div>
      </section>
    </>
  );
}
