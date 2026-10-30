import React, { useState } from "react";
import type { ExecutionMode, ProjectPreferences } from "../../types/maya";

interface PreferencesDrawerProps {
  preferences: ProjectPreferences;
  onSave: (prefs: ProjectPreferences) => Promise<void>;
  onClose: () => void;
}

export const PreferencesDrawer: React.FC<PreferencesDrawerProps> = ({
  preferences,
  onSave,
  onClose,
}) => {
  const [colors, setColors] = useState<string[]>(preferences.brand_colors || []);
  const [newColor, setNewColor] = useState("#FF4500");
  const [formats, setFormats] = useState<string[]>(preferences.preferred_export_formats || ["WEBP", "PNG"]);
  const [mode, setMode] = useState<ExecutionMode>(preferences.default_execution_mode || "execute");
  const [customInstructions, setCustomInstructions] = useState(preferences.custom_instructions || "");
  const [isSaving, setIsSaving] = useState(false);

  function handleAddColor() {
    if (newColor && !colors.includes(newColor)) {
      setColors([...colors, newColor]);
    }
  }

  function handleRemoveColor(c: string) {
    setColors(colors.filter((item) => item !== c));
  }

  function toggleFormat(fmt: string) {
    if (formats.includes(fmt)) {
      setFormats(formats.filter((f) => f !== fmt));
    } else {
      setFormats([...formats, fmt]);
    }
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      await onSave({
        ...preferences,
        brand_colors: colors,
        preferred_export_formats: formats,
        default_execution_mode: mode,
        custom_instructions: customInstructions,
      });
      onClose();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="preferences-drawer" role="dialog" aria-label="Project Creative Preferences">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h4 style={{ margin: 0, color: "#f0f0f5", fontSize: "13px" }}>Project Brand & Creative Preferences</h4>
        <button type="button" className="mode-btn" onClick={onClose}>✕</button>
      </div>

      <div className="pref-field">
        <label>Default Execution Mode</label>
        <div className="mode-selector" style={{ alignSelf: "flex-start" }}>
          {(["assist", "execute", "autonomous"] as ExecutionMode[]).map((m) => (
            <button
              key={m}
              type="button"
              className={`mode-btn ${mode === m ? "active" : ""}`}
              onClick={() => setMode(m)}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="pref-field">
        <label>Brand Colors</label>
        <div className="pref-chips-row">
          {colors.map((c) => (
            <span key={c} className="color-swatch-chip">
              <span className="color-dot" style={{ background: c }} />
              {c}
              <button
                type="button"
                style={{ background: "transparent", border: "none", color: "#888", padding: 0 }}
                onClick={() => handleRemoveColor(c)}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
          <input
            type="color"
            value={newColor}
            onChange={(e) => setNewColor(e.target.value)}
            style={{ width: "32px", height: "30px", border: "none", background: "transparent", cursor: "pointer" }}
          />
          <button type="button" className="btn-prefs-toggle" onClick={handleAddColor}>
            + Add Swatch
          </button>
        </div>
      </div>

      <div className="pref-field">
        <label>Preferred Export Formats</label>
        <div className="pref-chips-row">
          {["WEBP", "PNG", "JPEG"].map((fmt) => (
            <button
              key={fmt}
              type="button"
              className={`mode-btn ${formats.includes(fmt) ? "active" : ""}`}
              onClick={() => toggleFormat(fmt)}
            >
              {fmt}
            </button>
          ))}
        </div>
      </div>

      <div className="pref-field">
        <label>Custom Brand & Creative Directives</label>
        <textarea
          className="maya-text-input"
          style={{ height: "64px", resize: "vertical", fontFamily: "var(--mono)", fontSize: "11px" }}
          placeholder="e.g. Always preserve sharp logo contrast, prefer 1:1 square crops for Instagram."
          value={customInstructions}
          onChange={(e) => setCustomInstructions(e.target.value)}
        />
      </div>

      <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
        <button type="button" className="secondary" onClick={onClose}>
          Cancel
        </button>
        <button type="button" className="primary" onClick={handleSave} disabled={isSaving}>
          {isSaving ? "Saving…" : "Save Brand Preferences"}
        </button>
      </div>
    </div>
  );
};
