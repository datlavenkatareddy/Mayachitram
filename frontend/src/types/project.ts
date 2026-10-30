export interface Project {
  id: string;
  name: string;
  description?: string | null;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  asset_count: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}
