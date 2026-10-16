import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";

import Shell from "./components/Shell.jsx";
import { Loading } from "./components/ui.jsx";
import { AppProvider, useApp } from "./context/AppContext.jsx";
import NotFound from "./pages/NotFound.jsx";
import Overview from "./pages/Overview.jsx";

// Every other page is loaded when it is first opened, so the first visit downloads far less.
const named = (load, name) => lazy(() => load().then((m) => ({ default: m[name] })));
const loadHistory = () => import("./pages/AssessmentHistory.jsx");
const loadLibrary = () => import("./pages/Library.jsx");
const loadPrint = () => import("./pages/Print.jsx");
const AssessmentHistory = named(loadHistory, "AssessmentHistory");
const AssessmentReview = named(loadHistory, "AssessmentReview");
const Assessments = lazy(() => import("./pages/Assessments.jsx"));
const Chat = lazy(() => import("./pages/Chat.jsx"));
const LibraryDocument = named(loadLibrary, "LibraryDocument");
const LibraryIndex = named(loadLibrary, "LibraryIndex");
const PrintAssessment = named(loadPrint, "PrintAssessment");
const PrintNotes = named(loadPrint, "PrintNotes");
const Progress = lazy(() => import("./pages/Progress.jsx"));
const Subjects = lazy(() => import("./pages/Subjects.jsx"));
const TeacherConsole = lazy(() => import("./pages/Teacher.jsx"));
const Todos = lazy(() => import("./pages/Todos.jsx"));
const Translate = lazy(() => import("./pages/Translate.jsx"));

// Once the app is idle, fetch the remaining pages in the background so they open instantly and
// the service worker can keep them for offline use.
if (typeof window !== "undefined") {
  const warm = () => [loadHistory, loadLibrary, () => import("./pages/Chat.jsx"), () => import("./pages/Subjects.jsx"),
    () => import("./pages/Assessments.jsx"), () => import("./pages/Todos.jsx"), () => import("./pages/Translate.jsx"),
    () => import("./pages/Progress.jsx"), () => import("./components/MarkdownView.jsx")].forEach((load) => load().catch(() => {}));
  window.addEventListener("load", () => (window.requestIdleCallback || ((fn) => setTimeout(fn, 2500)))(warm), { once: true });
}

// Old help desk links now open TatvAI.
function HelpdeskRedirect() {
  const { conversationId } = useParams();
  return <Navigate to={conversationId ? `/tatvai/${conversationId}` : "/tatvai"} replace />;
}

function Routed() {
  const { app, bootError, retryBoot } = useApp();
  if (bootError) {
    return (
      <div className="empty-state" style={{ paddingTop: 120 }}>
        <h2>TatvaX could not start</h2>
        <p>{bootError}</p>
        <button className="btn" type="button" onClick={retryBoot}>Try again</button>
      </div>
    );
  }
  if (!app) return <Loading label="Starting TatvaX" />;

  return (
    <Routes>
      <Route path="print/notes/:slug" element={<Suspense fallback={<Loading />}><PrintNotes /></Suspense>} />
      <Route path="print/assessment/:id" element={<Suspense fallback={<Loading />}><PrintAssessment /></Suspense>} />
      <Route element={<Shell />}>
        <Route index element={<Overview />} />
        <Route path="subjects" element={<Subjects />} />
        <Route path="learn/:slug" element={<Chat mode="subject" />} />
        <Route path="learn/:slug/:conversationId" element={<Chat mode="subject" />} />
        <Route path="tatvai" element={<Chat mode="helpdesk" />} />
        <Route path="tatvai/:conversationId" element={<Chat mode="helpdesk" />} />
        <Route path="helpdesk" element={<HelpdeskRedirect />} />
        <Route path="helpdesk/:conversationId" element={<HelpdeskRedirect />} />
        <Route path="assessments" element={<Assessments />} />
        <Route path="assessments/history" element={<AssessmentHistory />} />
        <Route path="assessments/review/:id" element={<AssessmentReview />} />
        <Route path="assessments/:slug" element={<Assessments />} />
        <Route path="notes" element={<LibraryIndex />} />
        <Route path="notes/:slug" element={<LibraryDocument />} />
        <Route path="progress" element={<Progress />} />
        <Route path="translate" element={<Translate />} />
        <Route path="todos" element={<Todos />} />
        <Route path="teacher" element={<TeacherConsole />} />
        <Route path="teacher/:tab" element={<TeacherConsole />} />
        <Route path="teacher/:tab/:slug" element={<TeacherConsole />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routed />
      </BrowserRouter>
    </AppProvider>
  );
}
