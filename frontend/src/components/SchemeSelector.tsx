import { Icon } from "@/components/Icon";
import { SCHEMES } from "@/data/schemes";

type Props = {
  value: string;
  onChange: (schemeId: string) => void;
  disabled?: boolean;
};

export function SchemeSelector({ value, onChange, disabled }: Props) {
  return (
    <div className="mf-field">
      <label htmlFor="scheme-select">Scheme (optional)</label>
      <div className="mf-select-wrap">
        <select
          id="scheme-select"
          className="mf-select"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          aria-label="Select scheme"
        >
          <option value="">All 10 schemes (auto-detect)</option>
          {SCHEMES.map((s) => (
            <option key={s.scheme_id} value={s.scheme_id}>
              {s.display_name}
            </option>
          ))}
        </select>
        <span className="mf-select-chevron">
          <Icon name="expand_more" size={18} />
        </span>
      </div>
    </div>
  );
}
