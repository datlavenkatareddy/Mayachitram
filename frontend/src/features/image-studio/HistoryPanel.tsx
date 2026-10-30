import type { Asset } from "../../types/asset";
import type { OperationRecord } from "../../types/operation";

interface HistoryPanelProps {
  operations: OperationRecord[];
  assets: Asset[];
  onSelectAssetById: (assetId: string) => void;
  activeAssetId: string | null;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
  operations,
  assets,
  onSelectAssetById,
  activeAssetId,
}) => {
  return (
    <div className="history-panel" aria-label="Operation History">
      <div className="history-header">
        <span className="history-title">OPERATION HISTORY & VERSIONS ({operations.length})</span>
      </div>

      <div className="history-list">
        {operations.length === 0 ? (
          <p className="history-empty">No edits recorded yet. Edits produce non-destructive new versions.</p>
        ) : (
          operations.map((op) => {
            const outputAssetId = op.output_asset_ids[0];
            const outputAsset = assets.find((a) => a.id === outputAssetId);
            const isOutputActive = outputAssetId === activeAssetId;

            return (
              <div
                key={op.id}
                className={`history-card ${isOutputActive ? "active" : ""} ${op.status}`}
                onClick={() => {
                  if (outputAssetId) onSelectAssetById(outputAssetId);
                }}
              >
                <div className="history-card-header">
                  <span className="history-op-name">{op.tool_name}</span>
                  <span className={`status-badge ${op.status}`}>{op.status.toUpperCase()}</span>
                </div>

                <div className="history-card-body">
                  <small className="history-time">
                    {new Date(op.created_at).toLocaleTimeString()}
                  </small>
                  {outputAsset && (
                    <span className="history-output-link">
                      → {outputAsset.original_filename} ({outputAsset.width}×{outputAsset.height})
                    </span>
                  )}
                  {op.error && <p className="history-error">{op.error}</p>}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
