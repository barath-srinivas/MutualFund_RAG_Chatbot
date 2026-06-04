import { ExampleQuestions } from "@/components/ExampleQuestions";
import type { ExampleQuestion } from "@/data/examples";

type Props = {
  onSelectExample: (example: ExampleQuestion) => void;
  disabled?: boolean;
};

export function WelcomePanel({ onSelectExample, disabled }: Props) {
  return (
    <section className="mf-content">
      <p className="mf-intro">
        Objective answers from 10 ICICI Prudential direct-growth schemes —
        expense ratio, exit load, SIP, benchmarks, and fund manager disclosures.
        Every response cites the official ICICI Prudential AMC fund page.
      </p>

      <div className="mf-card">
        <h2>Welcome to your compliance workspace</h2>
        <p>
          Ask factual questions only. I cannot provide investment advice,
          performance comparisons, or opinions on fund managers. Responses are
          limited to verifiable fields from official SEBI-compliant documents.
        </p>
      </div>

      <ExampleQuestions onSelect={onSelectExample} disabled={disabled} />
    </section>
  );
}
