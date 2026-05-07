import { useState } from 'react';
import useAgentStore from '../../store/agentStore';
import { downloadArtifact } from '../../api/agentApi';

const OUTPUTS = [
  { type: 'optimized_sql', title: 'Optimized SQL', desc: 'Draft optimized SQL with review notes.', filename: 'optimized-sql.sql' },
  { type: 'index_script', title: 'Index Recommendation', desc: 'Generated index scripts based on filters and joins.', filename: 'index-recommendations.sql' },
  { type: 'execution_plan_analysis', title: 'Execution Plan Analysis', desc: 'Plan-operator risks and validation notes.', filename: 'execution-plan-analysis.md' },
  { type: 'test_data_generator', title: 'Test Data Generator', desc: 'Representative test-data guidance.', filename: 'test-data-generator.sql' },
  { type: 'db_review_report', title: 'DB Review Report', desc: 'Complete findings, risk, impact, and recommendations.', filename: 'db-review-report.md' },
  { type: 'comparison_report', title: 'Before vs After Report', desc: 'Expected changes and improvement areas.', filename: 'comparison-report.md' },
];

export default function DeployTab() {
  const { currentAnalysis } = useAgentStore();
  const [previewContent, setPreviewContent] = useState('');
  const [previewTitle, setPreviewTitle] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  if (!currentAnalysis) {
    return <div className="empty-state"><p>Run an analysis first to access deployment outputs.</p></div>;
  }

  const handleDownload = async (type, filename) => {
    const text = await downloadArtifact(type, currentAnalysis);
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleView = async (type, title) => {
    try {
      const text = await downloadArtifact(type, currentAnalysis);
      setPreviewTitle(`${title} Preview`);
      setPreviewContent(text || 'No content available.');
      setShowPreview(true);
    } catch (error) {
      alert(`Error loading ${title}: ${error.message}`);
    }
  };

  return (
    <section className="tab-content">
      <article className="card">
        <div className="section-heading blue">Recommended Outputs / Reports</div>
        <div className="outputs">
          {OUTPUTS.map(({ type, title, desc, filename }) => (
            <div key={type} className="output-card-container">
              <div className="output-card-header">
                <strong>{title}</strong>
                <span>{desc}</span>
              </div>
              <div className="output-card-actions">
                <button className="view-btn" onClick={() => handleView(type, title)}>
                  View
                </button>
                <button className="download-btn" onClick={() => handleDownload(type, filename)}>
                  ⬇️ Download
                </button>
              </div>
            </div>
          ))}
        </div>
      </article>
      
      {showPreview && (
        <article className="card" style={{ marginTop: 10 }}>
          <div className="section-heading green">{previewTitle}</div>
          <pre className="code-output">{previewContent}</pre>
        </article>
      )}
    </section>
  );
}
