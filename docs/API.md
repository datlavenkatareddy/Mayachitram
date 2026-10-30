# MayaChitram REST API Documentation

Base URL: `http://localhost:8000/api/v1`  
Interactive OpenAPI Documentation: `http://localhost:8000/docs`

---

## 1. System Endpoints

### `GET /health`
Returns system status.
- **Response:** `200 OK`
```json
{
  "status": "ok",
  "service": "mayachitram-api"
}
```

### `GET /api/v1/engines`
Returns list of registered engines and capabilities.
- **Response:** `200 OK`
```json
{
  "engines": [
    {
      "id": "image",
      "name": "Image Engine",
      "version": "1.0.0",
      "status": "available",
      "capabilities": ["image-description", "visible-object-identification"]
    }
  ]
}
```

---

## 2. Image Engine Endpoints

### `POST /api/v1/image/process`
Direct standalone image processing without requiring an active project.
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file`: Image binary (`image/jpeg`, `image/png`, `image/webp`)
  - `operation`: Tool name (e.g., `image.resize`, `image.crop`, `image.rotate`)
  - `params`: JSON string with validated arguments (e.g. `{"width": 800, "height": 600, "preserve_aspect": true}`)
- **Response:** `200 OK` with binary image stream and headers:
  - `X-Image-Width`: Result width in pixels
  - `X-Image-Height`: Result height in pixels
  - `X-Image-Format`: Output format (`JPEG`, `PNG`, `WEBP`)
  - `X-Image-Size`: File size in bytes

### `POST /api/v1/image/analyze`
Vision understanding through Groq Vision API.
- **Content-Type:** `multipart/form-data`
- **Fields:** `file`
- **Response:** `200 OK`
```json
{
  "engine": "image",
  "provider": "groq",
  "model": "llama-3.2-11b-vision-preview",
  "description": "A close-up shot of an espresso cup on a wooden table.",
  "objects": ["espresso cup", "wooden table"],
  "caveats": ["Object labels are descriptive observations, not pixel-accurate bounding boxes."]
}
```

---

## 3. Project Management Endpoints

### `POST /api/v1/projects`
Creates a persistent project.
- **Body:**
```json
{
  "name": "Social Media Campaign",
  "description": "Summer assets",
  "settings": {}
}
```
- **Response:** `201 Created`

### `GET /api/v1/projects`
Lists projects with pagination (`limit`, `offset`).
- **Response:** `200 OK` (Array of Project objects)

### `GET /api/v1/projects/{project_id}`
Retrieves project details.

### `PATCH /api/v1/projects/{project_id}`
Updates project name or description.

### `DELETE /api/v1/projects/{project_id}`
Deletes project and cascade-deletes all associated assets from storage and database.
- **Response:** `204 No Content`

---

## 4. Asset Endpoints

### `POST /api/v1/projects/{project_id}/assets`
Uploads an image asset to a project.
- **Content-Type:** `multipart/form-data`
- **Query Params:** `parent_asset_id` (optional, for versioning)
- **Response:** `201 Created` with Asset object.

### `GET /api/v1/projects/{project_id}/assets`
Lists all assets in the project.

### `GET /api/v1/projects/{project_id}/assets/{asset_id}`
Returns asset metadata.

### `GET /api/v1/projects/{project_id}/assets/{asset_id}/file`
Downloads or streams the binary image file.
- **Query Params:** `download=true` (sets `Content-Disposition: attachment`)

### `DELETE /api/v1/projects/{project_id}/assets/{asset_id}`
Deletes the asset file and database record.

### `GET /api/v1/projects/{project_id}/operations`
Returns chronological operation history records for the project.

---

## 5. Shared Tools & Maya Endpoints

### `GET /api/v1/tools`
Lists all registered tools with their descriptions and JSON parameter schemas.

### `POST /api/v1/tools/execute`
Executes any registered tool on an asset. Shared by UI controls and Maya.
- **Body:**
```json
{
  "project_id": "...",
  "tool_name": "image.crop",
  "parameters": {
    "left": 100,
    "top": 50,
    "width": 800,
    "height": 800
  },
  "input_asset_id": "..."
}
```
- **Response:** `200 OK` (`ToolExecutionResult`)

### `POST /api/v1/maya/plan`
Generates a structured plan from natural-language instructions.
- **Body:**
```json
{
  "project_id": "...",
  "user_prompt": "Make a square 1:1 version of this image and convert it to WebP",
  "target_asset_id": "..."
}
```
- **Response:** `200 OK` (`PlanResponse` containing ordered steps and rationale)

### `POST /api/v1/maya/execute`
Executes an approved plan step-by-step.
- **Body:**
```json
{
  "project_id": "...",
  "target_asset_id": "...",
  "plan": { ... },
  "confirmed": true
}
```
- **Response:** `200 OK` (`PlanExecutionResult`)
