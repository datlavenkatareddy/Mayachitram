import type { ImageAnalysis } from "../types/image";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export async function analyzeImage(file: File): Promise<ImageAnalysis> {
  const form = new FormData();
  form.append("file", file);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/image/analyze`, { method: "POST", body: form });
  } catch {
    throw new Error("Cannot reach the MayaChitram API. Check that the backend is running.");
  }
  const payload = await response.json().catch(() => ({})) as Partial<ImageAnalysis> & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? `Image analysis failed (HTTP ${response.status}).`);
  return payload as ImageAnalysis;
}
