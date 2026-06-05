import type { Scheme } from "./schemes";

export type ExampleQuestion = {
  label: string;
  message: string;
  scheme_id: Scheme["scheme_id"];
};

/** Phase 4 example questions: fee, exit load, fund manager. */
export const EXAMPLE_QUESTIONS: ExampleQuestion[] = [
  {
    label: "Expense ratio (Large Cap)",
    message: "What is the expense ratio of the Large Cap Fund?",
    scheme_id: "icici-large-cap",
  },
  {
    label: "Exit load (Multi Asset)",
    message: "What is the exit load for the Multi Asset Fund?",
    scheme_id: "icici-multi-asset",
  },
  {
    label: "Fund manager (Manufacturing)",
    message: "Who manages the Manufacturing Fund?",
    scheme_id: "icici-manufacturing",
  },
];
