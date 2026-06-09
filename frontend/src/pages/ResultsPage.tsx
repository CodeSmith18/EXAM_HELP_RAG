import { CheckCircle2, CircleX, FileQuestion } from "lucide-react";
import { Link } from "react-router-dom";
import { SourceList } from "../components/SourceList";
import { CombinedResults } from "../types";

interface ResultsPageProps {
  results: CombinedResults | null;
}

export function ResultsPage({ results }: ResultsPageProps) {
  if (!results) {
    return (
      <section className="card mx-auto max-w-xl p-6 text-center">
        <FileQuestion className="mx-auto text-slate-400" size={34} aria-hidden="true" />
        <h2 className="mt-3 text-xl font-bold text-ink">No Results</h2>
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
            <p className="text-sm text-slate-500">{new Date(results.submittedAt).toLocaleString()}</p>
          </div>
          <Link to="/generate-test" className="btn-secondary">
            New Test
          </Link>
        </div>
      </section>

      {results.mcq ? (
        <section className="space-y-3">
          <div className="card p-5">
            <h3 className="text-lg font-bold text-ink">MCQ Score</h3>
            <p className="mt-2 text-3xl font-bold text-teal">
              {results.mcq.score}/{results.mcq.total}
              <span className="ml-2 text-base text-slate-500">({results.mcq.percentage}%)</span>
            </p>
          </div>
          {results.mcq.results.map((item) => (
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

      {results.written ? (
        <section className="space-y-3">
          <div className="card p-5">
            <h3 className="text-lg font-bold text-ink">Written Score</h3>
            <p className="mt-2 text-3xl font-bold text-indigo">
              {results.written.score}/{results.written.max_score}
              <span className="ml-2 text-base text-slate-500">({results.written.percentage}%)</span>
            </p>
          </div>
          {results.written.results.map((item) => (
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
