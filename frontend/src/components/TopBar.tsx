import type { Project } from "../types/project";

interface TopBarProps {
  currentProject: Project | null;
  projects: Project[];
  onSelectProject: (projectId: string) => void;
  onOpenNewProjectModal: () => void;
  activeTab: "studio" | "maya";
  onTabChange: (tab: "studio" | "maya") => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  currentProject,
  projects,
  onSelectProject,
  onOpenNewProjectModal,
  activeTab,
  onTabChange,
}) => {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <a className="brand" href="/" onClick={(e) => { e.preventDefault(); }}>
          <span className="brand-mark" aria-hidden="true">
            <i /><i /><i /><i />
          </span>
          <strong>Maya<span>Chitram</span></strong>
          <i className="divider" />
          <small>CREATIVE STUDIO</small>
        </a>

        <div className="mode-switcher">
          <button
            className={`mode-btn ${activeTab === "studio" ? "active" : ""}`}
            onClick={() => onTabChange("studio")}
          >
            ◈ Image Studio
          </button>
          <button
            className={`mode-btn ${activeTab === "maya" ? "active" : ""}`}
            onClick={() => onTabChange("maya")}
          >
            ✦ Maya AI Assistant
          </button>
        </div>
      </div>

      <div className="topbar-right">
        <div className="project-control">
          <label htmlFor="project-select" className="sr-only">Select Project</label>
          <select
            id="project-select"
            className="project-dropdown"
            value={currentProject?.id || ""}
            onChange={(e) => onSelectProject(e.target.value)}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                📁 {p.name} ({p.asset_count} assets)
              </option>
            ))}
          </select>
          <button
            className="btn-new-project"
            onClick={onOpenNewProjectModal}
            title="Create new persistent project"
          >
            + New
          </button>
        </div>

        <a
          className="api-docs"
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
        >
          API DOCS ↗
        </a>
      </div>
    </header>
  );
};
