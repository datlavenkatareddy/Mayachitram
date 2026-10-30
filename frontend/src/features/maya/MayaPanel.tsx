import React, { useEffect, useState } from "react";
import {
  applyRecommendation,
  cancelWorkflow,
  chatWithMaya,
  createMayaPlan,
  executeMayaPlan,
  executeWorkflow,
  getProjectPreferences,
  getRecommendations,
  updateProjectPreferences,
} from "../../services/api";
import type { Asset } from "../../types/asset";
import type {
  ConversationMessage,
  CreativeRecommendation,
  ExecutionMode,
  PlanExecutionResult,
  PlanResponse,
  ProjectPreferences,
  Workflow,
} from "../../types/maya";
import { PreferencesDrawer } from "./PreferencesDrawer";
import { RecommendationsShelf } from "./RecommendationsShelf";
import { WorkflowCard } from "./WorkflowCard";

interface MayaPanelProps {
  projectId: string;
  activeAsset: Asset | null;
  onPlanExecuted?: (result: PlanExecutionResult) => void;
  onWorkflowExecuted?: (workflow: Workflow) => void;
  onSwitchToStudio: () => void;
}

const SAMPLE_PROMPTS = [
  "Make a 1:1 square version of this image",
  "Resize to 1080x1350 for an Instagram portrait post",
  "Rotate 90 degrees clockwise",
  "Convert this to WebP format with high quality",
  "Increase brightness slightly and boost contrast",
  "Convert to black and white",
  "Warm up the color temperature",
];

