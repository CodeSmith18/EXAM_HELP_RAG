import { FormEvent, useMemo, useState } from "react";
import { CheckCircle2, FileQuestion, Loader2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { evaluateWrittenTest, submitMcqTest } from "../api";
import { SourceList } from "../components/SourceList";
import { CombinedResults, GeneratedQuestion, GenerateTestResponse } from "../types";

interface TakeTestPageProps {
  test: GenerateTestResponse | null;
  onResults: (results: CombinedResults) => void;
}

export function TakeTestPage({ test, onResults }: TakeTestPageProps) {
  const navigate = useNavigate();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const mcqQuestions = useMemo(() => test?.questions.filter((question) => question.type === "mcq") || [], [test]);
  const writtenQuestions = useMemo(() => test?.questions.filter((question) => question.type === "written") || [], [test]);

  if (!test) {
    return (
      <section className="card mx-auto max-w-xl p-6 text-center">
        <FileQuestion className="mx-auto text-slate-400" size={34} aria-hidden="true" />
        <h2 className="mt-3 text-xl font-bold text-ink">No Active Test</h2>
        <Link to="/generate-test" className="btn-primary mt-5">
          Generate Test
        </Link>
      </section>
    );
  }

  function updateAnswer(questionId: string, value: string) {
    setAnswers((current) => ({ ...current, [questionId]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!test) {
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const [mcq, written] = await Promise.all([
        mcqQuestions.length ? submitMcqTest(mcqQuestions, answers) : Promise.resolve(null),
        writtenQuestions.length ? evaluateWrittenTest(writtenQuestions, answers) : Promise.resolve(null)
      ]);
      onResults({
        test,
        mcq,
        written,
        submittedAt: new Date().toISOString()
      });
      navigate("/results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit the test.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="card p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-bold text-ink">Take Test</h2>
            <p className="text-sm capitalize text-slate-500">
              {test.mode} - {test.difficulty} - {test.questions.length} questions
            </p>
          </div>
          <SourceList sources={test.sources.slice(0, 4)} />
        </div>
      </div>

      {test.questions.map((question, index) => (
        <QuestionBlock key={question.id} question={question} index={index} value={answers[question.id] || ""} onChange={updateAnswer} />
      ))}

      {error ? <p className="text-sm font-medium text-red-600">{error}</p> : null}

      <div className="sticky bottom-4 z-10 flex justify-end">
        <button className="btn-primary shadow-soft" disabled={submitting}>
          {submitting ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <CheckCircle2 size={17} aria-hidden="true" />}
          Submit Test
        </button>
      </div>
    </form>
  );
}

function QuestionBlock({
  question,
  index,
  value,
  onChange
}: {
  question: GeneratedQuestion;
  index: number;
  value: string;
  onChange: (questionId: string, value: string) => void;
}) {
  return (
    <section className="card p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">Question {index + 1}</span>
          <h3 className="mt-1 text-lg font-bold leading-7 text-ink">{question.question}</h3>
        </div>
        <span className="w-fit rounded-md border border-line bg-slate-50 px-2 py-1 text-xs font-bold capitalize text-slate-600">
          {question.type}
        </span>
      </div>

      {question.type === "mcq" ? (
        <div className="grid gap-3">
          {question.options.map((option) => (
            <label
              key={option}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition ${
                value === option ? "border-teal bg-teal/5" : "border-line bg-white hover:bg-slate-50"
              }`}
            >
              <input
                type="radio"
                name={question.id}
                value={option}
                checked={value === option}
                onChange={(event) => onChange(question.id, event.target.value)}
                className="mt-1 h-4 w-4 accent-teal"
              />
              <span className="text-sm font-medium leading-6 text-slate-700">{option}</span>
            </label>
          ))}
        </div>
      ) : (
        <textarea
          className="input min-h-36 resize-y leading-6"
          value={value}
          onChange={(event) => onChange(question.id, event.target.value)}
          placeholder="Write your answer"
        />
      )}

      <div className="mt-4">
        <SourceList sources={question.sources} />
      </div>
    </section>
  );
}
