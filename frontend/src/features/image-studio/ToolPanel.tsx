import { useEffect, useState } from "react";
import type { Asset } from "../../types/asset";

interface ToolPanelProps {
  activeAsset: Asset | null;
  onApplyTool: (toolName: string, parameters: Record<string, unknown>) => Promise<void>;
  isProcessing: boolean;
  error: string | null;
}

type TabType = "transform" | "crop" | "color" | "format";

export const ToolPanel: React.FC<ToolPanelProps> = ({
  activeAsset,
  onApplyTool,
  isProcessing,
  error,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>("transform");

  // Resize State
  const [resizeWidth, setResizeWidth] = useState<number>(1080);
  const [resizeHeight, setResizeHeight] = useState<number>(1080);
  const [preserveAspect, setPreserveAspect] = useState<boolean>(true);
  const [fitMode, setFitMode] = useState<"contain" | "cover" | "stretch">("contain");

  // Crop State
  const [cropLeft, setCropLeft] = useState<number>(0);
  const [cropTop, setCropTop] = useState<number>(0);
  const [cropWidth, setCropWidth] = useState<number>(800);
  const [cropHeight, setCropHeight] = useState<number>(800);

  // Color State
  const [brightness, setBrightness] = useState<number>(1.0);
  const [contrast, setContrast] = useState<number>(1.0);
  const [saturation, setSaturation] = useState<number>(1.0);
  const [temperature, setTemperature] = useState<number>(0);

  // Format State
  const [targetFormat, setTargetFormat] = useState<"WEBP" | "JPEG" | "PNG">("WEBP");
  const [quality, setQuality] = useState<number>(85);

  // Sync defaults when active asset changes
  useEffect(() => {
    if (activeAsset) {
      setResizeWidth(activeAsset.width);
      setResizeHeight(activeAsset.height);
      const minDim = Math.min(activeAsset.width, activeAsset.height);
      setCropLeft(Math.max(0, Math.floor((activeAsset.width - minDim) / 2)));
      setCropTop(Math.max(0, Math.floor((activeAsset.height - minDim) / 2)));
      setCropWidth(minDim);
      setCropHeight(minDim);
      setBrightness(1.0);
      setContrast(1.0);
      setSaturation(1.0);
      setTemperature(0);
    }
  }, [activeAsset?.id, activeAsset?.width, activeAsset?.height]);

  function handleResizePreset(ratio: "1:1" | "4:5" | "16:9" | "9:16") {
    if (!activeAsset) return;
    const w = activeAsset.width;
    if (ratio === "1:1") {
      const dim = Math.min(w, activeAsset.height);
      setResizeWidth(dim);
      setResizeHeight(dim);
    } else if (ratio === "4:5") {
      setResizeWidth(1080);
      setResizeHeight(1350);
      setFitMode("cover");
    } else if (ratio === "16:9") {
      setResizeWidth(1920);
      setResizeHeight(1080);
      setFitMode("contain");
    } else if (ratio === "9:16") {
      setResizeWidth(1080);
      setResizeHeight(1920);
      setFitMode("contain");
    }
  }

  function handleSquareCropPreset() {
    if (!activeAsset) return;
    const minDim = Math.min(activeAsset.width, activeAsset.height);
    const left = Math.floor((activeAsset.width - minDim) / 2);
    const top = Math.floor((activeAsset.height - minDim) / 2);
    setCropLeft(left);
    setCropTop(top);
    setCropWidth(minDim);
    setCropHeight(minDim);
  }

  if (!activeAsset) {
    return (
      <aside className="tool-panel empty">
        <p className="muted text-center">Select an asset to view creative tools.</p>
      </aside>
    );
  }

  return (
    <aside className="tool-panel" aria-label="Creative Tools Panel">
      <div className="tool-tabs">
        <button
          className={`tab-btn ${activeTab === "transform" ? "active" : ""}`}
          onClick={() => setActiveTab("transform")}
        >
          Transform
        </button>
        <button
          className={`tab-btn ${activeTab === "crop" ? "active" : ""}`}
          onClick={() => setActiveTab("crop")}
        >
          Crop
        </button>
        <button
          className={`tab-btn ${activeTab === "color" ? "active" : ""}`}
          onClick={() => setActiveTab("color")}
        >
          Color & Light
        </button>
        <button
          className={`tab-btn ${activeTab === "format" ? "active" : ""}`}
          onClick={() => setActiveTab("format")}
        >
          Export
        </button>
      </div>

      {error && <div className="tool-error" role="alert">{error}</div>}

      <div className="tool-tab-content">
        {/* --- TAB 1: TRANSFORM & RESIZE --- */}
        {activeTab === "transform" && (
          <div className="tool-section">
            <div className="section-title">Resize & Scaling</div>

            <div className="preset-chips">
              <span className="preset-label">Presets:</span>
              <button type="button" className="chip" onClick={() => handleResizePreset("1:1")}>1:1 Square</button>
              <button type="button" className="chip" onClick={() => handleResizePreset("4:5")}>4:5 Portrait</button>
              <button type="button" className="chip" onClick={() => handleResizePreset("16:9")}>16:9 Landscape</button>
              <button type="button" className="chip" onClick={() => handleResizePreset("9:16")}>9:16 Story</button>
            </div>

            <div className="dims-row">
              <div className="field">
                <label htmlFor="resize-width">Width (px)</label>
                <input
                  id="resize-width"
                  type="number"
                  className="num-input"
                  min={1}
                  max={8192}
                  value={resizeWidth}
                  onChange={(e) => setResizeWidth(parseInt(e.target.value, 10) || 1)}
                />
              </div>
              <div className="field">
                <label htmlFor="resize-height">Height (px)</label>
                <input
                  id="resize-height"
                  type="number"
                  className="num-input"
                  min={1}
                  max={8192}
                  value={resizeHeight}
                  onChange={(e) => setResizeHeight(parseInt(e.target.value, 10) || 1)}
                />
              </div>
            </div>

            <div className="toggle-row">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={preserveAspect}
                  onChange={(e) => setPreserveAspect(e.target.checked)}
                />
                Preserve Aspect Ratio
              </label>

              {preserveAspect && (
                <div className="fit-selector">
                  <label htmlFor="fit-mode">Fit Mode:</label>
                  <select
                    id="fit-mode"
                    className="select-input"
                    value={fitMode}
                    onChange={(e) => setFitMode(e.target.value as "contain" | "cover" | "stretch")}
                  >
                    <option value="contain">Contain (Fit)</option>
                    <option value="cover">Cover (Fill & Crop)</option>
                    <option value="stretch">Stretch</option>
                  </select>
                </div>
              )}
            </div>

            <button
              type="button"
              className="btn-apply"
              disabled={isProcessing}
              onClick={() => onApplyTool("image.resize", {
                width: resizeWidth,
                height: resizeHeight,
                preserve_aspect: preserveAspect,
                fit_mode: fitMode,
              })}
            >
              {isProcessing ? "Applying Resize…" : "Apply Resize"}
            </button>

            <div className="divider-h" />

            <div className="section-title">Rotation & Orientation</div>
            <div className="btn-group-grid">
              <button
                type="button"
                className="action-btn"
                disabled={isProcessing}
                onClick={() => onApplyTool("image.rotate", { degrees: 90, expand: true })}
              >
                ↻ 90° Clockwise
              </button>
              <button
                type="button"
                className="action-btn"
                disabled={isProcessing}
                onClick={() => onApplyTool("image.rotate", { degrees: 180, expand: true })}
              >
                ↻ 180° Flip
              </button>
              <button
                type="button"
                className="action-btn"
                disabled={isProcessing}
                onClick={() => onApplyTool("image.flip", { horizontal: true, vertical: false })}
              >
                ⇄ Flip Horizontal
              </button>
              <button
                type="button"
                className="action-btn"
                disabled={isProcessing}
                onClick={() => onApplyTool("image.flip", { horizontal: false, vertical: true })}
              >
                ⇅ Flip Vertical
              </button>
            </div>
          </div>
        )}

        {/* --- TAB 2: CROP --- */}
        {activeTab === "crop" && (
          <div className="tool-section">
            <div className="section-title">Crop Image Bounds</div>

            <div className="preset-chips">
              <span className="preset-label">Presets:</span>
              <button type="button" className="chip" onClick={handleSquareCropPreset}>Centered 1:1 Square</button>
            </div>

            <div className="grid-2x2">
              <div className="field">
                <label htmlFor="crop-left">Left Offset (px)</label>
                <input
                  id="crop-left"
                  type="number"
                  className="num-input"
                  min={0}
                  max={activeAsset.width - 1}
                  value={cropLeft}
                  onChange={(e) => setCropLeft(Math.max(0, parseInt(e.target.value, 10) || 0))}
                />
              </div>
              <div className="field">
                <label htmlFor="crop-top">Top Offset (px)</label>
                <input
                  id="crop-top"
                  type="number"
                  className="num-input"
                  min={0}
                  max={activeAsset.height - 1}
                  value={cropTop}
                  onChange={(e) => setCropTop(Math.max(0, parseInt(e.target.value, 10) || 0))}
                />
              </div>
              <div className="field">
                <label htmlFor="crop-width">Crop Width (px)</label>
                <input
                  id="crop-width"
                  type="number"
                  className="num-input"
                  min={1}
                  max={activeAsset.width - cropLeft}
                  value={cropWidth}
                  onChange={(e) => setCropWidth(Math.max(1, parseInt(e.target.value, 10) || 1))}
                />
              </div>
              <div className="field">
                <label htmlFor="crop-height">Crop Height (px)</label>
                <input
                  id="crop-height"
                  type="number"
                  className="num-input"
                  min={1}
                  max={activeAsset.height - cropTop}
                  value={cropHeight}
                  onChange={(e) => setCropHeight(Math.max(1, parseInt(e.target.value, 10) || 1))}
                />
              </div>
            </div>

            <button
              type="button"
              className="btn-apply"
              disabled={isProcessing}
              onClick={() => onApplyTool("image.crop", {
                left: cropLeft,
                top: cropTop,
                width: cropWidth,
                height: cropHeight,
              })}
            >
              {isProcessing ? "Cropping…" : "Apply Crop"}
            </button>
          </div>
        )}

        {/* --- TAB 3: COLOR & LIGHT --- */}
        {activeTab === "color" && (
          <div className="tool-section">
            <div className="section-title">Color & Tonal Balance</div>

            <div className="slider-group">
              <div className="slider-header">
                <label htmlFor="brightness-slider">Brightness</label>
                <span className="slider-val">{brightness.toFixed(2)}x</span>
              </div>
              <input
                id="brightness-slider"
                type="range"
                min={0.2}
                max={2.5}
                step={0.05}
                value={brightness}
                onChange={(e) => setBrightness(parseFloat(e.target.value))}
              />
              <button
                type="button"
                className="btn-apply-slider"
                disabled={isProcessing || brightness === 1.0}
                onClick={() => onApplyTool("image.adjust_brightness", { factor: brightness })}
              >
                Apply Brightness
              </button>
            </div>

            <div className="slider-group">
              <div className="slider-header">
                <label htmlFor="contrast-slider">Contrast</label>
                <span className="slider-val">{contrast.toFixed(2)}x</span>
              </div>
              <input
                id="contrast-slider"
                type="range"
                min={0.2}
                max={2.5}
                step={0.05}
                value={contrast}
                onChange={(e) => setContrast(parseFloat(e.target.value))}
              />
              <button
                type="button"
                className="btn-apply-slider"
                disabled={isProcessing || contrast === 1.0}
                onClick={() => onApplyTool("image.adjust_contrast", { factor: contrast })}
              >
                Apply Contrast
              </button>
            </div>

            <div className="slider-group">
              <div className="slider-header">
                <label htmlFor="saturation-slider">Saturation</label>
                <span className="slider-val">{saturation === 0 ? "Grayscale" : `${saturation.toFixed(2)}x`}</span>
              </div>
              <input
                id="saturation-slider"
                type="range"
                min={0.0}
                max={2.5}
                step={0.05}
                value={saturation}
                onChange={(e) => setSaturation(parseFloat(e.target.value))}
              />
              <div className="button-subrow">
                <button
                  type="button"
                  className="chip-btn"
                  onClick={() => setSaturation(0.0)}
                >
                  Set Grayscale
                </button>
                <button
                  type="button"
                  className="btn-apply-slider"
                  disabled={isProcessing || saturation === 1.0}
                  onClick={() => onApplyTool("image.adjust_saturation", { factor: saturation })}
                >
                  Apply Saturation
                </button>
              </div>
            </div>

            <div className="slider-group">
              <div className="slider-header">
                <label htmlFor="temp-slider">Color Temperature</label>
                <span className="slider-val">{temperature > 0 ? `+${temperature} Warm` : temperature < 0 ? `${temperature} Cool` : "Neutral"}</span>
              </div>
              <input
                id="temp-slider"
                type="range"
                min={-100}
                max={100}
                step={5}
                value={temperature}
                onChange={(e) => setTemperature(parseInt(e.target.value, 10))}
              />
              <button
                type="button"
                className="btn-apply-slider"
                disabled={isProcessing || temperature === 0}
                onClick={() => onApplyTool("image.adjust_temperature", { shift: temperature })}
              >
                Apply Temperature
              </button>
            </div>
          </div>
        )}

        {/* --- TAB 4: FORMAT & EXPORT --- */}
        {activeTab === "format" && (
          <div className="tool-section">
            <div className="section-title">Format Conversion & Compression</div>

            <div className="field">
              <label htmlFor="target-format">Target Format</label>
              <select
                id="target-format"
                className="select-input"
                value={targetFormat}
                onChange={(e) => setTargetFormat(e.target.value as "WEBP" | "JPEG" | "PNG")}
              >
                <option value="WEBP">WebP (Modern, compact, alpha-supported)</option>
                <option value="JPEG">JPEG (Universal photo format)</option>
                <option value="PNG">PNG (Lossless with alpha channel)</option>
              </select>
            </div>

            {targetFormat !== "PNG" && (
              <div className="slider-group">
                <div className="slider-header">
                  <label htmlFor="quality-slider">Quality / Compression</label>
                  <span className="slider-val">{quality}%</span>
                </div>
                <input
                  id="quality-slider"
                  type="range"
                  min={1}
                  max={100}
                  value={quality}
                  onChange={(e) => setQuality(parseInt(e.target.value, 10))}
                />
              </div>
            )}

            <button
              type="button"
              className="btn-apply"
              disabled={isProcessing}
              onClick={() => onApplyTool("image.convert_format", {
                target_format: targetFormat,
                quality,
              })}
            >
              {isProcessing ? "Converting Format…" : `Convert to ${targetFormat}`}
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};
