import { BrowserRouter, Route, Routes } from "react-router-dom";

import Shell from "./components/Shell.jsx";
import { Loading } from "./components/ui.jsx";
import { AppProvider, useApp } from "./context/AppContext.jsx";
import Assessments from "./pages/Assessments.jsx";
import Chat from "./pages/Chat.jsx";
import { LibraryDocument, LibraryIndex } from "./pages/Library.jsx";
import NotFound from "./pages/NotFound.jsx";
import Overview from "./pages/Overview.jsx";
import Progress from "./pages/Progress.jsx";
import Subjects from "./pages/Subjects.jsx";
import TeacherConsole from "./pages/Teacher.jsx";
import Translate from "./pages/Translate.jsx";

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
      <Route element={<Shell />}>
        <Route index element={<Overview />} />
        <Route path="subjects" element={<Subjects />} />
        <Route path="learn/:slug" element={<Chat mode="subject" />} />
        <Route path="learn/:slug/:conversationId" element={<Chat mode="subject" />} />
        <Route path="helpdesk" element={<Chat mode="helpdesk" />} />
        <Route path="helpdesk/:conversationId" element={<Chat mode="helpdesk" />} />
        <Route path="assessments" element={<Assessments />} />
        <Route path="assessments/:slug" element={<Assessments />} />
        <Route path="notes" element={<LibraryIndex />} />
        <Route path="notes/:slug" element={<LibraryDocument />} />
        <Route path="progress" element={<Progress />} />
        <Route path="translate" element={<Translate />} />
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
