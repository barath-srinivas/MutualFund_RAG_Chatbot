import { Icon } from "@/components/Icon";
import { EXAMPLE_QUESTIONS, type ExampleQuestion } from "@/data/examples";

type Props = {
  onSelect: (example: ExampleQuestion) => void;
  disabled?: boolean;
};

export function ExampleQuestions({ onSelect, disabled }: Props) {
  return (
    <div>
      <p className="mf-examples-title">Try an example</p>
      <div className="mf-chips">
        {EXAMPLE_QUESTIONS.map((ex) => (
          <button
            key={ex.label}
            type="button"
            className="mf-chip"
            disabled={disabled}
            onClick={() => onSelect(ex)}
          >
            <span>{ex.label}</span>
            <Icon name="arrow_forward" size={16} />
          </button>
        ))}
      </div>
      <p className="mf-hint">Clicking an example sends the question immediately.</p>
    </div>
  );
}
