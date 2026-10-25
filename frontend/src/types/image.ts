export interface ImageAnalysis {
  engine: string;
  provider: string;
  model: string;
  description: string;
  objects: string[];
  caveats: string[];
}
