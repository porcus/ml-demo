import React, { useMemo } from "react";
import type { Application } from "../types/loanModels";

interface Props {
  applications: Application[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
}

export const ApplicationSelector: React.FC<Props> = ({
  applications,
  selectedIds,
  onSelectionChange,
}) => {
  const allSelected =
    applications.length > 0 &&
    selectedIds.length === applications.length;

  const toggleAll = () => {
    if (allSelected) {
      onSelectionChange([]);
    } else {
      onSelectionChange(applications.map((a) => a.application_id));
    }
  };

  const toggleOne = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((x) => x !== id));
    } else {
      onSelectionChange([...selectedIds, id]);
    }
  };

  const stats = useMemo(() => {
    if (applications.length === 0) return null;

    const count = applications.length;
    const manual = applications.filter((a) => a.decision_source === "manual");
    const auto = applications.filter((a) => a.decision_source === "auto");
    const manualApproved = manual.filter(
      (a) => a.final_decision === "approve"
    ).length;
    const manualDeclined = manual.filter(
      (a) => a.final_decision === "decline"
    ).length;
    const undecisioned = applications.filter(
      (a) => !a.final_decision
    ).length;

    const avgScore =
      applications.reduce((sum, a) => sum + a.credit_score, 0) / count;
    const avgDti =
      applications.reduce((sum, a) => sum + a.dti_ratio, 0) / count;

    return {
      count,
      manualCount: manual.length,
      autoCount: auto.length,
      manualApproved,
      manualDeclined,
      undecisioned,
      avgScore,
      avgDti,
    };
  }, [applications]);

  return (
    <div>
      <div style={{ marginBottom: 4, fontSize: 12, color: "#555" }}>
        {stats ? (
          <>
            {stats.count} apps | manual {stats.manualCount}, auto{" "}
            {stats.autoCount}, undecisioned {stats.undecisioned} | manual
            approvals {stats.manualApproved}, manual declines{" "}
            {stats.manualDeclined} | avg score{" "}
            {Math.round(stats.avgScore)}, avg DTI{" "}
            {stats.avgDti.toFixed(2)}
          </>
        ) : (
          "No applications loaded."
        )}
      </div>
      <div
        style={{
          maxHeight: 260,
          overflowY: "auto",
          border: "1px solid #ddd",
          borderRadius: 4,
        }}
      >
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 13,
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #eee",
                  textAlign: "left",
                }}
              >
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleAll}
                />{" "}
                App ID
              </th>
              <th style={{ padding: "4px 6px", borderBottom: "1px solid #eee" }}>
                Score
              </th>
              <th style={{ padding: "4px 6px", borderBottom: "1px solid #eee" }}>
                DTI
              </th>
              <th style={{ padding: "4px 6px", borderBottom: "1px solid #eee" }}>
                Decision
              </th>
              <th style={{ padding: "4px 6px", borderBottom: "1px solid #eee" }}>
                Source
              </th>
            </tr>
          </thead>
          <tbody>
            {applications.map((a) => {
              const isSelected = selectedIds.includes(a.application_id);
              return (
                <tr
                  key={a.application_id}
                  onClick={() => toggleOne(a.application_id)}
                  style={{
                    cursor: "pointer",
                    backgroundColor: isSelected ? "#eef6ff" : "white",
                  }}
                >
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    <input
                      type="checkbox"
                      readOnly
                      checked={isSelected}
                      style={{ marginRight: 6 }}
                    />
                    {a.application_id}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {a.credit_score}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {a.dti_ratio.toFixed(2)}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {a.final_decision ?? "-"}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {a.sourceLabel ??
                      a.sourceType ??
                      a.decision_source ??
                      ""}
                  </td>
                </tr>
              );
            })}
            {applications.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: 8 }}>
                  No applications.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
