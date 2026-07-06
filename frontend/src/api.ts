import {
  AskQuestionResponse,
  AuthResponse,
  DocumentOut,
  EvaluateWrittenResponse,
  GenerateTestRequest,
  GenerateTestResponse,
  GeneratedQuestion,
  SavedTestResult,
  StudyModeResponse,
  StudySessionOut,
  SubmitMcqResponse,
  TestHistoryItem,
  UserOut
} from "./types";

const rawApiBase = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://localhost:8000" : "");
const API_BASE = rawApiBase ? (rawApiBase.startsWith("http") ? rawApiBase : `https://${rawApiBase}`) : "";
const AUTH_TOKEN_KEY = "examprep_auth_token";

export function getAuthToken(): string {
  return window.localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

export function setAuthToken(token: string) {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken() {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {})
    }
  });
  if (!response.ok) {
    const text = await response.text();
    try {
      const data = JSON.parse(text);
      throw new Error(data.detail || text);
    } catch {
      throw new Error(text || `Request failed with ${response.status}`);
    }
  }
  return response.json();
}

export async function registerAccount(email: string, password: string, fullName?: string): Promise<AuthResponse> {
  const response = await request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName || null })
  });
  setAuthToken(response.access_token);
  return response;
}

export async function loginAccount(email: string, password: string): Promise<AuthResponse> {
  const response = await request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
  setAuthToken(response.access_token);
  return response;
}

export function getCurrentUser(): Promise<UserOut> {
  return request<UserOut>("/auth/me");
}

export function uploadPdfs(files: File[], onProgress: (progress: number) => void): Promise<DocumentOut[]> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/upload-pdf`);
    const token = getAuthToken();
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText).documents);
        } catch {
          reject(new Error("Upload completed but the response could not be read."));
        }
      } else {
        try {
          const data = JSON.parse(xhr.responseText);
          reject(new Error(data.detail || xhr.responseText));
        } catch {
          reject(new Error(xhr.responseText || `Upload failed with ${xhr.status}`));
        }
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed. Check that the backend is running."));
    xhr.send(form);
  });
}

export function listDocuments(): Promise<DocumentOut[]> {
  return request<DocumentOut[]>("/documents");
}

export function reingestDocument(documentId: string): Promise<DocumentOut> {
  return request<DocumentOut>("/ingest-document", {
    method: "POST",
    body: JSON.stringify({ document_id: documentId })
  });
}

export function generateTest(payload: GenerateTestRequest): Promise<GenerateTestResponse> {
  return request<GenerateTestResponse>("/generate-test", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listTests(): Promise<TestHistoryItem[]> {
  return request<TestHistoryItem[]>("/tests");
}

export function getTest(testId: string): Promise<GenerateTestResponse> {
  return request<GenerateTestResponse>(`/tests/${testId}`);
}

export function submitMcqTest(
  questions: GeneratedQuestion[],
  answers: Record<string, string>
): Promise<SubmitMcqResponse> {
  return request<SubmitMcqResponse>("/submit-mcq-test", {
    method: "POST",
    body: JSON.stringify({
      questions,
      answers: Object.entries(answers).map(([question_id, selected_answer]) => ({ question_id, selected_answer }))
    })
  });
}

export function evaluateWrittenTest(
  questions: GeneratedQuestion[],
  answers: Record<string, string>
): Promise<EvaluateWrittenResponse> {
  return request<EvaluateWrittenResponse>("/evaluate-written-test", {
    method: "POST",
    body: JSON.stringify({
      questions,
      answers: Object.entries(answers).map(([question_id, answer]) => ({ question_id, answer }))
    })
  });
}

export function saveTestResult(
  test: GenerateTestResponse,
  mcq: SubmitMcqResponse | null,
  written: EvaluateWrittenResponse | null
): Promise<SavedTestResult> {
  return request<SavedTestResult>("/save-test-result", {
    method: "POST",
    body: JSON.stringify({ test, mcq, written })
  });
}

export function listTestResults(): Promise<SavedTestResult[]> {
  return request<SavedTestResult[]>("/test-results");
}

export function studyMode(topic: string, includeDiagram: boolean, documentIds: string[] = []): Promise<StudyModeResponse> {
  return request<StudyModeResponse>("/study-mode", {
    method: "POST",
    body: JSON.stringify({ topic, include_diagram: includeDiagram, document_ids: documentIds })
  });
}

export function listStudySessions(): Promise<StudySessionOut[]> {
  return request<StudySessionOut[]>("/study-sessions");
}

export function askQuestion(question: string, documentIds: string[] = []): Promise<AskQuestionResponse> {
  return request<AskQuestionResponse>("/ask-question", {
    method: "POST",
    body: JSON.stringify({ question, top_k: 6, document_ids: documentIds })
  });
}
