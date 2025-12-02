import React, { useState } from "react";
import type { Application } from "../types/loanModels";
import { ApplicationSelector } from "./ApplicationSelector";

type GenerationStrategy = "llm" | "python";
type LoadMode = "append" | "replace";

interface Props {
  applications: Application[];
  onApplicationsChange: (apps: Application[]) => void;
  selectedIds: string[];
  onSelectedIdsChange: (ids: string[]) => void;
}

interface GenerateRequest {
  total_count: number;
  manual_count: number;
  manual_approved_count: number;
  generation_strategy: GenerationStrategy;
  seed?: number | null;
}

async function postJson<TReq, TRes>(
  url: string,
  body: TReq
): Promise<TRes> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed: ${res.status} ${text}`);
  }
  return (await res.json()) as TRes;
}

export const ApplicationsPage: React.FC<Props> = ({
  applications,
  onApplicationsChange,
  selectedIds,
  onSelectedIdsChange,
}) => {
  // Generation controls
  const [totalCount, setTotalCount] = useState<number>(100);
  const [manualPct, setManualPct] = useState<number>(100); // % of total
  const [approvedPct, setApprovedPct] = useState<number>(50); // % of manual
  const [strategy, setStrategy] = useState<GenerationStrategy>("python");

  const [jsonText, setJsonText] = useState<string>("");

  const [loadMode, setLoadMode] = useState<LoadMode>("append");

  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState<boolean>(false);

  // Derived counts
  const manualCount = Math.round((totalCount * manualPct) / 100);
  const manualApprovedCount = Math.round(
    (manualCount * approvedPct) / 100
  );
  const manualDeclinedCount = manualCount - manualApprovedCount;
  const undecisionedCount = totalCount - manualCount;

  const handleGenerate = async () => {
    setError(null);

    if (
      !Number.isFinite(totalCount) ||
      totalCount < 1 ||
      totalCount > 1000
    ) {
      setError("Total applications must be between 1 and 1000.");
      return;
    }
    if (manualCount < 0 || manualCount > totalCount) {
      setError("Manual count is out of range for total applications.");
      return;
    }
    if (
      manualApprovedCount < 0 ||
      manualApprovedCount > manualCount
    ) {
      setError(
        "Manual approved count must be between 0 and manual count."
      );
      return;
    }

    const body: GenerateRequest = {
      total_count: totalCount,
      manual_count: manualCount,
      manual_approved_count: manualApprovedCount,
      generation_strategy: strategy,
      seed: null,
    };

    setIsBusy(true);
    try {
      const generated = await postJson<GenerateRequest, Application[]>(
        "/api/applications/generate",
        body
      );

      // Tag apps client-side
      const now = new Date();
      const label = `${strategy.toUpperCase()} generation ${now.toLocaleString()}`;
      const batchId = `batch-${strategy}-${now.getTime()}`;

      const enriched = generated.map((a) => ({
        ...a,
        sourceType: strategy,
        sourceLabel: label,
        batchId,
      }));

      setJsonText(JSON.stringify(enriched, null, 2));
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setIsBusy(false);
    }
  };

  const handleLoad = () => {
    setError(null);
    if (!jsonText.trim()) {
      setError("JSON text is empty.");
      return;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonText);
    } catch (e: any) {
      setError("Failed to parse JSON: " + (e.message ?? String(e)));
      return;
    }

    if (!Array.isArray(parsed)) {
      setError("Expected JSON array of applications.");
      return;
    }

    const candidate = parsed as Application[];

    // Strict-ish schema + fuzzy validation
    const errors: string[] = [];
    const seenIds = new Set<string>();

    candidate.forEach((app, idx) => {
      const prefix = `App[${idx}]`;

      if (!app.application_id || typeof app.application_id !== "string") {
        errors.push(`${prefix}: application_id must be a non-empty string.`);
      } else if (seenIds.has(app.application_id)) {
        errors.push(`${prefix}: duplicate application_id ${app.application_id}.`);
      } else {
        seenIds.add(app.application_id);
      }

      if (typeof app.credit_score !== "number") {
        errors.push(`${prefix}: credit_score must be a number.`);
      } else if (app.credit_score < 300 || app.credit_score > 900) {
        errors.push(
          `${prefix}: credit_score ${app.credit_score} outside [300, 900].`
        );
      }

      if (typeof app.dti_ratio !== "number") {
        errors.push(`${prefix}: dti_ratio must be a number.`);
      } else if (app.dti_ratio < 0 || app.dti_ratio > 1.5) {
        errors.push(
          `${prefix}: dti_ratio ${app.dti_ratio} outside [0, 1.5].`
        );
      }

      if (
        app.monthly_gross_income &&
        app.monthly_debt_payments &&
        app.monthly_gross_income > 0
      ) {
        const impliedDti =
          app.monthly_debt_payments / app.monthly_gross_income;
        const diff = Math.abs(impliedDti - app.dti_ratio);
        if (diff > 0.2) {
          errors.push(
            `${prefix}: dti_ratio ${app.dti_ratio.toFixed(
              2
            )} inconsistent with income/debt (implied ${impliedDti.toFixed(
              2
            )}).`
          );
        }
      }

      if (!app.decision_source) {
        errors.push(`${prefix}: decision_source missing.`);
      } else if (
        app.decision_source !== "manual" &&
        app.decision_source !== "auto"
      ) {
        errors.push(
          `${prefix}: decision_source ${app.decision_source} invalid.`
        );
      }

      // final_decision can be null/undefined for undecisioned; if present, validate
      if (
        app.final_decision != null &&
        app.final_decision !== "approve" &&
        app.final_decision !== "decline"
      ) {
        errors.push(
          `${prefix}: final_decision ${app.final_decision} invalid.`
        );
      }
    });

    if (errors.length > 0) {
      const header = `${errors.length} validation error(s). Showing first 10:\n`;
      setError(header + errors.slice(0, 10).join("\n"));
      return;
    }

    const now = new Date();
    const importedLabel = `Imported JSON ${now.toLocaleString()}`;
    const batchId = `batch-import-${now.getTime()}`;

    const enriched: Application[] = candidate.map((a) => ({
      ...a,
      sourceType: a.sourceType ?? "import",
      sourceLabel: a.sourceLabel ?? importedLabel,
      batchId: a.batchId ?? batchId,
    }));

    if (loadMode === "replace") {
      onApplicationsChange(enriched);
      onSelectedIdsChange([]);
    } else {
      // append
      const combinedIds = new Set(applications.map((a) => a.application_id));
      const deduped = [
        ...applications,
        ...enriched.filter((a) => !combinedIds.has(a.application_id)),
      ];
      onApplicationsChange(deduped);
    }
  };

  const handleClearSelected = () => {
    if (selectedIds.length === 0) return;
    const remaining = applications.filter(
      (a) => !selectedIds.includes(a.application_id)
    );
    onApplicationsChange(remaining);
    onSelectedIdsChange([]);
  };

  // const manualPctWarning =
  //   manualCount === 0 || manualCount === totalCount || manualPct <= 10 || manualPct >= 90;
  const approvalPctWarning =
    manualCount > 0 &&
    (approvedPct <= 10 || approvedPct >= 90);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {error && (
        <div style={{ color: "red" }}>
          {error.split("\n").map((line, idx) => (
            <div key={idx}>{line}</div>
          ))}
        </div>
      )}

      {/* Generate */}
      <section
        style={{
          padding: 12,
          border: "1px solid #ccc",
          borderRadius: 4,
        }}
      >
        <h2>Generate Application Data</h2>

        <div style={{ marginBottom: 8 }}>
          <label>
            Number of applications (1–1000):{" "}
            <input
              type="number"
              min={1}
              max={1000}
              value={totalCount}
              onChange={(e) =>
                setTotalCount(
                  Math.max(
                    1,
                    Math.min(1000, Number(e.target.value) || 0)
                  )
                )
              }
              style={{ width: 80 }}
            />
          </label>
        </div>

        <div style={{ marginBottom: 8 }}>
          <label>
            Manually decisioned (% of total): {manualPct}%
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={manualPct}
            onChange={(e) => setManualPct(Number(e.target.value))}
            style={{ width: "100%" }}
          />
          <div style={{ fontSize: 12, color: "#555" }}>
            Manually decisioned: {manualCount} of {totalCount}, undecisioned:{" "}
            {undecisionedCount}.
          </div>
          {/* {manualPctWarning && (
            <div style={{ fontSize: 12, color: "#c27b00" }}>
              Warning: extreme manual percentage. Datasets with 0 or nearly
              0 / 100% manual decisions may not be useful for training.
            </div>
          )} */}
        </div>

        <div style={{ marginBottom: 8 }}>
          <label>
            Approved among manual (% of manual): {approvedPct}%
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={approvedPct}
            onChange={(e) => setApprovedPct(Number(e.target.value))}
            style={{ width: "100%" }}
          />
          <div style={{ fontSize: 12, color: "#555" }}>
            Manual approvals: {manualApprovedCount} of {manualCount}, manual
            declines: {manualDeclinedCount}.
          </div>
          {approvalPctWarning && manualCount > 0 && (
            <div style={{ fontSize: 12, color: "#c27b00" }}>
              Warning: approvals among manual are in an extreme range; mined
              rules may be trivial.
            </div>
          )}
        </div>

        <div style={{ marginBottom: 8 }}>
          <span>Generation strategy: </span>
          <label style={{ marginRight: 12 }}>
            <input
              type="radio"
              name="genStrategy"
              value="python"
              checked={strategy === "python"}
              onChange={() => setStrategy("python")}
            />{" "}
            Python simulation (very fast)
          </label>
          <label>
            <input
              type="radio"
              name="genStrategy"
              value="llm"
              checked={strategy === "llm"}
              onChange={() => setStrategy("llm")}
            />{" "}
            LLM (LM Studio) (very slow)
          </label>
        </div>

        <button onClick={handleGenerate} disabled={isBusy}>
          {isBusy ? "Generating..." : "Generate applications"}
        </button>
      </section>

      {/* JSON textarea + Load */}
      <section
        style={{
          padding: 12,
          border: "1px solid #ccc",
          borderRadius: 4,
        }}
      >
        <h2>Load Application Data</h2>
        <textarea
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          rows={10}
          style={{
            width: "100%",
            fontFamily: "monospace",
            fontSize: 12,
            whiteSpace: "pre",
          }}
        />
        <div style={{ marginTop: 8, marginBottom: 8 }}>
          <span>Load mode: </span>
          <label style={{ marginRight: 12 }}>
            <input
              type="radio"
              name="loadMode"
              value="append"
              checked={loadMode === "append"}
              onChange={() => setLoadMode("append")}
            />{" "}
            Append to existing applications
          </label>
          <label>
            <input
              type="radio"
              name="loadMode"
              value="replace"
              checked={loadMode === "replace"}
              onChange={() => setLoadMode("replace")}
            />{" "}
            Replace existing applications
          </label>
        </div>
        <button onClick={handleLoad}>Load applications from JSON</button>
      </section>

      {/* Display + Clear selected */}
      <section
        style={{
          padding: 12,
          border: "1px solid #ccc",
          borderRadius: 4,
        }}
      >
        <h2>Loaded Applications</h2>

        {/* Simple decision filter; you can extend to filter by sourceType if you like */}
        {/* For now, we'll just show all and let other tabs filter as needed */}

        <ApplicationSelector
          applications={applications}
          selectedIds={selectedIds}
          onSelectionChange={onSelectedIdsChange}
        />

        <div style={{ marginTop: 8 }}>
          <button
            onClick={handleClearSelected}
            disabled={selectedIds.length === 0}
          >
            Clear selected applications
          </button>
        </div>
      </section>
    </div>
  );
};
