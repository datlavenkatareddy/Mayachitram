export interface Asset {
  id: string;
  project_id: string;
  original_filename: string;
  media_type: string;
  storage_key: string;
  file_size: number;
  width: number;
  height: number;
  parent_asset_id?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}
