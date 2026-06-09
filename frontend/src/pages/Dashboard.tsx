import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { ArrowRight, BookOpen, FileQuestion, LibraryBig, Loader2, Search, UploadCloud } from "lucide-react";
import { Link } from "react-router-dom";
import { askQuestion, listDocuments } from "../api";
import { SourceList } from "../components/SourceList";
import { StatusPill } from "../components/StatusPill";
import { AskQuestionResponse, DocumentOut } from "../types";

export function Dashboard() {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskQuestionResponse | null>(null);
  const [asking, setAsking] = useState(false);
  const [docError, setDocError] = useState("");
  const [askError, setAskError] = useState("");

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch((err: Error) => setDocError(err.message))
      .finally(() => setLoadingDocs(false));
  }, []);

  const stats = useMemo(() => {
    const ready = documents.filter((doc) => doc.status === "ready").length;
    const chunks = documents.reduce((sum, doc) => sum + doc.chunk_count, 0);
    const pages = documents.reduce((sum, doc) => sum + doc.page_count, 0);
    return { ready, chunks, pages };
  }, [documents]);

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) {
      return;
    }
    setAsking(true);
    setAskError("");
    setAnswer(null);
    try {
      setAnswer(await askQuestion(question.trim()));
    } catch (err) {
      setAskError(err instanceof Error ? err.message : "Could not answer the question.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
      <section className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="card p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Ready PDFs</p>
            <p className="mt-2 text-3xl font-bold text-ink">{stats.ready}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Pages</p>
            <p className="mt-2 text-3xl font-bold text-indigo">{stats.pages}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Chunks</p>
            <p className="mt-2 text-3xl font-bold text-teal">{stats.chunks}</p>
          </div>
        </div>

        <div className="card p-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-xl font-bold text-ink">PDF Q&A</h2>
              <p className="text-sm text-slate-500">Answers stay grounded in uploaded documents.</p>
            </div>
          </div>
          <form onSubmit={handleAsk} className="flex flex-col gap-3 sm:flex-row">
            <input
              className="input"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask from your notes"
            />
            <button className="btn-primary sm:w-36" disabled={asking || !question.trim()}>
              {asking ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <Search size={17} aria-hidden="true" />}
              Ask
            </button>
          </form>
          {answer ? (
            <div className="mt-5 space-y-3 rounded-lg border border-line bg-slate-50 p-4">
              <p className="text-sm leading-6 text-slate-700">{answer.answer}</p>
              <SourceList sources={answer.sources} />
            </div>
          ) : null}
          {askError ? <p className="mt-3 text-sm font-medium text-red-600">{askError}</p> : null}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <QuickAction to="/upload" icon={<UploadCloud size={19} />} label="Upload PDFs" />
          <QuickAction to="/generate-test" icon={<FileQuestion size={19} />} label="Generate Test" />
          <QuickAction to="/study" icon={<BookOpen size={19} />} label="Study Mode" />
          <QuickAction to="/documents" icon={<LibraryBig size={19} />} label="Documents" />
        </div>
      </section>

      <aside className="card h-fit p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink">Recent PDFs</h2>
          <Link to="/documents" className="text-sm font-bold text-teal hover:text-teal/80">
            View all
          </Link>
        </div>
        {loadingDocs ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 size={16} className="animate-spin" aria-hidden="true" />
            Loading
          </div>
        ) : docError ? (
          <p className="text-sm font-medium text-red-600">{docError}</p>
        ) : documents.length ? (
          <div className="space-y-3">
            {documents.slice(0, 5).map((doc) => (
              <div key={doc.id} className="border-t border-line py-3 first:border-t-0">
                <div className="flex items-start justify-between gap-3">
                  <p className="min-w-0 truncate text-sm font-bold text-ink">{doc.file_name}</p>
                  <StatusPill status={doc.status} />
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {doc.page_count} pages - {doc.chunk_count} chunks
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No PDFs uploaded yet.</p>
        )}
      </aside>
    </div>
  );
}

function QuickAction({ to, icon, label }: { to: string; icon: ReactNode; label: string }) {
  return (
    <Link to={to} className="card group flex items-center justify-between p-4 transition hover:border-slate-400">
      <span className="inline-flex items-center gap-3 text-sm font-bold text-ink">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-teal">{icon}</span>
        {label}
      </span>
      <ArrowRight size={18} className="text-slate-400 transition group-hover:translate-x-1 group-hover:text-teal" aria-hidden="true" />
    </Link>
  );
}
