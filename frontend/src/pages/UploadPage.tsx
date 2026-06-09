import { ChangeEvent, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, UploadCloud } from "lucide-react";
import { uploadPdfs } from "../api";
import { StatusPill } from "../components/StatusPill";
import { DocumentOut } from "../types";

export function UploadPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState<DocumentOut[]>([]);
  const [error, setError] = useState("");

  function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files || []));
    setUploaded([]);
    setError("");
    setProgress(0);
  }

  async function handleUpload() {
    if (!files.length) {
      return;
    }
    setUploading(true);
    setError("");
    setUploaded([]);
    try {
      const docs = await uploadPdfs(files, setProgress);
      setUploaded(docs);
      setProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
      <section className="card p-5">
        <h2 className="text-xl font-bold text-ink">Upload PDF</h2>
        <div className="mt-5 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5">
          <label className="flex cursor-pointer flex-col items-center justify-center gap-3 text-center">
            <span className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-white text-teal shadow-sm">
              <UploadCloud size={24} aria-hidden="true" />
            </span>
            <span className="text-sm font-bold text-ink">Select PDF files</span>
            <input type="file" multiple accept="application/pdf" className="sr-only" onChange={handleFiles} />
          </label>
        </div>

        {files.length ? (
          <div className="mt-4 space-y-2">
            {files.map((file) => (
              <div key={`${file.name}-${file.size}`} className="flex items-center justify-between gap-3 rounded-lg border border-line bg-white px-3 py-2">
                <span className="min-w-0 truncate text-sm font-semibold text-slate-700">{file.name}</span>
                <span className="shrink-0 text-xs font-medium text-slate-500">{Math.ceil(file.size / 1024)} KB</span>
              </div>
            ))}
          </div>
        ) : null}

        {uploading || progress > 0 ? (
          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-xs font-bold text-slate-500">
              <span>Upload</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-teal transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        ) : null}

        <button className="btn-primary mt-5 w-full" disabled={!files.length || uploading} onClick={handleUpload}>
          {uploading ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <UploadCloud size={17} aria-hidden="true" />}
          Upload and Ingest
        </button>

        {error ? (
          <p className="mt-4 flex items-center gap-2 text-sm font-medium text-red-600">
            <AlertCircle size={16} aria-hidden="true" />
            {error}
          </p>
        ) : null}
      </section>

      <section className="card p-5">
        <h2 className="text-xl font-bold text-ink">Ingestion Status</h2>
        {uploaded.length ? (
          <div className="mt-5 space-y-3">
            {uploaded.map((doc) => (
              <div key={doc.id} className="border-t border-line py-4 first:border-t-0">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate font-bold text-ink">{doc.file_name}</p>
                    <p className="mt-1 text-sm text-slate-500">
                      {doc.page_count} pages - {doc.chunk_count} chunks
                    </p>
                  </div>
                  <StatusPill status={doc.status} />
                </div>
              </div>
            ))}
            <p className="flex items-center gap-2 text-sm font-semibold text-emerald-700">
              <CheckCircle2 size={16} aria-hidden="true" />
              Vector store updated
            </p>
          </div>
        ) : (
          <p className="mt-5 text-sm text-slate-500">Uploaded PDFs appear here after ingestion.</p>
        )}
      </section>
    </div>
  );
}
