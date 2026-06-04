import { Icon } from "@/components/Icon";

export function DisclaimerBanner() {
  return (
    <div className="mf-disclaimer" role="note" aria-label="Disclaimer">
      <Icon name="shield" size={18} />
      <span>Facts-only. No investment advice.</span>
    </div>
  );
}
