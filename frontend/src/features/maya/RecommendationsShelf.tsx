import React from "react";
import type { CreativeRecommendation } from "../../types/maya";

interface RecommendationsShelfProps {
  recommendations: CreativeRecommendation[];
  onApply: (rec: CreativeRecommendation) => void;
  isLoading?: boolean;
}

export const RecommendationsShelf: React.FC<RecommendationsShelfProps> = ({
  recommendations,
  onApply,
  isLoading = false,
}) => {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <section className="recs-shelf" aria-label="Maya Creative Recommendations">
      <div className="recs-shelf-header">
        <h5>💡 Maya Creative Recommendations</h5>
        <span className="file-badge">AI GROUNDED</span>
      </div>
      <div className="recs-grid">
        {recommendations.map((rec) => (
          <div key={rec.id} className="rec-card">
            <div>
              <span className="rec-category-badge">{rec.category.replace("_", " ")}</span>
              <div className="rec-title">{rec.title}</div>
              <p className="rec-desc">{rec.description}</p>
              {rec.trade_offs && <p className="rec-tradeoff">Note: {rec.trade_offs}</p>}
            </div>
            <button
              type="button"
              className="btn-apply-rec"
              disabled={isLoading}
              onClick={() => onApply(rec)}
            >
              Apply Workflow ↗
            </button>
          </div>
        ))}
      </div>
    </section>
  );
};
