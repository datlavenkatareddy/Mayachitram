import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("../services/api", () => ({
  listProjects: vi.fn().mockResolvedValue([
    {
      id: "proj-1",
      name: "Campaign 2026",
      description: "Hero images",
      settings: {},
      created_at: "2026-10-25T10:00:00Z",
      updated_at: "2026-10-25T10:00:00Z",
      asset_count: 1,
    },
  ]),
  createProject: vi.fn().mockImplementation((data) =>
    Promise.resolve({
      id: "proj-2",
      name: data.name,
      description: data.description,
      settings: {},
      created_at: "2026-10-25T10:00:00Z",
      updated_at: "2026-10-25T10:00:00Z",
      asset_count: 0,
    })
  ),
  listAssets: vi.fn().mockResolvedValue([
    {
      id: "asset-1",
      project_id: "proj-1",
      original_filename: "hero_shot.png",
      media_type: "image/png",
      storage_key: "assets/hero.png",
      file_size: 204800,
      width: 1920,
      height: 1080,
      parent_asset_id: null,
      metadata: {},
      created_at: "2026-10-25T10:00:00Z",
    },
  ]),
  listOperations: vi.fn().mockResolvedValue([
    {
      id: "op-1",
      project_id: "proj-1",
      tool_name: "image.resize",
      parameters: { width: 1920, height: 1080 },
      input_asset_ids: ["asset-1"],
      output_asset_ids: ["asset-1"],
      status: "succeeded",
      created_at: "2026-10-25T10:00:00Z",
    },
  ]),
  getAssetFileUrl: vi.fn().mockReturnValue("http://localhost:8000/api/v1/projects/proj-1/assets/asset-1/file"),
  uploadAsset: vi.fn(),
  deleteAsset: vi.fn(),
  executeTool: vi.fn(),
  createMayaPlan: vi.fn(),
  executeMayaPlan: vi.fn(),
}));

describe("MayaChitram Creative Platform", () => {
  it("renders the studio brand, project selector, and asset filmstrip", async () => {
    render(<App />);

    expect(screen.getByText(/CREATIVE STUDIO/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Campaign 2026/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /\+ New/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Image Studio/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Maya AI Assistant/i })).toBeInTheDocument();
  });

  it("switches to Maya AI Assistant and displays conversational planner", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Campaign 2026/i)).toBeInTheDocument();
    });

    const mayaTabBtn = screen.getByRole("button", { name: /Maya AI Assistant/i });
    fireEvent.click(mayaTabBtn);

    expect(screen.getByText(/Maya Creative Assistant/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Make a 1:1 square crop/i)).toBeInTheDocument();
    expect(screen.getByText(/Quick Ideas:/i)).toBeInTheDocument();
  });

  it("renders tool panel tabs for creative transformations", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText(/hero_shot\.png/i).length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("button", { name: /^Transform$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Crop$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Color & Light$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Export$/i })).toBeInTheDocument();

    // Click Color tab
    fireEvent.click(screen.getByRole("button", { name: /^Color & Light$/i }));
    expect(screen.getByLabelText(/Brightness/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Contrast/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Saturation/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Color Temperature/i)).toBeInTheDocument();
  });
});
