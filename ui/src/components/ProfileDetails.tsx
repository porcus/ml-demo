// src/components/ProfileDetails.tsx
import React from "react";
import type { DecisionProfile } from "../types/loanModels";

interface Props {
  profile: DecisionProfile;
}

export const ProfileDetails: React.FC<Props> = ({ profile }) => {
  const rules = profile.rules.map((prc) => prc.rule);

  return (
    <div style={{ fontSize: 14 }}>
      <section style={{ marginBottom: 12 }}>
        <h3>Profile Info</h3>
        <div>
          <strong>Name:</strong> {profile.name}
        </div>
        {profile.description && (
          <div>
            <strong>Description:</strong> {profile.description}
          </div>
        )}
        <div>
          <strong>Approval threshold:</strong>{" "}
          {profile.approval_threshold}
        </div>
        <div>
          <strong>Origin:</strong>{" "}
          {profile._origin ?? "unknown"} |{" "}
          <strong>Saved at:</strong>{" "}
          {profile._savedAt
            ? new Date(profile._savedAt).toLocaleString()
            : profile.created_at
            ? new Date(profile.created_at).toLocaleString()
            : "unknown"}
        </div>
        <div>
          <strong>Source applications:</strong>{" "}
          {profile.source_application_ids.length}
        </div>
      </section>

      {profile.llm_explanation && (
        <section style={{ marginBottom: 12 }}>
          <h3>LLM Explanation</h3>
          <p
            style={{
              whiteSpace: "pre-wrap",
              backgroundColor: "#f9f9f9",
              padding: 8,
              borderRadius: 4,
              border: "1px solid #eee",
            }}
          >
            {profile.llm_explanation}
          </p>
        </section>
      )}

      <section>
        <h3>Rules ({rules.length})</h3>
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
                Name
              </th>
              <th
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #eee",
                }}
              >
                Expression
              </th>
              <th
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #eee",
                }}
              >
                Target
              </th>
              <th
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #eee",
                }}
              >
                Support / Confidence
              </th>
              <th
                style={{
                  padding: "4px 6px",
                  borderBottom: "1px solid #eee",
                }}
              >
                Base score
              </th>
            </tr>
          </thead>
          <tbody>
            {profile.rules.map((prc) => {
              const r = prc.rule;
              return (
                <tr key={r.rule_instance_id}>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {r.name}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    <code>{r.expression}</code>
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {r.target_decision_hint ?? "-"}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {r.support_count} / {r.confidence.toFixed(2)}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      borderBottom: "1px solid #f3f3f3",
                    }}
                  >
                    {r.suggested_base_score}
                  </td>
                </tr>
              );
            })}
            {rules.length === 0 && (
              <tr>
                <td colSpan={5} style={{ padding: 8 }}>
                  No rules in this profile.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Rule explanations */}
        {profile.rules.map((prc) => {
          const r = prc.rule;
          if (!r.llm_explanation) return null;
          return (
            <div
              key={`${r.rule_instance_id}-ex`}
              style={{
                marginTop: 8,
                padding: 8,
                backgroundColor: "#fafafa",
                borderRadius: 4,
                border: "1px solid #eee",
              }}
            >
              <strong>{r.name} — explanation</strong>
              <p style={{ whiteSpace: "pre-wrap", marginTop: 4 }}>
                {r.llm_explanation}
              </p>
            </div>
          );
        })}
      </section>
    </div>
  );
};
