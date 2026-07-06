import { useEffect, useState } from "react";
import { CheckCircle2, CircleX, FileQuestion, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";
import { listTestResults } from "../api";
import { SourceList } from "../components/SourceList";
import { CombinedResults, SavedTestResult } from "../types";

interface ResultsPageProps {
  results: CombinedResults | null;
}

function savedToCombined(saved: SavedTestResult): CombinedResults {
  return {
    resultId: saved.result_id,
    test: saved.test,
    mcq: saved.mcq,
    written: saved.written,
    submittedAt: saved.submitted_at,
    percentage: saved.percentage
  };
}

export function ResultsPage({ results }: ResultsPageProps) {
  const [history, setHistory] = useState<CombinedResults[]>([]);
  const [selected, setSelected] = useState<CombinedResults | null>(results);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    if (results) {
      setSelected(results);
    }
  }, [results]);

  useEffect(() => {
    let active = true;

    async function loadHistory() {
      setLoadingHistory(true);
      setHistoryError("");
      try {
        const saved = (await listTestResults()).map(savedToCombined);
        if (!active) {
          return;
        }
        setHistory(saved);
        if (!results && saved.length) {
          setSelected(saved[0]);
        }
      } catch (err) {
        if (active) {
          setHistoryError(err instanceof Error ? err.message : "Could not load result history.");
        }
      } finally {
        if (active) {
          setLoadingHistory(false);
        }
      }
    }

    loadHistory();
    return () => {
      active = false;
    };
  }, [results]);

  if (!selected && loadingHistory) {
    return (
      <section className="card mx-auto max-w-xl p-6 text-center">
        <Loader2 className="mx-auto animate-spin text-slate-400" size={34} aria-hidden="true" />
        <h2 className="mt-3 text-xl font-bold text-ink">Loading Results</h2>
      </section>
    );
  }

  if (!selected) {
    return (
      <section className="card mx-auto max-w-xl p-6 text-center">
        <FileQuestion className="mx-auto text-slate-400" size={34} aria-hidden="true" />
        <h2 className="mt-3 text-xl font-bold text-ink">No Results</h2>
        {historyError ? <p className="mt-2 text-sm font-medium text-red-600">{historyError}</p> : null}
        <Link to="/generate-test" className="btn-primary mt-5">
          Generate Test
        </Link>
      </section>
    );
  }

  return (
    <div className="space-y-5">
      <section className="card p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-bold text-ink">Results</h2>
            <p className="text-sm text-slate-500">{new Date(selected.submittedAt).toLocaleString()}</p>
          </div>
          <Link to="/generate-test" className="btn-secondary">
            New Test
          </Link>
        </div>
      </section>

      {history.length ? (
        <section className="card p-5">
          <h3 className="text-lg font-bold text-ink">Saved Attempts</h3>
          <div className="mt-3 grid gap-2">
            {history.map((item) => (
              <button
                key={item.resultId || item.submittedAt}
                type="button"
                className={`rounded-lg border px-3 py-2 text-left transition ${
                  selected.resultId === item.resultId ? "border-teal bg-teal/5" : "border-line bg-white hover:bg-slate-50"
                }`}
                onClick={() => setSelected(item)}
              >
                <span className="block text-sm font-bold capitalize text-ink">
                  {item.test.mode} - {item.test.difficulty} - {item.test.questions.length} questions
                </span>
                <span className="block text-xs text-slate-500">
                  {new Date(item.submittedAt).toLocaleString()} - {item.percentage ?? 0}%
                </span>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {selected.mcq ? (
        <section className="space-y-3">
          <div className="card p-5">
            <h3 className="text-lg font-bold text-ink">MCQ Score</h3>
            <p className="mt-2 text-3xl font-bold text-teal">
              {selected.mcq.score}/{selected.mcq.total}
              <span className="ml-2 text-base text-slate-500">({selected.mcq.percentage}%)</span>
            </p>
          </div>
          {selected.mcq.results.map((item) => (
            <div key={item.question_id} className="card p-4">
              <div className="flex items-start gap-3">
                {item.is_correct ? (
                  <CheckCircle2 className="mt-1 shrink-0 text-emerald-600" size={18} aria-hidden="true" />
                ) : (
                  <CircleX className="mt-1 shrink-0 text-red-600" size={18} aria-hidden="true" />
                )}
                <div className="min-w-0">
                  <p className="font-semibold leading-6 text-ink">{item.question}</p>
                  <p className="mt-2 text-sm text-slate-600">Your answer: {item.selected_answer || "Not answered"}</p>
                  <p className="text-sm text-slate-600">Correct answer: {item.correct_answer}</p>
                  {item.explanation ? <p className="mt-2 text-sm leading-6 text-slate-500">{item.explanation}</p> : null}
                </div>
              </div>
            </div>
          ))}
        </section>
      ) : null}

      {selected.written ? (
        <section className="space-y-3">
          <div className="card p-5">
            <h3 className="text-lg font-bold text-ink">Written Score</h3>
            <p className="mt-2 text-3xl font-bold text-indigo">
              {selected.written.score}/{selected.written.max_score}
              <span className="ml-2 text-base text-slate-500">({selected.written.percentage}%)</span>
            </p>
          </div>
          {selected.written.results.map((item) => (
            <div key={item.question_id} className="card p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <p className="font-semibold leading-6 text-ink">{item.question}</p>
                <span className="w-fit rounded-md bg-indigo/10 px-2 py-1 text-xs font-bold text-indigo">
                  {item.score}/{item.max_score}
                </span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600">{item.feedback}</p>
              <div className="mt-3 rounded-lg bg-slate-50 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Model Answer</p>
                <p className="mt-1 text-sm leading-6 text-slate-700">{item.model_answer}</p>
              </div>
              <div className="mt-3">
                <SourceList sources={item.sources} />
              </div>
            </div>
          ))}
        </section>
      ) : null}
    </div>
  );
}
