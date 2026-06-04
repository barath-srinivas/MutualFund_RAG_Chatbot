"use client";

import { Icon } from "@/components/Icon";
import { SCHEMES } from "@/data/schemes";
import { schemeShortLabel } from "@/lib/scheme-label";

type Props = {
  schemeId: string;
  onSchemeSelect: (schemeId: string) => void;
  onClearScheme: () => void;
};

function schemeIcon(category: string): string {
  if (category.includes("Debt")) return "account_balance";
  if (category.includes("Hybrid")) return "hub";
  return "trending_up";
}

export function FundsSidebar({
  schemeId,
  onSchemeSelect,
  onClearScheme,
}: Props) {
  return (
    <aside className="mf-sidebar">
      <h2 className="mf-sidebar-title">Funds Catalog</h2>
      <p className="mf-sidebar-sub">10 official direct-growth schemes</p>

      <nav className="mf-sidebar-nav">
        <button
          type="button"
          className={`mf-nav-item${!schemeId ? " mf-nav-item--active" : ""}`}
          onClick={onClearScheme}
        >
          <Icon name="chat" size={18} />
          <span>Chat Home</span>
        </button>

        {SCHEMES.map((s) => (
          <button
            key={s.scheme_id}
            type="button"
            className={`mf-nav-item${schemeId === s.scheme_id ? " mf-nav-item--active" : ""}`}
            onClick={() => onSchemeSelect(s.scheme_id)}
            title={s.display_name}
          >
            <Icon name={schemeIcon(s.category)} size={18} />
            <span>{schemeShortLabel(s.display_name)}</span>
          </button>
        ))}
      </nav>

      <div className="mf-sidebar-footer">
        <button type="button" className="mf-btn-block" onClick={onClearScheme}>
          All schemes
        </button>
        <p className="mf-sidebar-note">
          <Icon name="gavel" size={16} />
          <span>Facts from official ICICI Prudential AMC pages only</span>
        </p>
      </div>
    </aside>
  );
}
