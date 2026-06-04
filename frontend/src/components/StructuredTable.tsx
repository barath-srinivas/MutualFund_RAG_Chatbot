import { Icon } from "@/components/Icon";
import type { StructuredTablePayload } from "@/lib/api";

type Props = {
  data: StructuredTablePayload;
};

export function StructuredTable({ data }: Props) {
  return (
    <div>
      <div className="mf-msg-brand">
        <Icon name="table_chart" size={18} />
        <span>{data.title ?? "Data summary"}</span>
      </div>
      <div className="mf-table-wrap">
        <table className="mf-table">
          <thead>
            <tr>
              {data.columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td key={`cell-${rowIndex}-${cellIndex}`}>{cell || "—"}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
