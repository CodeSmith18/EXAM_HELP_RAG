import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { AUTH_REQUIRED_EVENT, clearAuthToken, getAuthToken, getCurrentUser } from "./api";
import { AppShell } from "./components/AppShell";
import { AuthPage } from "./pages/AuthPage";
import { Dashboard } from "./pages/Dashboard";
import { DocumentsPage } from "./pages/DocumentsPage";
import { GenerateTestPage } from "./pages/GenerateTestPage";
import { ResultsPage } from "./pages/ResultsPage";
import { StudyModePage } from "./pages/StudyModePage";
import { TakeTestPage } from "./pages/TakeTestPage";
import { UploadPage } from "./pages/UploadPage";
import { CombinedResults, GenerateTestResponse, UserOut } from "./types";

export default function App() {
  const [user, setUser] = useState<UserOut | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [currentTest, setCurrentTest] = useState<GenerateTestResponse | null>(null);
  const [results, setResults] = useState<CombinedResults | null>(null);

  useEffect(() => {
    if (!getAuthToken()) {
      setAuthLoading(false);
      return;
    }

    getCurrentUser()
      .then(setUser)
      .catch(() => {
        clearAuthToken();
        setUser(null);
      })
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    function handleAuthRequired() {
      setUser(null);
      setCurrentTest(null);
      setResults(null);
    }

    window.addEventListener(AUTH_REQUIRED_EVENT, handleAuthRequired);
    return () => window.removeEventListener(AUTH_REQUIRED_EVENT, handleAuthRequired);
  }, []);

  function handleLogout() {
    clearAuthToken();
    setUser(null);
    setCurrentTest(null);
    setResults(null);
  }

  if (authLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <section className="card p-6 text-center">
          <p className="text-sm font-semibold text-slate-500">Loading workspace</p>
        </section>
      </main>
    );
  }

  if (!user) {
    return <AuthPage onAuthenticated={setUser} />;
  }

  return (
    <Routes>
      <Route element={<AppShell user={user} onLogout={handleLogout} />}>
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