export const MayaPanel: React.FC<MayaPanelProps> = ({
  projectId,
  activeAsset,
  onPlanExecuted,
  onWorkflowExecuted,
  onSwitchToStudio,
}) => {
  const [prompt, setPrompt] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("execute");

  const [isPlanning, setIsPlanning] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [executionResult, setExecutionResult] = useState<PlanExecutionResult | null>(null);
  const [activeWorkflow, setActiveWorkflow] = useState<Workflow | null>(null);
  const [recommendations, setRecommendations] = useState<CreativeRecommendation[]>([]);
  const [preferences, setPreferences] = useState<ProjectPreferences | null>(null);
  const [showPreferences, setShowPreferences] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load preferences and initial recommendations
  useEffect(() => {
    let isMounted = true;
    async function loadInitialData() {
      try {
        const [prefs, recs] = await Promise.all([
          getProjectPreferences(projectId).catch(() => null),
          getRecommendations(projectId, activeAsset?.id).catch(() => []),
        ]);
        if (isMounted) {
          if (prefs) {
            setPreferences(prefs);
            setExecutionMode(prefs.default_execution_mode || "execute");
          }
          setRecommendations(recs);
        }
      } catch {
        // Non-blocking
      }
    }
    loadInitialData();
    return () => {
      isMounted = false;
    };
  }, [projectId, activeAsset?.id]);

  // Handle Conversational Message Submission
  async function handleSendMessage(instruction?: string) {
    const text = instruction || prompt;
    if (!text.trim()) return;
    setError(null);
    setIsPlanning(true);
    setExecutionResult(null);

    try {
      const response = await chatWithMaya(
        projectId,
        text.trim(),
        activeAsset?.id,
        conversationId,
        executionMode
      );
      setConversationId(response.conversation_id);
      setMessages((prev) => [...prev, response.user_message, response.assistant_message]);
      if (response.recommendations?.length > 0) {
        setRecommendations(response.recommendations);
      }
      if (response.workflow) {
        setActiveWorkflow(response.workflow);
        // If mode is autonomous, auto-execute eligible workflow
        if (executionMode === "autonomous") {
          handleExecuteWorkflow(response.workflow.id);
        }
      }
      setPrompt("");
    } catch {
      // Fallback to legacy single plan endpoint if chat fails
      try {
        const fallbackPlan = await createMayaPlan(projectId, text.trim(), activeAsset?.id);
        setPlan(fallbackPlan);
        if (instruction) setPrompt(instruction);
      } catch (err2) {
        setError(err2 instanceof Error ? err2.message : "Failed to process request with Maya.");
      }
    } finally {
      setIsPlanning(false);
    }
  }

  // Handle Workflow Execution
  async function handleExecuteWorkflow(workflowId: string) {
    setError(null);
    setIsExecuting(true);
    try {
      const resultWorkflow = await executeWorkflow(workflowId, activeAsset?.id, ["__ALL__"]);
      setActiveWorkflow(resultWorkflow);
      if (onWorkflowExecuted) {
        onWorkflowExecuted(resultWorkflow);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to execute workflow.");
    } finally {
      setIsExecuting(false);
    }
  }

  // Handle Workflow Cancellation
  async function handleCancelWorkflow(workflowId: string) {
    try {
      const cancelled = await cancelWorkflow(workflowId);
      setActiveWorkflow(cancelled);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel workflow.");
    }
  }

  // Handle Applying a Creative Recommendation
  async function handleApplyRecommendation(rec: CreativeRecommendation) {
    if (!activeAsset) {
      setError("Please select or upload an active asset before applying a recommendation.");
      return;
    }
    setError(null);
    setIsPlanning(true);
    try {
      const generatedWf = await applyRecommendation(projectId, rec.id, activeAsset.id);
      setActiveWorkflow(generatedWf);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to apply recommendation.");
    } finally {
      setIsPlanning(false);
    }
  }

  // Handle Legacy Single Plan Execution
  async function handleExecutePlan() {
    if (!plan) return;
    setError(null);
    setIsExecuting(true);
    try {
      const result = await executeMayaPlan(projectId, plan, activeAsset?.id);
      setExecutionResult(result);
      if (onPlanExecuted) {
        onPlanExecuted(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to execute plan.");
    } finally {
      setIsExecuting(false);
    }
  }

  return (
    <section className="maya-workspace" aria-label="Maya AI Creative Assistant">
      <div className="maya-header">
        <div className="maya-title-area">
          <h2>Maya Creative Assistant</h2>
          <p className="muted">
            Unified agentic creative intelligence. Maya recommends, plans, and executes verified workflows across your project assets.
          </p>
        </div>
        <div className="maya-context-badge">
          <span>ACTIVE CONTEXT:</span>
          <strong>{activeAsset ? activeAsset.original_filename : "No asset selected"}</strong>
          {activeAsset && <small>({activeAsset.width}×{activeAsset.height})</small>}
        </div>
      </div>

      {/* Mode Controls & Brand Preferences Toggle */}
      <div className="maya-top-bar-controls">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "10px", fontFamily: "var(--mono)", color: "#8c8d97" }}>MODE:</span>
          <div className="mode-selector" role="radiogroup" aria-label="Execution Mode">
            {(["assist", "execute", "autonomous"] as ExecutionMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                className={`mode-btn ${executionMode === mode ? "active" : ""}`}
                onClick={() => setExecutionMode(mode)}
                title={
                  mode === "assist"
                    ? "Assist: Recommends & prepares actions without executing."
                    : mode === "execute"
                    ? "Execute: Generates verified plan with explicit user approval."
                    : "Autonomous: Executes eligible workflows automatically within safety bounds."
                }
              >
                {mode.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          className="btn-prefs-toggle"
          onClick={() => setShowPreferences(!showPreferences)}
        >
          ⚙ Brand Preferences {preferences?.brand_colors?.length ? `(${preferences.brand_colors.length} swatches)` : ""}
        </button>
      </div>

      {/* Brand Preferences Drawer */}
      {showPreferences && preferences && (
        <PreferencesDrawer
          preferences={preferences}
          onSave={async (updated) => {
            const saved = await updateProjectPreferences(projectId, updated);
            setPreferences(saved);
          }}
          onClose={() => setShowPreferences(false)}
        />
      )}

      {/* Creative Recommendations Shelf */}
      <RecommendationsShelf
        recommendations={recommendations}
        onApply={handleApplyRecommendation}
        isLoading={isPlanning || isExecuting}
      />

      <div className="maya-chat-area">
        {/* Multi-turn Chat Stream */}
        {messages.length > 0 && (
          <div className="chat-stream" aria-label="Conversation History">
            {messages.map((msg) => (
              <div key={msg.id} className={`chat-bubble ${msg.role}`}>
                <div className="chat-bubble-meta">
                  <span className="role-tag">{msg.role === "user" ? "YOU" : "MAYA"}</span>
                  <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
                <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
              </div>
            ))}
          </div>
        )}

        {/* Input Card */}
        <div className="maya-input-card">
          <label htmlFor="maya-prompt" className="sr-only">Instructions for Maya</label>
          <div className="input-with-button">
            <input
              id="maya-prompt"
              type="text"
              className="maya-text-input"
              placeholder="e.g. Make a 1:1 square crop, resize to 1080x1350, or convert to WebP…"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              disabled={isPlanning || isExecuting}
            />
            <button
              className="primary btn-plan"
              onClick={() => handleSendMessage()}
              disabled={!prompt.trim() || isPlanning || isExecuting}
            >
              {isPlanning ? "Planning…" : "Plan with Maya ↗"}
            </button>
          </div>

          <div className="sample-chips">
            <span className="chips-label">Quick Ideas:</span>
            {SAMPLE_PROMPTS.map((sample) => (
              <button
                key={sample}
                type="button"
                className="chip-prompt"
                disabled={isPlanning || isExecuting}
                onClick={() => handleSendMessage(sample)}
              >
                {sample}
              </button>
            ))}
          </div>
        </div>

        {error && <div className="maya-error" role="alert">{error}</div>}

        {/* Active DAG Workflow Card */}
        {activeWorkflow && (
          <WorkflowCard
            workflow={activeWorkflow}
            isExecuting={isExecuting}
            onExecute={handleExecuteWorkflow}
            onCancel={handleCancelWorkflow}
            onSwitchToStudio={onSwitchToStudio}
          />
        )}

        {/* Legacy Single Plan Preview Card (if generated via fallback) */}
        {plan && !activeWorkflow && (
          <div className="plan-card" aria-live="polite">
            <div className="plan-card-header">
              <span className="plan-badge">PROPOSED CREATIVE PLAN</span>
              <h4>{plan.summary}</h4>
            </div>

            {plan.missing_information && (
              <div className="plan-warning">
                ⓘ {plan.missing_information}
              </div>
            )}

            <div className="plan-steps-list">
              {plan.steps.map((step) => (
                <div key={step.step_id} className="plan-step-item">
                  <span className="step-num">{step.step_id}</span>
                  <div className="step-details">
                    <strong className="step-tool">{step.tool_name}</strong>
                    <p className="step-rationale">{step.rationale}</p>
                    <code className="step-params">
                      {JSON.stringify(step.parameters)}
                    </code>
                  </div>
                </div>
              ))}
            </div>

            <div className="plan-actions">
              <button
                className="secondary"
                onClick={() => setPlan(null)}
                disabled={isExecuting}
              >
                Discard Plan
              </button>
              <button
                className="primary btn-execute-plan"
                onClick={handleExecutePlan}
                disabled={!plan.can_execute || isExecuting}
              >
                {isExecuting ? "Executing Plan…" : "Approve & Execute Plan"}
              </button>
            </div>
          </div>
        )}

        {/* Legacy Execution Result Card */}
        {executionResult && (
          <div className={`execution-card ${executionResult.status}`} aria-live="polite">
            <div className="execution-header">
              <span className={`status-pill ${executionResult.status}`}>
                {executionResult.status.toUpperCase()}
              </span>
              <h4>{executionResult.summary_message}</h4>
            </div>

            <div className="step-results-list">
              {executionResult.steps.map((step) => (
                <div key={step.step_id} className={`step-result-item ${step.status}`}>
                  <span>Step {step.step_id}: {step.tool_name}</span>
                  <span className="step-status-tag">{step.status}</span>
                  {step.error && <p className="step-err">{step.error}</p>}
                </div>
              ))}
            </div>

            {executionResult.final_asset && (
              <div className="final-asset-callout">
                <p>
                  New Version Generated: <strong>{executionResult.final_asset.original_filename}</strong> ({executionResult.final_asset.width} × {executionResult.final_asset.height} px)
                </p>
                <button
                  type="button"
                  className="primary btn-view-in-studio"
                  onClick={onSwitchToStudio}
                >
                  Open in Image Studio ↗
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};
