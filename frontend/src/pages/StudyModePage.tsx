import { FormEvent, useEffect, useMemo, useState } from "react";
import { BookOpen, History, Loader2, MessageSquareText, RefreshCw, Search, Trash2 } from "lucide-react";
import { askQuestion, deleteStudySession, listDocuments, listStudySessions, studyMode } from "../api";
import { MermaidBlock } from "../components/MermaidBlock";
import { SourceList } from "../components/SourceList";
import { AskQuestionResponse, DocumentOut, StudyModeResponse, StudySessionOut } from "../types";

type StudyTab = "study" | "ask";

export function StudyModePage() {
  const [tab, setTab] = useState<StudyTab>("study");
  const [topic, setTopic] = useState("");
  const [question, setQuestion] = useState("");
  const [includeDiagram, setIncludeDiagram] = useState(true);
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [study, setStudy] = useState<StudyModeResponse | null>(null);
  const [studySessions, setStudySessions] = useState<StudySessionOut[]>([]);
  const [answer, setAnswer] = useState<AskQuestionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const readyDocuments = useMemo(() => documents.filter((document) => document.status === "ready"), [documents]);

  async function loadDocuments() {
    setLoadingDocuments(true);
    setError("");
    try {
      setDocuments(await listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load documents.");
    } finally {
      setLoadingDocuments(false);
    }
  }

  async function loadStudySessions() {
    try {
      setStudySessions(await listStudySessions());
    } catch {
      setStudySessions([]);
    }
  }

  useEffect(() => {
    loadDocuments();
    loadStudySessions();
  }, []);

  function toggleDocument(documentId: string) {
    setSelectedDocumentIds((current) =>
      current.includes(documentId) ? current.filter((id) => id !== documentId) : [...current, documentId]
    );
  }

  async function handleStudy(event: FormEvent) {
    event.preventDefault();
    if (!topic.trim()) {
      return;
    }
    setLoading(true);
    setError("");
    setStudy(null);
    try {
      const response = await studyMode(topic.trim(), includeDiagram, selectedDocumentIds);
      setStudy(response);
      await loadStudySessions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create study notes.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) {
      return;
    }
    setLoading(true);
    setError("");
    setAnswer(null);
    try {
      setAnswer(await askQuestion(question.trim(), selectedDocumentIds));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not answer the question.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteSession(sessionId: string) {
    try {
      await deleteStudySession(sessionId);
      setStudySessions((current) => current.filter((session) => session.id !== sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete study session.");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[0.82fr_1.18fr]">
      <section className="card h-fit p-5">
        <div className="mb-5 flex items-center gap-3">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-teal/10 text-teal">
            <BookOpen size={22} aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-xl font-bold text-ink">Study Mode</h2>
            <p className="text-sm text-slate-500">Simple notes from uploaded PDF context.</p>
          </div>
        </div>

        <div className="segmented mb-5 grid-cols-2">
          <button type="button" className={`segment ${tab === "study" ? "segment-active" : ""}`} onClick={() => setTab("study")}>
            Study
          </button>
          <button type="button" className={`segment ${tab === "ask" ? "segment-active" : ""}`} onClick={() => setTab("ask")}>
            Ask
          </button>
        </div>

        <div className="mb-5">
          <div className="mb-2 flex items-center justify-between gap-3">
            <label className="label block">PDFs</label>
            <button type="button" className="btn-icon" title="Refresh documents" onClick={loadDocuments} disabled={loadingDocuments}>
              {loadingDocuments ? <Loader2 size={16} className="animate-spin" aria-hidden="true" /> : <RefreshCw size={16} aria-hidden="true" />}
            </button>
          </div>
          <div className="rounded-lg border border-line bg-slate-50 p-3">
            {loadingDocuments ? (
              <p className="flex items-center gap-2 text-sm font-medium text-slate-500">
                <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                Loading PDFs
              </p>
            ) : readyDocuments.length ? (
              <div className="space-y-2">
                <label className="flex cursor-pointer items-center gap-3 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={selectedDocumentIds.length === 0}
                    onChange={() => setSelectedDocumentIds([])}
                    className="h-4 w-4 accent-teal"
                  />
                  All ready PDFs
                </label>
                {readyDocuments.map((document) => (
                  <label
                    key={document.id}
                    className="flex cursor-pointer items-start gap-3 rounded-lg bg-white px-3 py-2 text-sm text-slate-700"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDocumentIds.includes(document.id)}
                      onChange={() => toggleDocument(document.id)}
                      className="mt-1 h-4 w-4 accent-teal"
                    />
                    <span className="min-w-0">
                      <span className="block truncate font-semibold text-ink">{document.file_name}</span>
                      <span className="text-xs text-slate-500">
                        {document.page_count} pages - {document.chunk_count} chunks
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            ) : (
              <p className="text-sm font-medium text-slate-500">Upload and ingest a PDF first.</p>
            )}
          </div>
        </div>

        {tab === "study" ? (
          <form onSubmit={handleStudy} className="space-y-4">
            <div>
              <label htmlFor="studyTopic" className="label mb-2 block">
                Topic
              </label>
              <input
                id="studyTopic"
                className="input"
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                placeholder="Concept or chapter"
              />
            </div>
            <label className="flex items-center gap-3 rounded-lg border border-line bg-white p-3 text-sm font-semibold text-slate-700">
              <input
                type="checkbox"
                checked={includeDiagram}
                onChange={(event) => setIncludeDiagram(event.target.checked)}
                className="h-4 w-4 accent-teal"
              />
              Mermaid diagram
            </label>
            <button className="btn-primary w-full" disabled={loading || !topic.trim()}>
              {loading ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <BookOpen size={17} aria-hidden="true" />}
              Study
            </button>
          </form>
        ) : (
          <form onSubmit={handleAsk} className="space-y-4">
            <div>
              <label htmlFor="studyQuestion" className="label mb-2 block">
                Question
              </label>
              <textarea
                id="studyQuestion"
                className="input min-h-28 resize-y leading-6"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask from your PDF"
              />
            </div>
            <button className="btn-primary w-full" disabled={loading || !question.trim()}>
              {loading ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <Search size={17} aria-hidden="true" />}
              Ask
            </button>
          </form>
        )}

        {error ? <p className="mt-4 text-sm font-medium text-red-600">{error}</p> : null}

        {studySessions.length ? (
          <div className="mt-5 border-t border-line pt-5">
            <div className="mb-3 flex items-center gap-2">
              <History size={17} className="text-slate-500" aria-hidden="true" />
              <h3 className="text-sm font-bold text-ink">Saved Sessions</h3>
            </div>
            <div className="grid gap-2">
              {studySessions.slice(0, 5).map((session) => (
                <div key={session.id} className="flex items-center gap-2 rounded-lg border border-line bg-white px-3 py-2">
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    onClick={() => {
                      setStudy(session.response);
                      setAnswer(null);
                    }}
                  >
                    <span className="block truncate text-sm font-bold text-ink">{session.topic}</span>
                    <span className="block text-xs text-slate-500">{new Date(session.created_at).toLocaleString()}</span>
                  </button>
                  <button type="button" className="btn-icon h-9 w-9" title="Delete session" onClick={() => handleDeleteSession(session.id)}>
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      <section className="space-y-5">
        {study ? (
          <>
            <div className="card p-5">
              <h3 className="text-lg font-bold text-ink">{study.topic}</h3>
              <p className="mt-3 leading-7 text-slate-700">{study.simple_explanation}</p>
              <div className="mt-4">
                <SourceList sources={study.sources} />
              </div>
            </div>

            {study.key_points.length ? (
              <div className="card p-5">
                <h3 className="text-lg font-bold text-ink">Key Points</h3>
                <ul className="mt-3 space-y-2">
                  {study.key_points.map((point) => (
                    <li key={point} className="rounded-lg bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-700">
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {study.example ? (
              <div className="card p-5">
                <h3 className="text-lg font-bold text-ink">Example</h3>
                <p className="mt-3 leading-7 text-slate-700">{study.example}</p>
              </div>
            ) : null}

            {study.important_terms.length ? (
              <div className="card p-5">
                <h3 className="text-lg font-bold text-ink">Important Terms</h3>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {study.important_terms.map((term) => (
                    <div key={term.term} className="rounded-lg bg-slate-50 p-3">
                      <p className="font-bold text-ink">{term.term}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{term.meaning}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="card p-5">
              <h3 className="text-lg font-bold text-ink">Quick Revision</h3>
              <p className="mt-3 leading-7 text-slate-700">{study.quick_revision_summary}</p>
            </div>

            <MermaidBlock chart={study.mermaid_diagram} />
          </>
        ) : null}

        {answer ? (
          <div className="card p-5">
            <div className="mb-3 flex items-center gap-2">
              <MessageSquareText size={19} className="text-indigo" aria-hidden="true" />
              <h3 className="text-lg font-bold text-ink">Answer</h3>
            </div>
            <p className="leading-7 text-slate-700">{answer.answer}</p>
            <div className="mt-4">
              <SourceList sources={answer.sources} />
            </div>
          </div>
        ) : null}

        {!study && !answer ? (
          <div className="card p-6 text-center text-sm text-slate-500">
            <BookOpen className="mx-auto mb-3 text-slate-400" size={34} aria-hidden="true" />
            Choose a topic or question.
          </div>
        ) : null}
      </section>
    </div>
  );
}
