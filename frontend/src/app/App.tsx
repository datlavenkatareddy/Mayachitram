import { useCallback, useEffect, useState } from "react";
import { TopBar } from "../components/TopBar";
import { AssetFilmstrip } from "../features/assets/AssetFilmstrip";
import { ImageStudio } from "../features/image-studio/ImageStudio";
import { MayaPanel } from "../features/maya/MayaPanel";
import { ProjectModal } from "../features/projects/ProjectModal";
import {
  createProject,
  deleteAsset,
  listAssets,
  listOperations,
  listProjects,
  uploadAsset,
} from "../services/api";
import type { Asset } from "../types/asset";
import type { PlanExecutionResult, Workflow } from "../types/maya";
import type { OperationRecord } from "../types/operation";
import type { Project, ProjectCreate } from "../types/project";

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [activeAsset, setActiveAsset] = useState<Asset | null>(null);
  const [operations, setOperations] = useState<OperationRecord[]>([]);

  const [activeTab, setActiveTab] = useState<"studio" | "maya">("studio");
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [appError, setAppError] = useState<string | null>(null);

  // Load project assets and operations
  const loadProjectData = useCallback(async (projectId: string) => {
    try {
      const [projAssets, projOps] = await Promise.all([
        listAssets(projectId),
        listOperations(projectId),
      ]);
      setAssets(projAssets);
      setOperations(projOps);
      // Select latest asset if current selection is invalid
      setActiveAsset((prev) => {
        if (prev && projAssets.some((a) => a.id === prev.id)) {
          return prev;
        }
        return projAssets[0] || null;
      });
    } catch (err) {
      setAppError(err instanceof Error ? err.message : "Failed to load project assets.");
    }
  }, []);

  // Initialize or fetch projects on mount
  useEffect(() => {
    let isMounted = true;
    async function init() {
      setIsLoading(true);
      try {
        let projs = await listProjects();
        if (projs.length === 0) {
          const defaultProject = await createProject({
            name: "Studio Session",
            description: "Default creative project",
          });
          projs = [defaultProject];
        }
        if (isMounted) {
          setProjects(projs);
          const initial = projs[0];
          setCurrentProject(initial);
          await loadProjectData(initial.id);
        }
      } catch (err) {
        if (isMounted) {
          setAppError(err instanceof Error ? err.message : "Failed to connect to MayaChitram API.");
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    init();
    return () => {
      isMounted = false;
    };
  }, [loadProjectData]);

  // Handle Project Selection
  async function handleSelectProject(projectId: string) {
    const found = projects.find((p) => p.id === projectId);
    if (found) {
      setCurrentProject(found);
      await loadProjectData(found.id);
    }
  }

  // Handle Project Creation
  async function handleCreateProject(data: ProjectCreate) {
    const created = await createProject(data);
    setProjects((prev) => [created, ...prev]);
    setCurrentProject(created);
    setAssets([]);
    setActiveAsset(null);
    setOperations([]);
  }

  // Handle Image Upload
  async function handleUploadFile(file: File) {
    if (!currentProject) return;
    setIsUploading(true);
    setAppError(null);
    try {
      const newAsset = await uploadAsset(currentProject.id, file);
      setAssets((prev) => [newAsset, ...prev]);
      setActiveAsset(newAsset);
      // Refresh project asset count
      setProjects((prev) =>
        prev.map((p) => (p.id === currentProject.id ? { ...p, asset_count: p.asset_count + 1 } : p))
      );
    } catch (err) {
      setAppError(err instanceof Error ? err.message : "Failed to upload asset.");
    } finally {
      setIsUploading(false);
    }
  }

  // Handle Asset Deletion
  async function handleDeleteAsset(assetId: string) {
    if (!currentProject) return;
    try {
      await deleteAsset(currentProject.id, assetId);
      setAssets((prev) => prev.filter((a) => a.id !== assetId));
      if (activeAsset?.id === assetId) {
        setActiveAsset(assets.find((a) => a.id !== assetId) || null);
      }
      setProjects((prev) =>
        prev.map((p) =>
          p.id === currentProject.id ? { ...p, asset_count: Math.max(0, p.asset_count - 1) } : p
        )
      );
    } catch (err) {
      setAppError(err instanceof Error ? err.message : "Failed to delete asset.");
    }
  }

  // Handle Output Asset Created from Studio Tool
  function handleAssetCreated(newAsset: Asset) {
    setAssets((prev) => [newAsset, ...prev]);
    setActiveAsset(newAsset);
    if (currentProject) {
      loadProjectData(currentProject.id);
    }
  }

  // Handle Plan Executed in Maya
  function handlePlanExecuted(result: PlanExecutionResult) {
    if (result.final_asset) {
      setAssets((prev) => [result.final_asset as Asset, ...prev]);
      setActiveAsset(result.final_asset);
    }
    if (currentProject) {
      loadProjectData(currentProject.id);
    }
  }

  // Handle Workflow Executed in Maya
  async function handleWorkflowExecuted(workflow?: Workflow) {
    if (currentProject) {
      try {
        const [projAssets, projOps] = await Promise.all([
          listAssets(currentProject.id),
          listOperations(currentProject.id),
        ]);
        setAssets(projAssets);
        setOperations(projOps);
        if (workflow?.final_asset_ids?.length) {
          const latestId = workflow.final_asset_ids[workflow.final_asset_ids.length - 1];
          const newAsset = projAssets.find((a) => a.id === latestId);
          if (newAsset) {
            setActiveAsset(newAsset);
            return;
          }
        }
        setActiveAsset((prev) => {
          if (prev && projAssets.some((a) => a.id === prev.id)) return prev;
          return projAssets[0] || null;
        });
      } catch (err) {
        setAppError(err instanceof Error ? err.message : "Failed to refresh project data.");
      }
    }
  }

  // Resolve parent asset for before/after comparison
  const parentAsset = activeAsset?.parent_asset_id
    ? assets.find((a) => a.id === activeAsset.parent_asset_id) || null
    : null;

  return (
    <div className="app-shell">
      <TopBar
        currentProject={currentProject}
        projects={projects}
        onSelectProject={handleSelectProject}
        onOpenNewProjectModal={() => setIsProjectModalOpen(true)}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <main>
        {appError && (
          <div className="tool-error" style={{ margin: "16px 0 0" }} role="alert">
            {appError}
          </div>
        )}

        {isLoading ? (
          <div className="canvas-empty" style={{ margin: "40px 0" }}>
            <span className="spinner big" />
            <h3>Connecting to MayaChitram Creative Engine…</h3>
          </div>
        ) : (
          <div className="studio-container">
            {currentProject && (
              <AssetFilmstrip
                projectId={currentProject.id}
                assets={assets}
                activeAssetId={activeAsset?.id || null}
                onSelectAsset={setActiveAsset}
                onUploadFile={handleUploadFile}
                onDeleteAsset={handleDeleteAsset}
                isUploading={isUploading}
              />
            )}

            {activeTab === "studio" && currentProject && (
              <ImageStudio
                projectId={currentProject.id}
                activeAsset={activeAsset}
                parentAsset={parentAsset}
                assets={assets}
                operations={operations}
                onAssetCreated={handleAssetCreated}
                onSelectAssetById={(id) => {
                  const target = assets.find((a) => a.id === id);
                  if (target) setActiveAsset(target);
                }}
              />
            )}

            {activeTab === "maya" && currentProject && (
              <MayaPanel
                projectId={currentProject.id}
                activeAsset={activeAsset}
                onPlanExecuted={handlePlanExecuted}
                onWorkflowExecuted={handleWorkflowExecuted}
                onSwitchToStudio={() => setActiveTab("studio")}
              />
            )}
          </div>
        )}
      </main>

      <ProjectModal
        isOpen={isProjectModalOpen}
        onClose={() => setIsProjectModalOpen(false)}
        onCreate={handleCreateProject}
      />

      <footer>
        <span className="footer-brand">
          <span className="brand-mark" aria-hidden="true">
            <i /><i /><i /><i />
          </span>
          MAYACHITRAM
        </span>
        <span>ONE ENGINE. TWO MODES. UNIFIED PERSISTENT STUDIO.</span>
        <span>V1.0.0 <i>●</i> PRODUCTION READY</span>
      </footer>
    </div>
  );
}
