import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Asset } from "../../types/asset";
import { MayaPanel } from "./MayaPanel";

vi.mock("../../services/api", () => ({
  getProjectPreferences: vi.fn().mockResolvedValue({
    project_id: "test-proj",
    brand_colors: ["#FF4500", "#1A1A2E"],
    brand_fonts: ["Inter"],
    preferred_aspect_ratios: ["1:1"],
    preferred_export_formats: ["WEBP"],
    default_execution_mode: "execute",
    custom_instructions: "Prefer clean studio lighting.",
  }),
  getRecommendations: vi.fn().mockResolvedValue([
    {
      id: "rec_square_crop",
      category: "social_format",
      title: "Instagram / Feed Square (1:1)",
      description: "Centered 1:1 square crop",
      trade_offs: "Trims edges",
      suggested_prompt: "Make a centered 1:1 square crop",
      applicable_tools: ["image.crop"],
      parameters: { width: 800, height: 800 },
    },
  ]),
  chatWithMaya: vi.fn().mockResolvedValue({
    conversation_id: "conv-123",
    user_message: {
      id: "u-1",
      conversation_id: "conv-123",
      role: "user",
      content: "Make a square crop",
      message_type: "text",
      metadata: {},
      created_at: new Date().toISOString(),
    },
    assistant_message: {
      id: "a-1",
      conversation_id: "conv-123",
      role: "assistant",
      content: "I have created a 1-step creative workflow: Crop asset into a 1:1 square.",
      message_type: "workflow",
      metadata: {},
      created_at: new Date().toISOString(),
    },
    workflow: {
      id: "wf-1",
      project_id: "test-proj",
      title: "Crop asset into a 1:1 square.",
      description: "Generated from user request",
      tasks: [
        {
          task_id: "task_1",
          tool_name: "image.crop",
          description: "Crop square",
          parameters: { left: 0, top: 0, width: 800, height: 800 },
          dependencies: [],
          status: "pending",
          requires_approval: false,
          retry_count: 0,
          max_retries: 1,
        },
      ],
      status: "draft",
      execution_mode: "execute",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      final_asset_ids: [],
    },
    recommendations: [],
  }),
  executeWorkflow: vi.fn().mockResolvedValue({
    id: "wf-1",
    project_id: "test-proj",
    title: "Crop asset into a 1:1 square.",
    description: "Generated from user request",
    tasks: [
      {
        task_id: "task_1",
        tool_name: "image.crop",
        description: "Crop square",
        parameters: { left: 0, top: 0, width: 800, height: 800 },
        dependencies: [],
        status: "succeeded",
        requires_approval: false,
        retry_count: 0,
        max_retries: 1,
      },
    ],
    status: "completed",
    execution_mode: "execute",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    final_asset_ids: ["out-asset-1"],
  }),
  cancelWorkflow: vi.fn(),
  applyRecommendation: vi.fn(),
  updateProjectPreferences: vi.fn(),
  createMayaPlan: vi.fn(),
  executeMayaPlan: vi.fn(),
}));

const mockAsset: Asset = {
  id: "asset-100",
  project_id: "test-proj",
  original_filename: "product_model.png",
  media_type: "image/png",
  storage_key: "assets/product.png",
  file_size: 102400,
  width: 1200,
  height: 800,
  parent_asset_id: null,
  metadata: {},
  created_at: "2026-10-30T00:00:00Z",
};

describe("MayaPanel Component", () => {
  it("renders active context and execution mode buttons", async () => {
    render(
      <MayaPanel
        projectId="test-proj"
        activeAsset={mockAsset}
        onSwitchToStudio={vi.fn()}
      />
    );

    expect(screen.getByText(/Maya Creative Assistant/i)).toBeInTheDocument();
    expect(screen.getByText(/product_model\.png/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^ASSIST$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^EXECUTE$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^AUTONOMOUS$/i })).toBeInTheDocument();
  });

  it("renders grounded creative recommendations shelf", async () => {
    render(
      <MayaPanel
        projectId="test-proj"
        activeAsset={mockAsset}
        onSwitchToStudio={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Maya Creative Recommendations/i)).toBeInTheDocument();
      expect(screen.getByText(/Instagram \/ Feed Square \(1:1\)/i)).toBeInTheDocument();
    });
  });

  it("submits conversational prompt and renders workflow DAG card", async () => {
    render(
      <MayaPanel
        projectId="test-proj"
        activeAsset={mockAsset}
        onSwitchToStudio={vi.fn()}
      />
    );

    const input = screen.getByPlaceholderText(/Make a 1:1 square crop/i);
    fireEvent.change(input, { target: { value: "Make a square crop" } });

    const planBtn = screen.getByRole("button", { name: /Plan with Maya/i });
    fireEvent.click(planBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Crop asset into a 1:1 square/i).length).toBeGreaterThan(0);
      expect(screen.getByRole("button", { name: /Approve & Execute Workflow/i })).toBeInTheDocument();
    });
  });
});
