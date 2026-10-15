import { BookOpen, ChevronRight, ClipboardCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import { PageHeader, Panel } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";
import { subjectCode } from "../lib/format.js";

export function SubjectRows({ showAll = true }) {
  const { app, t } = useApp();
  return (
    <>
      {showAll && (
        <Link className="list-row" to="/learn/all">
          <span className="subject-code" style={{ "--subject-color": "var(--accent)" }}>ALL</span>
          <span className="grow">
            <span className="title">{t("all_subjects")}</span>
            <span className="desc" style={{ display: "block" }}>{t("all_subjects_desc")}</span>
          </span>
          <ChevronRight className="chev" size={18} aria-hidden="true" />
        </Link>
      )}
      {app.subjects.map((subject) => (
        <div className="list-row" key={subject.slug}>
          <span className="subject-code" style={{ "--subject-color": subject.color }}>{subjectCode(subject.title)}</span>
          <Link className="grow" to={`/learn/${subject.slug}`} style={{ color: "inherit", textDecoration: "none" }}>
            <span className="title">{subject.title}</span>
            <span className="desc" style={{ display: "block" }}>{subject.description}</span>
          </Link>
          <Link className="btn btn-ghost btn-sm" to={`/assessments/${subject.slug}`} title={t("nav_quiz")}>
            <ClipboardCheck size={15} /><span className="sr-only">{t("nav_quiz")}: {subject.title}</span>
          </Link>
          <Link className="btn btn-ghost btn-sm" to={`/notes/${subject.slug}`} title={t("nav_library")}>
            <BookOpen size={15} /><span className="sr-only">{t("nav_library")}: {subject.title}</span>
          </Link>
          <Link className="btn btn-secondary btn-sm" to={`/learn/${subject.slug}`}>{t("open")}</Link>
        </div>
      ))}
    </>
  );
}

export default function Subjects() {
  const { t } = useApp();
  useCrumbs([{ label: t("nav_subjects") }]);
  return (
    <>
      <PageHeader eyebrow={t("group_learn")} title={t("choose_subject")} lede={t("choose_subject_sub")} />
      <Panel tight><SubjectRows /></Panel>
    </>
  );
}
