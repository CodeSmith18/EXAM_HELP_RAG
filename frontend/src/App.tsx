import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { DocumentsPage } from "./pages/DocumentsPage";
import { GenerateTestPage } from "./pages/GenerateTestPage";
import { ResultsPage } from "./pages/ResultsPage";
import { StudyModePage } from "./pages/StudyModePage";
import { TakeTestPage } from "./pages/TakeTestPage";
import { UploadPage } from "./pages/UploadPage";
import { CombinedResults, GenerateTestResponse } from "./types";

export default function App() {
  const [currentTest, setCurrentTest] = useState<GenerateTestResponse | null>(null);
  const [results, setResults] = useState<CombinedResults | null>(null);

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/generate-test" element={<GenerateTestPage onGenerated={setCurrentTest} />} />
        <Route path="/take-test" element={<TakeTestPage test={currentTest} onResults={setResults} />} />
        <Route path="/results" element={<ResultsPage results={results} />} />
        <Route path="/study" element={<StudyModePage />} />
      </Route>
    </Routes>
  );
}

