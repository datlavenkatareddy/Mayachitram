# Collaborator Engine Integration Contract: Design & Video Engines

**Target Audience:** Collaborators developing Design Engine and Video Engine in parallel.  
**Location in Codebase:** `backend/src/mayachitram/maya/registry/adapters.py` and `mayachitram/maya/registry/tools.py`  

---

## 1. Overview

Maya is designed to orchestrate operations across all three engines (Image, Design, Video) through a single unified `ToolRegistry`.

When your Design or Video engine operations are ready to be integrated, you do **not** need to modify Maya's conversational or workflow engine. Simply register your engine adapter and tool handlers according to this contract.

---

## 2. Implementing Your Engine Adapter

Each engine implements a subclass of `BaseEngineAdapter` located in `mayachitram.maya.registry.adapters`:

```python
from mayachitram.maya.registry.adapters import BaseEngineAdapter
from pydantic import BaseModel

class MyDesignEngineAdapter(BaseEngineAdapter):
    @property
    def engine_id(self) -> str:
        return "design"

    @property
    def engine_name(self) -> str:
        return "Design Engine"

    @property
    def is_available(self) -> bool:
        # Return True once your backend service is initialized
        return True

    def get_supported_operations(self) -> list[str]:
        return [
            "design.create_canvas",
            "design.add_text",
            "design.apply_template",
            "design.export",
        ]

    def execute(self, tool_name: str, input_bytes: bytes, validated_params: BaseModel) -> tuple[bytes, Any]:
        # Call your core processing service here
        ...
```

---

## 3. Registering Operations in Maya's Tool Registry

In `mayachitram.maya.registry.tools.py`, inside `get_default_tool_registry()`:

```python
# 1. Define parameter schema using Pydantic
class DesignAddTextParams(BaseModel):
    text: str
    font_size: int = 36
    font_family: str = "Inter"
    color: str = "#FFFFFF"
    x: int = 50
    y: int = 50

# 2. Register the tool
registry.register(
    name="design.add_text",
    description="Overlay styled typography element on top of canvas or graphic design.",
    category="design",
    engine="design",
    params_class=DesignAddTextParams,
    handler=lambda engine, data, params: my_design_service.add_text(data, params),
    is_destructive=False,
    requires_approval=False,
    timeout_seconds=20,
    max_retries=1,
)
```

---

## 4. Contract Rules & Constraints

1. **Non-Destructive Outputs:** Every operation must return new output bytes without mutating or overwriting the original input asset bytes on disk.
2. **Deterministic Validation:** All parameters must be strongly typed with Pydantic schemas so Maya can validate them prior to execution.
3. **No Fake Responses:** While an operation is in development, do not register a handler that returns dummy or simulated success. Return `OperationError` with a clear explanation until the real processing logic is operational.
4. **Binary & Storage Integrity:** All input media are provided as `bytes`, and output media must be returned as `tuple[bytes, OutputMetadata]`. Maya automatically handles storage persistence, SQLite metadata, and version parentage.
