import { useState } from "react";
import { executeTool, getAssetFileUrl } from "../../services/api";
import type { Asset } from "../../types/asset";
import type { OperationRecord } from "../../types/operation";
import { CanvasViewport } from "./CanvasViewport";
import { HistoryPanel } from "./HistoryPanel";
import { ToolPanel } from "./ToolPanel";

interface ImageStudioProps {
  projectId: string;
  activeAsset: Asset | null;
  parentAsset: Asset | null;
  assets: Asset[];
  operations: OperationRecord[];
  onAssetCreated: (newAsset: Asset) => void;
  onSelectAssetById: (assetId: string) => void;
}

export const ImageStudio: React.FC<ImageStudioProps> = ({
  projectId,
  activeAsset,
  parentAsset,
  assets,
  operations,
  onAssetCreated,
  onSelectAssetById,
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleApplyTool(toolName: string, parameters: Record<string, unknown>) {
    if (!activeAsset) return;
    setError(null);
    setIsProcessing(true);
    try {
      const result = await executeTool(projectId, toolName, parameters, activeAsset.id);
      if (result.output_asset) {
        onAssetCreated(result.output_asset);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to execute ${toolName}`);
    } finally {
      setIsProcessing(false);
    }
  }

  function handleDownload() {
    if (!activeAsset) return;
    const downloadUrl = getAssetFileUrl(projectId, activeAsset.id, true);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = activeAsset.original_filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  return (
    <div className="image-studio-layout">
      <div className="studio-main-col">
        <CanvasViewport
          projectId={projectId}
          activeAsset={activeAsset}
          parentAsset={parentAsset}
          onDownload={handleDownload}
        />
        <HistoryPanel
          operations={operations}
          assets={assets}
          onSelectAssetById={onSelectAssetById}
          activeAssetId={activeAsset?.id || null}
        />
      </div>

      <div className="studio-side-col">
        <ToolPanel
          activeAsset={activeAsset}
          onApplyTool={handleApplyTool}
          isProcessing={isProcessing}
          error={error}
        />
      </div>
    </div>
  );
};
