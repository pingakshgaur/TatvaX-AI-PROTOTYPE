import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";

import Shell from "./components/Shell.jsx";
import { Loading } from "./components/ui.jsx";
import { AppProvider, useApp } from "./context/AppContext.jsx";
import { AssessmentHistory, AssessmentReview } from "./pages/AssessmentHistory.jsx";
import Assessments from "./pages/Assessments.jsx";
import Chat from "./pages/Chat.jsx";
import { LibraryDocument, LibraryIndex } from "./pages/Library.jsx";
import NotFound from "./pages/NotFound.jsx";
import Overview from "./pages/Overview.jsx";
import { PrintAssessment, PrintNotes } from "./pages/Print.jsx";
import Progress from "./pages/Progress.jsx";
import Subjects from "./pages/Subjects.jsx";
import TeacherConsole from "./pages/Teacher.jsx";
import Todos from "./pages/Todos.jsx";
import Translate from "./pages/Translate.jsx";

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
      <Route path="print/notes/:slug" element={<PrintNotes />} />
      <Route path="print/assessment/:id" element={<PrintAssessment />} />
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
