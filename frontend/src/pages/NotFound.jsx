import { Compass } from "lucide-react";
import { Link } from "react-router-dom";

import { useCrumbs } from "../components/Shell.jsx";
import { EmptyState } from "../components/ui.jsx";
import { useApp } from "../context/AppContext.jsx";

export default function NotFound() {
  const { t } = useApp();
  useCrumbs([{ label: "Not found" }]);
  return (
    <EmptyState icon={Compass} title="This page doesn't exist" action={<Link className="btn" to="/">{t("back_home")}</Link>}>
      The link may be out of date, or the page may have moved.
    </EmptyState>
  );
}
