import { FormEvent, useEffect, useMemo, useState } from "react";
import { FileQuestion, History, Loader2, Play, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { generateTest, getTest, listDocuments, listTests } from "../api";
import { Difficulty, DocumentOut, GenerateTestResponse, TestHistoryItem, TestMode } from "../types";

interface GenerateTestPageProps {
  onGenerated: (test: GenerateTestResponse) => void;
}

const modes: TestMode[] = ["mcq", "written", "mixed"];
const difficulties: Difficulty[] = ["Easy", "Medium", "Hard"];

export function GenerateTestPage({ onGenerated }: GenerateTestPageProps) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<TestMode>("mcq");
  const [difficulty, setDifficulty] = useState<Difficulty>("Medium");
  const [numQuestions, setNumQuestions] = useState(5);
  const [topic, setTopic] = useState("");
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [savedTests, setSavedTests] = useState<TestHistoryItem[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [loadingTests, setLoadingTests] = useState(true);
  const [busyTestId, setBusyTestId] = useState("");
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

  async function loadTests() {
    setLoadingTests(true);
    try {
      setSavedTests(await listTests());
    } catch {
      setSavedTests([]);
    } finally {
      setLoadingTests(false);
    }
  }

  useEffect(() => {
    loadDocuments();
    loadTests();
  }, []);

  function toggleDocument(documentId: string) {
    setSelectedDocumentIds((current) =>
      current.includes(documentId) ? current.filter((id) => id !== documentId) : [...current, documentId]
    );
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const test = await generateTest({
        mode,
        difficulty,
        num_questions: numQuestions,
        topic: topic.trim() || null,
        document_ids: selectedDocumentIds
      });
      await loadTests();
      onGenerated(test);
      navigate("/take-test");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate the test.");
    } finally {
      setLoading(false);
    }
  }

  async function handleOpenSavedTest(testId: string) {
    setBusyTestId(testId);
    setError("");
    try {
      const test = await getTest(testId);
      onGenerated(test);
      navigate("/take-test");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open saved test.");
    } finally {
      setBusyTestId("");
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1fr_320px]">
      <form onSubmit={handleSubmit} className="card p-5">
        <div className="mb-5 flex items-center gap-3">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-indigo/10 text-indigo">
            <FileQuestion size={22} aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-xl font-bold text-ink">Generate Test</h2>
            <p className="text-sm text-slate-500">Questions are generated from retrieved PDF chunks.</p>
          </div>
        </div>

          <div className="grid gap-5">
          <div>
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

          <div>
            <label className="label mb-2 block">Mode</label>
            <div className="segmented grid-cols-3">
              {modes.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`segment capitalize ${mode === item ? "segment-active" : ""}`}
                  onClick={() => setMode(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label mb-2 block">Difficulty</label>
            <div className="segmented grid-cols-3">
              {difficulties.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`segment ${difficulty === item ? "segment-active" : ""}`}
                  onClick={() => setDifficulty(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-[180px_1fr]">
            <div>
              <label htmlFor="numQuestions" className="label mb-2 block">
                Questions
              </label>
              <input
                id="numQuestions"
                className="input"
                type="number"
                min={1}
                max={25}
                value={numQuestions}
                onChange={(event) => setNumQuestions(Number(event.target.value))}
              />
            </div>
            <div>
              <label htmlFor="topic" className="label mb-2 block">
                Topic
              </label>
              <input
                id="topic"
                className="input"
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                placeholder="Optional chapter or concept"
              />
            </div>
          </div>
        </div>

        {error ? <p className="mt-4 text-sm font-medium text-red-600">{error}</p> : null}

        <button className="btn-primary mt-6 w-full" disabled={loading}>
          {loading ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <FileQuestion size={17} aria-hidden="true" />}
          Generate
        </button>
      </form>

      <aside className="card h-fit p-5">
        <div className="mb-4 flex items-center gap-2">
          <History size={18} className="text-slate-500" aria-hidden="true" />
          <h3 className="text-lg font-bold text-ink">Saved Tests</h3>
        </div>
        {loadingTests ? (
          <p className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 size={16} className="animate-spin" aria-hidden="true" />
            Loading
          </p>
        ) : savedTests.length ? (
          <div className="grid gap-2">
            {savedTests.slice(0, 8).map((test) => (
              <button
                key={test.test_id}
                type="button"
                className="rounded-lg border border-line bg-white px-3 py-2 text-left transition hover:bg-slate-50"
                onClick={() => handleOpenSavedTest(test.test_id)}
                disabled={Boolean(busyTestId)}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="min-w-0 truncate text-sm font-bold capitalize text-ink">
                    {test.mode} - {test.difficulty}
                  </span>
                  {busyTestId === test.test_id ? (
                    <Loader2 size={15} className="shrink-0 animate-spin text-slate-400" aria-hidden="true" />
                  ) : (
                    <Play size={15} className="shrink-0 text-slate-400" aria-hidden="true" />
                  )}
                </span>
                <span className="mt-1 block text-xs text-slate-500">
                  {test.question_count} questions - {new Date(test.created_at).toLocaleDateString()}
                </span>
                {test.topic ? <span className="mt-1 block truncate text-xs text-slate-500">{test.topic}</span> : null}
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Generated tests appear here.</p>
        )}
      </aside>
    </div>
  );
}
