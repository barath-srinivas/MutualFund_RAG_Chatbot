"use client";

import { Icon } from "@/components/Icon";
import { APP_AMC_LABEL, APP_PRODUCT_LABEL } from "@/lib/app-config";

type Props = {
  onShowDisclaimer?: () => void;
};

export function AppHeader({ onShowDisclaimer }: Props) {
  return (
    <header className="mf-header">
      <div className="mf-header-inner">
        <div className="mf-header-brand">
          <h1 className="mf-header-title">{APP_AMC_LABEL}</h1>
          <p className="mf-header-subtitle">{APP_PRODUCT_LABEL}</p>
        </div>
        <div className="mf-header-actions">
          <button
            type="button"
            className="mf-icon-btn"
            onClick={onShowDisclaimer}
            aria-label="View disclaimer"
          >
            <Icon name="shield" size={22} />
          </button>
          <button
            type="button"
            className="mf-icon-btn"
            onClick={onShowDisclaimer}
            aria-label="About this assistant"
          >
            <Icon name="info" size={22} />
          </button>
        </div>
      </div>
    </header>
  );
}
