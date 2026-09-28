import { useEffect, useRef, useState } from "react";
import { X, FileCheck2, ArrowUpRight } from "lucide-react";
import { api } from "./api";
export default function EvidenceDrawer({
  id,
  snapshot,
  onClose,
  onFocus,
}: {
  id: string;
  snapshot: string;
  onClose: () => void;
  onFocus: (id: string) => void;
}) {
  const [record, setRecord] = useState<Record<string, unknown> | null>(null),
    [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    let active = true;
    api<Record<string, unknown>>(
      `/evidence/${encodeURIComponent(id)}?snapshot_id=${encodeURIComponent(snapshot)}`,
    )
      .then((r) => {
        if (active) setRecord(r);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [id, snapshot]);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return (
    <dialog ref={dialog} className="evidence-drawer" onCancel={onClose}>
      <div className="drawer-heading">
        <span className="eyebrow">
          <FileCheck2 size={15} /> RAW GRAPH EVIDENCE
        </span>
        <button
          className="icon-button"
          aria-label="Close evidence"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      <h2>{id}</h2>
      <p className="muted">Immutable record · {snapshot}</p>
      {error ? (
        <div className="error">{error}</div>
      ) : record ? (
        <>
          <h3>{String(record.name || record.kind || "Inventory balance")}</h3>
          <dl className="evidence-fields">
            {Object.entries(record)
              .filter(([key]) => key !== "lineage")
              .map(([key, value]) => (
                <div key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
          </dl>
          <h4>Provenance & lineage</h4>
          <pre>{JSON.stringify(record.lineage, null, 2)}</pre>
          {"latitude" in record && (
            <button
              className="primary"
              onClick={() => {
                onFocus(id);
                onClose();
              }}
            >
              Analyze this node <ArrowUpRight size={16} />
            </button>
          )}
        </>
      ) : (
        <p role="status">Loading evidence…</p>
      )}
    </dialog>
  );
}
