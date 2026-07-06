export type TestMode = "mcq" | "written" | "mixed";
export type Difficulty = "Easy" | "Medium" | "Hard";

export interface DocumentOut {
  id: string;
  file_name: string;
  uploaded_at: string;
  page_count: number;
  chunk_count: number;
  status: string;
  error?: string | null;
}

export interface SourceRef {
  document_id: string;
  file_name: string;
  page_number: number;
  chunk_id: string;
  score?: number | null;
}

export interface GeneratedQuestion {
  id: string;
  type: "mcq" | "written";
  question: string;
  options: string[];
  correct_answer?: string | null;
  explanation?: string | null;
  model_answer?: string | null;
  rubric: string[];
  sources: SourceRef[];
}

export interface GenerateTestRequest {
  mode: TestMode;
  num_questions: number;
  difficulty: Difficulty;
  topic?: string | null;
  document_ids?: string[];
}

export interface GenerateTestResponse {
  test_id: string;
  mode: TestMode;
  difficulty: Difficulty;
  topic?: string | null;
  questions: GeneratedQuestion[];
  sources: SourceRef[];
}

export interface TestHistoryItem {
  test_id: string;
  mode: TestMode;
  difficulty: Difficulty;
  topic?: string | null;
  question_count: number;
  created_at: string;
  sources: SourceRef[];
}

export interface McqResultItem {
  question_id: string;
  question: string;
  selected_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation?: string | null;
}

export interface SubmitMcqResponse {
  score: number;
  total: number;
  percentage: number;
  results: McqResultItem[];
}

export interface WrittenEvaluationItem {
  question_id: string;
  question: string;
  score: number;
  max_score: number;
  feedback: string;
  model_answer: string;
  rubric_breakdown: Record<string, unknown>;
  sources: SourceRef[];
}

export interface EvaluateWrittenResponse {
  score: number;
  max_score: number;
  percentage: number;
  results: WrittenEvaluationItem[];
}

export interface SavedTestResult {
  result_id: string;
  test: GenerateTestResponse;
  mcq?: SubmitMcqResponse | null;
  written?: EvaluateWrittenResponse | null;
  submitted_at: string;
  percentage: number;
}

export interface StudyModeResponse {
  topic: string;
  simple_explanation: string;
  key_points: string[];
  example?: string | null;
  important_terms: Array<{ term: string; meaning: string }>;
  quick_revision_summary: string;
  mermaid_diagram?: string | null;
  sources: SourceRef[];
}

export interface AskQuestionResponse {
  answer: string;
  sources: SourceRef[];
}

export interface CombinedResults {
  resultId?: string;
  test: GenerateTestResponse;
  mcq?: SubmitMcqResponse | null;
  written?: EvaluateWrittenResponse | null;
  submittedAt: string;
  percentage?: number;
}
