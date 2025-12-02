// src/App.tsx
import React, { useEffect, useState } from "react";
import type {
  Application,
  DecisionProfile,
  RuleMinerResponse,
  ApplicationDecisionResult,
  SavedDecisionRun,
} from "./types/loanModels";
import { ApplicationSelector } from "./components/ApplicationSelector";
import { ApplicationsPage } from "./components/ApplicationsPage";
import { ProfileDetailsModal } from "./components/ProfileDetailsModal";
import { DecisionResultsViewer } from "./components/DecisionResultsViewer";

// TODO: import your existing ChatPage
// import { ChatPage } from "./ChatPage";

type Page = "chat" | "applications" | "ruleMiner" | "decisionEngine";

const LOCAL_STORAGE_KEYS = {
  applications: "loanApplications",
  profiles: "decisionProfiles",
  decisionRuns: "decisionRuns",
};

async function postJson<TReq, TRes>(
  url: string,
  body: TReq
): Promise<TRes> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed: ${res.status} ${text}`);
  }
  return (await res.json()) as TRes;
}

function App() {
  const [currentPage, setCurrentPage] = useState<Page>("applications");

  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedApplicationIds, setSelectedApplicationIds] = useState<string[]>(
    []
  );

  const [profiles, setProfiles] = useState<DecisionProfile[]>([]);
  const [selectedProfileIds, setSelectedProfileIds] = useState<string[]>([]);

  const [candidateProfile, setCandidateProfile] =
    useState<DecisionProfile | null>(null);

  // timestamp of last rule miner run (client-side)
  const [lastRuleMinerRunAt, setLastRuleMinerRunAt] =
    useState<string | null>(null);

  const [decisionResults, setDecisionResults] = useState<
    ApplicationDecisionResult[] | null
  >(null);

  const [savedDecisionRuns, setSavedDecisionRuns] = useState<
    SavedDecisionRun[]
  >([]);

  const [activeProfileDetails, setActiveProfileDetails] =
    useState<DecisionProfile | null>(null);

  const [activeDecisionRunId, setActiveDecisionRunId] =
    useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState<boolean>(false);

  // NEW: simple decision filter on Decision Engine tab
  type DecisionFilter = "all" | "undecisioned";
  const [decisionEngineFilter, setDecisionEngineFilter] =
    useState<DecisionFilter>("all");

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const storedApps = localStorage.getItem(
        LOCAL_STORAGE_KEYS.applications
      );
      if (storedApps) {
        setApplications(JSON.parse(storedApps));
      }

      const storedProfiles = localStorage.getItem(
        LOCAL_STORAGE_KEYS.profiles
      );
      if (storedProfiles) {
        setProfiles(JSON.parse(storedProfiles));
      }

      const storedRuns = localStorage.getItem(
        LOCAL_STORAGE_KEYS.decisionRuns
      );
      if (storedRuns) {
        setSavedDecisionRuns(JSON.parse(storedRuns));
      }
    } catch (e) {
      console.error("Failed to load from localStorage", e);
    }
  }, []);

  // Persist applications, profiles, decision runs
  useEffect(() => {
    try {
      localStorage.setItem(
        LOCAL_STORAGE_KEYS.applications,
        JSON.stringify(applications)
      );
    } catch (e) {
      console.error("Failed to save applications", e);
    }
  }, [applications]);

  useEffect(() => {
    try {
      localStorage.setItem(
        LOCAL_STORAGE_KEYS.decisionRuns,
        JSON.stringify(savedDecisionRuns)
      );
    } catch (e) {
      console.error("Failed to save decision runs", e);
    }
  }, [savedDecisionRuns]);

  // Helper: derive rules from candidateProfile
  const candidateRules = candidateProfile
    ? candidateProfile.rules.map((prc) => prc.rule)
    : [];

  // Rule Miner: run /api/rules/mine on selected apps (or all if none selected)
  const handleRunRuleMiner = async () => {
    setError(null);
    setIsBusy(true);
    try {
      const appsToUse =
        selectedApplicationIds.length > 0
          ? applications.filter((a) =>
              selectedApplicationIds.includes(a.application_id)
            )
          : applications;

      if (appsToUse.length === 0) {
        throw new Error("No applications available to mine rules from.");
      }

      const body = { applications: appsToUse };
      const resp = await postJson<typeof body, RuleMinerResponse>(
        "/api/rules/mine",
        body
      );

      // Attach client-only fields
      const savedAt = new Date().toISOString();
      const candidate: DecisionProfile = {
        ...resp.candidate_profile,
        _origin: "mined",
        _savedAt: undefined,
      };

      setCandidateProfile(candidate);
      setLastRuleMinerRunAt(new Date().toISOString());
      setDecisionResults(null);
      setActiveDecisionRunId(null);
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setIsBusy(false);
    }
  };

  // Save profile (from candidateProfile) into profiles state
  const saveCandidateProfile = (andGoToDecisionEngine: boolean) => {
    if (!candidateProfile) return;

    const id = candidateProfile.id || `profile-${Date.now()}`;
    const savedAt = new Date().toISOString();

    const profileToSave: DecisionProfile = {
      ...candidateProfile,
      id,
      _origin: candidateProfile._origin ?? "mined",
      _savedAt: savedAt,
    };

    setProfiles((prev) => {
      const others = prev.filter((p) => p.id !== id);
      return [...others, profileToSave];
    });

    // Keep candidateProfile visible with updated id/savedAt
    setCandidateProfile(profileToSave);

    // Optionally transition to decision engine
    if (andGoToDecisionEngine) {
      setSelectedProfileIds([id]);
      // Use source_application_ids from profile, if present
      if (profileToSave.source_application_ids?.length) {
        setSelectedApplicationIds(profileToSave.source_application_ids);
      }
      setCurrentPage("decisionEngine");
    }
  };

  // Run decision engine on selected apps + profiles
  const handleRunDecisionEngine = async () => {
    setError(null);
    setIsBusy(true);
    try {
      const appsToUse =
        selectedApplicationIds.length > 0
          ? applications.filter((a) =>
              selectedApplicationIds.includes(a.application_id)
            )
          : applications;

      if (appsToUse.length === 0) {
        throw new Error("No applications selected for decisioning.");
      }

      const profilesToUse = profiles.filter((p) =>
        selectedProfileIds.includes(p.id || "")
      );

      if (profilesToUse.length === 0) {
        throw new Error("No profiles selected for decisioning.");
      }

      const body = {
        applications: appsToUse,
        profiles: profilesToUse,
      };

      const resp = await postJson<typeof body, ApplicationDecisionResult[]>(
        "/api/rules/decide",
        body
      );

      setDecisionResults(resp);

      const runId = `run-${Date.now()}`;
      const runName = `Run ${new Date().toLocaleString()}`;
      const savedRun: SavedDecisionRun = {
        id: runId,
        name: runName,
        createdAt: new Date().toISOString(),
        applications: appsToUse,
        profiles: profilesToUse,
        results: resp,
      };

      setSavedDecisionRuns((prev) => [...prev, savedRun]);
      setActiveDecisionRunId(runId);
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setIsBusy(false);
    }
  };

  const activeDecisionRun = savedDecisionRuns.find(
    (r) => r.id === activeDecisionRunId
  );



  // Navigation UI
  const renderNav = () => (
    <div
      className="nav-bar"
      style={{ display: "flex", gap: 8, marginBottom: 12 }}
    >
      <button
        onClick={() => setCurrentPage("applications")}
        style={{
          padding: "6px 12px",
          fontWeight:
            currentPage === "applications" ? "bold" : "normal",
        }}
      >
        Applications
      </button>
      {/* <button
        onClick={() => setCurrentPage("chat")}
        style={{
          padding: "6px 12px",
          fontWeight: currentPage === "chat" ? "bold" : "normal",
        }}
      >
        Chat
      </button> */}
      <button
        onClick={() => setCurrentPage("ruleMiner")}
        style={{
          padding: "6px 12px",
          fontWeight:
            currentPage === "ruleMiner" ? "bold" : "normal",
        }}
      >
        Rule Miner
      </button>
      <button
        onClick={() => setCurrentPage("decisionEngine")}
        style={{
          padding: "6px 12px",
          fontWeight:
            currentPage === "decisionEngine" ? "bold" : "normal",
        }}
      >
        Decision Engine
      </button>
    </div>
  );

  // NEW: Applications page
  const renderApplicationsPage = () => (
    <ApplicationsPage
      applications={applications}
      onApplicationsChange={setApplications}
      selectedIds={selectedApplicationIds}
      onSelectedIdsChange={setSelectedApplicationIds}
    />
  );

  // Rule Miner page
  const renderRuleMinerPage = () => {
    const statsApps =
      selectedApplicationIds.length > 0
        ? applications.filter((a) =>
            selectedApplicationIds.includes(a.application_id)
          )
        : applications;

    const appsUsedCount = candidateProfile?.source_application_ids?.length ?? 0;
    const rulesCount = candidateProfile?.rules?.length ?? 0;
    // human-friendly timestamp (prefer lastRuleMinerRunAt, fallback to profile.created_at if present)
    const generatedAtDisplay = (() => {
      const iso =
        lastRuleMinerRunAt ??
        (candidateProfile as any)?.created_at ??
        null;
      if (!iso) return null;
      try {
        return new Date(iso).toLocaleString();
      } catch {
        return iso;
      }
    })();
  
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div
          style={{
            padding: 12,
            border: "1px solid #ccc",
            borderRadius: 4,
          }}
        >
          <h2>Dataset</h2>

          <ApplicationSelector
            applications={applications}
            selectedIds={selectedApplicationIds}
            onSelectionChange={setSelectedApplicationIds}
          />

          <div style={{ marginTop: 8, fontSize: 12, color: "#555" }}>
            Stats based on{" "}
            {statsApps.length === applications.length
              ? "all applications"
              : "selected applications"}
            :{" "}
            {statsApps.length === 0
              ? "none"
              : `${statsApps.length} apps (approx ${Math.round(
                  (100 *
                    statsApps.filter((a) => a.final_decision === "approve")
                      .length) /
                    statsApps.length
                )}% approved, ${Math.round(
                  (100 *
                    statsApps.filter((a) => a.final_decision === "decline")
                      .length) /
                    statsApps.length
                )}% declined)`}
          </div>
        </div>

        <div
          style={{
            padding: 12,
            border: "1px solid #ccc",
            borderRadius: 4,
          }}
        >
          <h2>Rule Miner</h2>
          <div style={{ marginBottom: 8, display: "flex", gap: 8 }}>
            <button onClick={handleRunRuleMiner} disabled={isBusy}>
              {isBusy ? "Mining rules..." : "Run Rule Miner"}
            </button>
          </div>

          {candidateProfile && (
            <div style={{ marginTop: 12, borderTop: "1px solid #eee", paddingTop: 8 }}>
              <h3>Candidate Profile 
                {!candidateProfile._savedAt && (
                  <span>
                    (not yet saved)
                  </span>
                )}
                </h3>

              {candidateProfile ? (
                <div
                  style={{
                    fontSize: 12,
                    color: "#555",
                    marginBottom: 8,
                    padding: "6px 8px",
                    backgroundColor: "#f7f7f7",
                    borderRadius: 4,
                  }}
                >
                  <div>
                    <strong>Profile name:</strong>{" "}
                    {candidateProfile.name || "(unnamed)"}
                  </div>
                  {generatedAtDisplay && (
                    <div>
                      <strong>Generated:</strong> {generatedAtDisplay}
                    </div>
                  )}
                  <div>
                    <strong>Applications analyzed:</strong>{" "}
                    {appsUsedCount > 0
                      ? appsUsedCount
                      : selectedApplicationIds.length}
                  </div>
                  <div>
                    <strong>Rules:</strong> {rulesCount}
                  </div>
                </div>
              ) : (
                <div
                  style={{
                    fontSize: 12,
                    color: "#777",
                    marginBottom: 8,
                  }}
                >
                  Run the rule miner to generate a candidate profile from the
                  selected applications.
                </div>
              )}    

              <div style={{ marginBottom: 8 }}>
                <button
                  onClick={() => saveCandidateProfile(false)}
                  style={{ marginRight: 8 }}
                >
                  Save profile
                </button>
                <button
                  onClick={() => saveCandidateProfile(true)}
                  style={{ marginRight: 8 }}
                >
                  Save &amp; Validate
                </button>
                {candidateProfile._savedAt && (
                  <span style={{ fontSize: 12, color: "#555" }}>
                    Saved at: {candidateProfile._savedAt}
                  </span>
                )}
              </div>

              <button
                onClick={() => setActiveProfileDetails(candidateProfile)}
                style={{ marginBottom: 8 }}
              >
                View profile details
              </button>

              {/* You can also render a compact inline summary here if desired */}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Adjusted Decision Engine page with a simple filter for undecisioned
  const renderDecisionEnginePage = () => {
    const profilesToShow = profiles;

    const appsForSelector =
      decisionEngineFilter === "undecisioned"
        ? applications.filter((a) => !a.final_decision)
        : applications;

    const activeDecisionRun = savedDecisionRuns.find(
      (r) => r.id === activeDecisionRunId
    );

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Profiles selector */}
        <div
          style={{
            padding: 12,
            border: "1px solid #ccc",
            borderRadius: 4,
          }}
        >
          <h2>Profiles</h2>
          {profilesToShow.length === 0 ? (
            <div>No saved profiles yet.</div>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {profilesToShow.map((p) => {
                const id = p.id || "";
                const isSelected = selectedProfileIds.includes(id);
                const ruleCount = p.rules.length;
                const savedAtLabel = p._savedAt
                  ? new Date(p._savedAt).toLocaleString()
                  : p.created_at
                  ? new Date(p.created_at).toLocaleString()
                  : "unknown";

                return (
                  <li
                    key={id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      padding: "4px 0",
                      borderBottom: "1px solid #eee",
                    }}
                  >
                    <div
                      style={{ flex: 1, cursor: "pointer" }}
                      onClick={() => {
                        setSelectedProfileIds((prev) =>
                          isSelected
                            ? prev.filter((x) => x !== id)
                            : [...prev, id]
                        );
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        readOnly
                        style={{ marginRight: 8 }}
                      />
                      <strong>{p.name}</strong>{" "}
                      <span style={{ fontSize: 12, color: "#666" }}>
                        ({ruleCount} rule{ruleCount === 1 ? "" : "s"},{" "}
                        {p.source_application_ids.length} source apps, saved{" "}
                        {savedAtLabel})
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        onClick={() => setActiveProfileDetails(p)}
                        style={{ fontSize: 12 }}
                      >
                        View details
                      </button>
                      <button
                        onClick={() =>
                          setSelectedApplicationIds(p.source_application_ids)
                        }
                        style={{ fontSize: 12 }}
                      >
                        Use source apps
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Applications selector with filter */}
        <div
          style={{
            padding: 12,
            border: "1px solid #ccc",
            borderRadius: 4,
          }}
        >
          <h2>Applications</h2>
          <div style={{ marginBottom: 8, fontSize: 12 }}>
            <span>Filter: </span>
            <label style={{ marginRight: 12 }}>
              <input
                type="radio"
                name="decEngineFilter"
                value="all"
                checked={decisionEngineFilter === "all"}
                onChange={() => setDecisionEngineFilter("all")}
              />{" "}
              All applications
            </label>
            <label>
              <input
                type="radio"
                name="decEngineFilter"
                value="undecisioned"
                checked={decisionEngineFilter === "undecisioned"}
                onChange={() =>
                  setDecisionEngineFilter("undecisioned")
                }
              />{" "}
              Undecisioned only
            </label>
          </div>
          <ApplicationSelector
            applications={appsForSelector}
            selectedIds={selectedApplicationIds}
            onSelectionChange={setSelectedApplicationIds}
          />
        </div>

        {/* Run decision + results */}
        <div
          style={{
            padding: 12,
            border: "1px solid #ccc",
            borderRadius: 4,
          }}
        >
          <h2>Decision Engine</h2>
          <div style={{ marginBottom: 8, display: "flex", gap: 8 }}>
            <button onClick={handleRunDecisionEngine} disabled={isBusy}>
              {isBusy ? "Running..." : "Run Decision Engine"}
            </button>

            {/* Saved decision runs selector */}
            {savedDecisionRuns.length > 0 && (
              <select
                value={activeDecisionRunId ?? ""}
                onChange={(e) =>
                  setActiveDecisionRunId(
                    e.target.value || null
                  )
                }
              >
                <option value="">Select prior run...</option>
                {savedDecisionRuns.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {activeDecisionRun && (
            <DecisionResultsViewer run={activeDecisionRun} />
          )}

          {!activeDecisionRun && decisionResults && (
            <DecisionResultsViewer
              run={{
                id: "latest",
                name: "Latest run (unsaved)",
                createdAt: new Date().toISOString(),
                applications,
                profiles: profiles.filter((p) =>
                  selectedProfileIds.includes(p.id || "")
                ),
                results: decisionResults,
              }}
            />
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: 16 }}>
      {renderNav()}

      {error && (
        <div style={{ marginBottom: 8, color: "red" }}>
          Error: {error}
        </div>
      )}

      {currentPage === "applications" && renderApplicationsPage()}
      {currentPage === "chat" && (
        <div>
          <p>Chat page placeholder (wire your existing chat here).</p>
        </div>
      )}
      {currentPage === "ruleMiner" && renderRuleMinerPage()}
      {currentPage === "decisionEngine" && renderDecisionEnginePage()}

      {/* Shared profile details modal */}
      {activeProfileDetails && (
        <ProfileDetailsModal
          profile={activeProfileDetails}
          onClose={() => setActiveProfileDetails(null)}
        />
      )}
    </div>
  );
}

export default App;
