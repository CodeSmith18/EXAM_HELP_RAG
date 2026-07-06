import { useEffect, useState } from "react";
import { Loader2, RefreshCw, Trash2 } from "lucide-react";
import { deleteDocument, listDocuments, reingestDocument } from "../api";
import { StatusPill } from "../components/StatusPill";
import { DocumentOut } from "../types";

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setDocuments(await listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load documents.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleReingest(documentId: string) {
    setBusyId(documentId);
    setError("");
    try {
      const updated = await reingestDocument(documentId);
      setDocuments((current) => current.map((doc) => (doc.id === updated.id ? updated : doc)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not re-ingest document.");
    } finally {
      setBusyId("");
    }
  }

  async function handleDelete(document: DocumentOut) {
    if (!window.confirm(`Delete ${document.file_name}?`)) {
      return;
    }
    setBusyId(document.id);
    setError("");
    try {
      await deleteDocument(document.id);
      setDocuments((current) => current.filter((doc) => doc.id !== document.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete document.");
    } finally {
      setBusyId("");
    }
  }

  return (
    <section className="card p-5">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-ink">Documents</h2>
          <p className="text-sm text-slate-500">PDF metadata, chunks, and ingestion status.</p>
        </div>
        <button className="btn-secondary" onClick={load} disabled={loading}>
          {loading ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <RefreshCw size={17} aria-hidden="true" />}
          Refresh
        </button>
      </div>

      {error ? <p className="mb-4 text-sm font-medium text-red-600">{error}</p> : null}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          Loading
        </div>
      ) : documents.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line text-xs uppercase tracking-wide text-slate-500">
                <th className="py-3 pr-4 font-bold">File</th>
                <th className="py-3 pr-4 font-bold">Pages</th>
                <th className="py-3 pr-4 font-bold">Chunks</th>
                <th className="py-3 pr-4 font-bold">Uploaded</th>
                <th className="py-3 pr-4 font-bold">Status</th>
                <th className="py-3 text-right font-bold">Action</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b border-line last:border-b-0">
                  <td className="max-w-[280px] py-4 pr-4">
                    <p className="truncate font-bold text-ink">{doc.file_name}</p>
                    {doc.error ? <p className="mt-1 text-xs text-red-600">{doc.error}</p> : null}
                  </td>
                  <td className="py-4 pr-4 text-slate-700">{doc.page_count}</td>
                  <td className="py-4 pr-4 text-slate-700">{doc.chunk_count}</td>
                  <td className="py-4 pr-4 text-slate-500">{new Date(doc.uploaded_at).toLocaleString()}</td>
                  <td className="py-4 pr-4">
                    <StatusPill status={doc.status} />
                  </td>
                  <td className="py-4 text-right">
                    <div className="flex justify-end gap-2">
                      <button className="btn-secondary" onClick={() => handleReingest(doc.id)} disabled={busyId === doc.id}>
                        {busyId === doc.id ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <RefreshCw size={16} aria-hidden="true" />}
                        Re-ingest
                      </button>
                      <button className="btn-icon" title="Delete document" onClick={() => handleDelete(doc)} disabled={busyId === doc.id}>
                        <Trash2 size={16} aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-slate-500">No documents found.</p>
      )}
    </section>
  );
}
