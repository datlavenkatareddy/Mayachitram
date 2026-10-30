# Maya AI Tool System & Conversational Assistant

## 1. Architectural Philosophy

Maya is the conversational interface to MayaChitram's creative engine. Maya does **not** bypass application services, does **not** write raw files, and does **not** execute arbitrary code.

Manual controls in the Image Studio and natural-language commands to Maya call the exact same registered tools in `ToolRegistry` through `ExecutionService`.

---

## 2. Tool Definition & Registry

Every tool is registered with:
- **`name`**: Stable dot-notated identifier (`image.resize`, `image.crop`, etc.)
- **`description`**: Human-readable and LLM-friendly description
- **`category`**: Domain namespace (`image`, `project`)
- **`params_class`**: Pydantic model enforcing type safety, bounds, and defaults
- **`handler`**: Pure execution function `(ImageEngine, bytes, ValidatedParams) -> (bytes, ImageMetadata)`
- **`is_destructive`**: Boolean flag indicating if user confirmation is required

### Registered Tools in Maya v1:
- `image.resize`
- `image.crop`
- `image.rotate`
- `image.flip`
- `image.convert_format`
- `image.compress`
- `image.adjust_brightness`
- `image.adjust_contrast`
- `image.adjust_saturation`
- `image.adjust_temperature`

---

## 3. Planning Engine

### 3.1 AI Planning with Groq
When `GROQ_API_KEY` is configured, Maya formats:
- Active asset resolution and metadata
- Available project assets
- Registered tool schemas
And calls Groq's `llama-3.3-70b-versatile` with `response_format={"type": "json_object"}`.

The model is constrained to return a plan object:
```json
{
  "summary": "Crop photo into a square and convert to WebP",
  "steps": [
    {
      "step_id": 1,
      "tool_name": "image.crop",
      "parameters": { "left": 100, "top": 0, "width": 800, "height": 800 },
      "rationale": "Centered 1:1 square crop"
    },
    {
      "step_id": 2,
      "tool_name": "image.convert_format",
      "parameters": { "target_format": "WEBP", "quality": 85 },
      "rationale": "Modern compressed WebP format"
    }
  ]
}
```

### 3.2 Resilient Semantic Fallback
If the Groq API key is not configured or an offline request occurs, Maya falls back to a deterministic semantic parser capable of extracting parameters for:
- 1:1 Square crops (calculates centered crop based on actual image dimensions)
- Rotations (90°, 180°, 270°)
- Flips (Horizontal, Vertical)
- Resizes & Aspect ratio presets (Instagram portrait 1080x1350, landscape 1920x1080)
- Format conversions (WebP, JPEG, PNG)
- Tonal adjustments (Brightness, Contrast, Saturation, Temperature)

---

## 4. Execution & Safety Pipeline

1. **Schema Validation:** Each planned step's parameters are validated through Pydantic before any execution occurs.
2. **Context Resolution:** If a step does not specify an asset ID, it operates on the previous step's output (sequential chaining).
3. **Execution & History:**
   - Operation record is created with `status="running"`.
   - Transformation is performed by `ImageEngine`.
   - New version asset is saved with `parent_asset_id` pointing to the input asset.
   - Operation record is updated to `status="succeeded"`.
4. **Sandboxing:** Arbitrary code execution, shell commands, raw filesystem paths, and direct SQL queries are strictly prevented.
