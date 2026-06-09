import {
  AskQuestionResponse,
  DocumentOut,
  EvaluateWrittenResponse,
  GenerateTestRequest,
  GenerateTestResponse,
  GeneratedQuestion,
  StudyModeResponse,
  SubmitMcqResponse
} from "./types";

const rawApiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_BASE = rawApiBase.startsWith("http") ? rawApiBase : `https://${rawApiBase}`;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
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

export function uploadPdfs(files: File[], onProgress: (progress: number) => void): Promise<DocumentOut[]> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/upload-pdf`);
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

export function studyMode(topic: string, includeDiagram: boolean, documentIds: string[] = []): Promise<StudyModeResponse> {
  return request<StudyModeResponse>("/study-mode", {
    method: "POST",
    body: JSON.stringify({ topic, include_diagram: includeDiagram, document_ids: documentIds })
  });
}

export function askQuestion(question: string, documentIds: string[] = []): Promise<AskQuestionResponse> {
  return request<AskQuestionResponse>("/ask-question", {
    method: "POST",
    body: JSON.stringify({ question, top_k: 6, document_ids: documentIds })
  });
}
