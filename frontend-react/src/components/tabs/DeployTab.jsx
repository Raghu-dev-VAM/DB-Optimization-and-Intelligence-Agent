import { useState } from 'react';
import useAgentStore from '../../store/agentStore';
import { downloadArtifact } from '../../api/agentApi';
import { jsPDF } from 'jspdf';

const OUTPUTS = [
  { type: 'optimized_sql', title: 'Optimized SQL', desc: 'Draft optimized SQL with review notes.', filename: 'optimized-sql.sql', pdf: false },
  { type: 'index_script', title: 'Index Recommendation', desc: 'Generated index scripts based on filters and joins.', filename: 'index-recommendations.sql', pdf: false },
  { type: 'db_review_report', title: 'DB Review Report', desc: 'Complete findings, risk, impact, and recommendations.', filename: 'db-review-report.pdf', pdf: true },
  { type: 'comparison_report', title: 'Before vs After Report', desc: 'What was wrong before and what was improved after.', filename: 'before-after-report.pdf', pdf: true },
];

export default function DeployTab() {
  const { currentAnalysis } = useAgentStore();
  const [previewContent, setPreviewContent] = useState('');
  const [previewTitle, setPreviewTitle] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  if (!currentAnalysis) {
    return <div className="empty-state"><p>Run an analysis first to access deployment outputs.</p></div>;
  }

  const downloadAsPdf = (text, filename) => {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 40;
    const maxWidth = pageWidth - margin * 2;
    const lineHeight = 14;
    let y = margin;

    const lines = text.split('\n');
    lines.forEach((line) => {
      const wrapped = doc.splitTextToSize(line, maxWidth);
      wrapped.forEach((wline) => {
        if (y > doc.internal.pageSize.getHeight() - margin) {
          doc.addPage();
          y = margin;
        }
        if (line.startsWith('# ')) {
          doc.setFontSize(16);
          doc.setFont('helvetica', 'bold');
        } else if (line.startsWith('## ')) {
          doc.setFontSize(13);
          doc.setFont('helvetica', 'bold');
        } else {
          doc.setFontSize(10);
          doc.setFont('helvetica', 'normal');
        }
        doc.text(wline.replace(/^#+\s*/, ''), margin, y);
        y += lineHeight;
      });
    });
    doc.save(filename);
  };

  const handleDownload = async (type, filename, pdf) => {
    const text = await downloadArtifact(type, currentAnalysis);
    if (pdf) {
      downloadAsPdf(text, filename);
    } else {
      const blob = new Blob([text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    }
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
          {OUTPUTS.map(({ type, title, desc, filename, pdf }) => (
            <div key={type} className="output-card-container">
              <div className="output-card-header">
                <strong>{title}</strong>
                <span>{desc}</span>
              </div>
              <div className="output-card-actions">
                <button className="view-btn" onClick={() => handleView(type, title)}>
                  View
                </button>
                <button className="download-btn" onClick={() => handleDownload(type, filename, pdf)}>
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
