import { useState } from "react";
import { getAssetFileUrl } from "../../services/api";
import type { Asset } from "../../types/asset";

interface CanvasViewportProps {
  projectId: string;
  activeAsset: Asset | null;
  parentAsset: Asset | null;
  onDownload: () => void;
}

export const CanvasViewport: React.FC<CanvasViewportProps> = ({
  projectId,
  activeAsset,
  parentAsset,
  onDownload,
}) => {
  const [showOriginal, setShowOriginal] = useState(false);

  if (!activeAsset) {
    return (
      <div className="canvas-empty">
        <div className="canvas-empty-content">
          <span className="canvas-empty-glyph">◈</span>
          <h3>No Image Selected</h3>
          <p>Choose an asset from the project filmstrip or upload a photo to begin editing.</p>
        </div>
      </div>
    );
  }

  const activeUrl = getAssetFileUrl(projectId, activeAsset.id);
  const parentUrl = parentAsset ? getAssetFileUrl(projectId, parentAsset.id) : null;
  const displayedUrl = showOriginal && parentUrl ? parentUrl : activeUrl;
  const displayedAsset = showOriginal && parentAsset ? parentAsset : activeAsset;

  return (
    <section className="canvas-viewport" aria-label="Image Studio Canvas">
      <div className="canvas-toolbar">
        <div className="canvas-meta">
          <span className="canvas-filename">{displayedAsset.original_filename}</span>
          <span className="canvas-pill">{displayedAsset.width} × {displayedAsset.height} px</span>
          <span className="canvas-pill uppercase">{displayedAsset.media_type.split("/")[1] || "IMG"}</span>
          <span className="canvas-pill">{(displayedAsset.file_size / 1024).toFixed(1)} KB</span>
        </div>

        <div className="canvas-actions">
          {parentAsset && (
            <button
              type="button"
              className={`btn-compare ${showOriginal ? "active" : ""}`}
              onMouseDown={() => setShowOriginal(true)}
              onMouseUp={() => setShowOriginal(false)}
              onMouseLeave={() => setShowOriginal(false)}
              onClick={() => setShowOriginal((prev) => !prev)}
              title="Hold or click to compare with previous version"
            >
              {showOriginal ? "Showing Before" : "👁 Hold for Before"}
            </button>
          )}

          <button
            type="button"
            className="btn-download"
            onClick={onDownload}
            title="Download full resolution image"
          >
            ↓ Export / Download
          </button>
        </div>
      </div>

      <div className="canvas-stage">
        <div className="stage-frame">
          <img
            src={displayedUrl}
            alt={displayedAsset.original_filename}
            className="canvas-image"
          />
        </div>
      </div>
    </section>
  );
};
