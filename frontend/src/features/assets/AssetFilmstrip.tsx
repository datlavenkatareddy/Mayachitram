import { useRef } from "react";
import type { ChangeEvent } from "react";
import { getAssetFileUrl } from "../../services/api";
import type { Asset } from "../../types/asset";

interface AssetFilmstripProps {
  projectId: string;
  assets: Asset[];
  activeAssetId: string | null;
  onSelectAsset: (asset: Asset) => void;
  onUploadFile: (file: File) => Promise<void>;
  onDeleteAsset: (assetId: string) => Promise<void>;
  isUploading: boolean;
}

export const AssetFilmstrip: React.FC<AssetFilmstripProps> = ({
  projectId,
  assets,
  activeAssetId,
  onSelectAsset,
  onUploadFile,
  onDeleteAsset,
  isUploading,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      onUploadFile(file);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <aside className="asset-filmstrip" aria-label="Project Assets">
      <div className="filmstrip-header">
        <span className="filmstrip-title">PROJECT ASSETS ({assets.length})</span>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden-input"
          onChange={handleFileChange}
        />
        <button
          className="btn-upload-strip"
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
          title="Upload new image"
        >
          {isUploading ? "Uploading…" : "+ Add Image"}
        </button>
      </div>

      <div className="filmstrip-list">
        {assets.length === 0 ? (
          <div className="filmstrip-empty" onClick={() => fileInputRef.current?.click()}>
            <span className="filmstrip-empty-icon">↑</span>
            <p>No assets in project</p>
            <small>Click to upload image</small>
          </div>
        ) : (
          assets.map((asset) => {
            const isActive = asset.id === activeAssetId;
            const isVersion = Boolean(asset.parent_asset_id);
            const thumbUrl = getAssetFileUrl(projectId, asset.id);

            return (
              <div
                key={asset.id}
                className={`filmstrip-item ${isActive ? "active" : ""}`}
                onClick={() => onSelectAsset(asset)}
              >
                <div className="thumb-wrapper">
                  <img src={thumbUrl} alt={asset.original_filename} loading="lazy" />
                  <span className={`asset-badge ${isVersion ? "version" : "original"}`}>
                    {isVersion ? "EDIT" : "ORIGINAL"}
                  </span>
                  <button
                    className="btn-delete-thumb"
                    title="Delete asset"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Delete "${asset.original_filename}"?`)) {
                        onDeleteAsset(asset.id);
                      }
                    }}
                  >
                    ×
                  </button>
                </div>
                <div className="thumb-info">
                  <span className="thumb-filename" title={asset.original_filename}>
                    {asset.original_filename}
                  </span>
                  <span className="thumb-dims">
                    {asset.width} × {asset.height}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
