import React from "react";
import type { Workflow } from "../../types/maya";

interface WorkflowCardProps {
  workflow: Workflow;
  isExecuting: boolean;
  onExecute: (workflowId: string) => void;
  onCancel: (workflowId: string) => void;
  onSwitchToStudio?: () => void;
}

export const WorkflowCard: React.FC<WorkflowCardProps> = ({
  workflow,
  isExecuting,
  onExecute,
  onCancel,
  onSwitchToStudio,
}) => {
  const isAwaitingApproval = workflow.status === "awaiting_approval";
  const isDraft = workflow.status === "draft";
  const canRun = (isDraft || isAwaitingApproval) && !isExecuting;

  return (
    <div className="workflow-dag-card" aria-label="Creative Workflow Pipeline">
      <div className="workflow-dag-header">
        <div>
          <h4>{workflow.title}</h4>
          <span className="workflow-task-deps">{workflow.description}</span>
        </div>
        <span className={`workflow-status-badge ${workflow.status}`}>
          {workflow.status.replace("_", " ")}
        </span>
      </div>

      <div className="workflow-tasks-pipeline">
        {workflow.tasks.map((task, idx) => (
          <div key={task.task_id} className={`workflow-task-row ${task.status}`}>
            <span className="workflow-task-index">#{idx + 1}</span>
            <div className="workflow-task-info">
              <strong>{task.tool_name}</strong>
              <small>{task.description}</small>
              {task.dependencies.length > 0 && (
                <span className="workflow-task-deps">
                  Depends on: {task.dependencies.join(", ")}
                </span>
              )}
              {task.error && <p className="step-err" style={{ margin: "4px 0 0" }}>{task.error}</p>}
            </div>
            <span className="step-status-tag">{task.status}</span>
          </div>
        ))}
      </div>

      <div className="plan-actions" style={{ marginTop: "14px" }}>
        {canRun && (
          <button
            type="button"
            className="primary btn-execute-plan"
            onClick={() => onExecute(workflow.id)}
            disabled={isExecuting}
          >
            {isExecuting ? "Executing Pipeline…" : "Approve & Execute Workflow ↗"}
          </button>
        )}

        {workflow.status === "running" && (
          <button
            type="button"
            className="secondary"
            onClick={() => onCancel(workflow.id)}
          >
            Cancel Execution
          </button>
        )}

        {workflow.status === "completed" && onSwitchToStudio && (
          <button
            type="button"
            className="primary btn-view-in-studio"
            onClick={onSwitchToStudio}
          >
            Open in Image Studio ↗
          </button>
        )}
      </div>
    </div>
  );
};
