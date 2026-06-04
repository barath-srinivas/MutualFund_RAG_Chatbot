import { APP_NAME } from "@/lib/app-config";

export function AppFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="mf-footer">
      <div className="mf-footer-inner">
        <span className="mf-footer-brand">{APP_NAME}</span>
        <span>Facts-only · No investment advice · Official AMC / AMFI / SEBI</span>
        <span>© {year} · Informational purposes only</span>
      </div>
    </footer>
  );
}
