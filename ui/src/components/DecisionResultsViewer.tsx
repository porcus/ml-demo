// src/components/DecisionResultsViewer.tsx
import React, { useMemo } from "react";
import type {
  SavedDecisionRun,
  ApplicationDecisionResult,
  ProfileDecisionResult,
} from "../types/loanModels";

interface Props {
  run: SavedDecisionRun;
}

export const DecisionResultsViewer: React.FC<Props> = ({ run }) => {
  const { results, applications, profiles } = run;

  const stats = useMemo(() => {
    if (!results.length) return null;

    let totalWithManual = 0;
    let matchCount = 0;
    let falseApprovals = 0;
    let falseDeclines = 0;

    let autoDecisionCount = 0; // not refer
    let totalApps = results.length;

    for (const r of results) {
      const manual = r.manual_final_decision;
      const system = r.final_system_decision;

      if (system !== "refer") {
        autoDecisionCount++;
      }

      if (!manual) continue;

      totalWithManual++;
      if (manual === "approve" && system === "approve") {
        matchCount++;
      } else if (manual === "decline" && system === "decline") {
        matchCount++;
      } else if (manual === "decline" && system === "approve") {
        falseApprovals++;
      } else if (manual === "approve" && system === "decline") {
        falseDeclines++;
      }
    }

    const matchRate =
      totalWithManual > 0 ? matchCount / totalWithManual : null;
    const autoDecisionRate =
      totalApps > 0 ? autoDecisionCount / totalApps : null;

    return {
      totalApps,
      totalWithManual,
      matchRate,
      autoDecisionRate,
      falseApprovals,
      falseDeclines,
    };
  }, [results]);

  const findApp = (id: string) =>
    applications.find((a) => a.application_id === id);

  const profileNameById = (id: string) =>
    profiles.find((p) => (p.id || "") === id)?.name ?? id;

  return (
    <div style={{ marginTop: 8 }}>
      <h3>Decision Results — {run.name}</h3>
      {stats && (
        <div style={{ fontSize: 13, marginBottom: 8 }}>
          <div>
            <strong>Applications:</strong> {stats.totalApps} (
            {stats.totalWithManual} with manual decisions)
          </div>
          <div>
            <strong>Match rate vs manual:</strong>{" "}
            {stats.matchRate != null
              ? `${(stats.matchRate * 100).toFixed(1)}%`
              : "n/a"}
          </div>
          <div>
            <strong>Auto-decision rate:</strong>{" "}
            {stats.autoDecisionRate != null
              ? `${(stats.autoDecisionRate * 100).toFixed(1)}%`
              : "n/a"}
          </div>
          <div>
            <strong>False approvals:</strong> {stats.falseApprovals} |{" "}
            <strong>False declines:</strong> {stats.falseDeclines}
          </div>
        </div>
      )}

      <div
        style={{
          maxHeight: 320,
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
                App ID
              </th>
              <th
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #eee",
                }}
              >
                Manual
              </th>
              {profiles.map((p) => (
                <th
                  key={p.id || ""}
                  style={{
                    padding: "4px 6px",
                    borderBottom: "1px solid #eee",
                  }}
                >
                  {p.name}
                </th>
              ))}
              <th
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #eee",
                }}
              >
                System
              </th>
              <th
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #eee",
                }}
              >
                Needs review?
              </th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => {
              const app = findApp(r.application_id);
              const manual = r.manual_final_decision ?? "-";
              const system = r.final_system_decision;

              return (
                <tr key={r.application_id}>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {r.application_id}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {manual}
                  </td>
                  {profiles.map((p) => {
                    const pr: ProfileDecisionResult | undefined =
                      r.profile_results.find(
                        (x) => x.profile_id === (p.id || "")
                      );
                    return (
                      <td
                        key={p.id || ""}
                        style={{
                          padding: "4px 6px",
                          borderBottom: "1px solid #f3f3f3",
                        }}
                      >
                        {pr
                          ? `${pr.decision} (${pr.total_score.toFixed(1)})`
                          : "-"}
                      </td>
                    );
                  })}
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {system}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {r.needs_manual_review ? "yes" : "no"}
                  </td>
                </tr>
              );
            })}
            {results.length === 0 && (
              <tr>
                <td colSpan={4 + profiles.length} style={{ padding: 8 }}>
                  No results.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {/* You can extend this with a row-expansion UI to show rule-level details later */}
    </div>
  );
};
