import { useState, useEffect, useRef } from 'react';
import useAgentStore from '../../store/agentStore';
import { designSchema } from '../../api/agentApi';
import mermaid from 'mermaid';
import html2canvas from 'html2canvas';

mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'antiscript' });

const SAMPLE_PROMPT = `Design a customer order management schema with customers, orders, order items, products, and payments. Include relationships, constraints, indexes, audit columns, migration script, rollback script, and identify schema quality issues.`;

const SCHEMA_OUTPUTS = [
  { type: 'ddl_script', title: 'DDL Script', desc: 'Create tables, keys, relationships, and indexes.', filename: 'schema-migration.sql' },
  { type: 'rollback_script', title: 'Rollback Script', desc: 'Drop generated schema objects in safe order.', filename: 'schema-rollback.sql' },
  { type: 'erd_summary', title: 'ERD Summary', desc: 'Mermaid ERD relationship summary.', filename: 'schema-erd.mmd' },
  { type: 'schema_review_report', title: 'Schema Review Report', desc: 'Quality, relationships, impact, and scripts.', filename: 'schema-review-report.md' },
  { type: 'migration_plan', title: 'Migration Plan', desc: 'Deployment sequence and validation checklist.', filename: 'schema-migration-plan.md' },
];

function ErdDiagram({ erdText }) {
  const ref = useRef();

  useEffect(() => {
    if (!erdText || erdText.trim() === 'erDiagram' || !ref.current) return;
    const id = 'erd' + Date.now();
    mermaid.render(id, erdText.trim())
      .then(({ svg }) => { if (ref.current) ref.current.innerHTML = svg; })
      .catch(() => { if (ref.current) ref.current.innerHTML = `<pre style="font-size:12px">${erdText}</pre>`; });
  }, [erdText]);

  return <div ref={ref} className="erd-diagram" />;
}

export default function SchemaTab() {
  const [prompt, setPrompt] = useState(SAMPLE_PROMPT);
  const { currentSchema, setSchema, schemaLoading, setSchemaLoading } = useAgentStore();

  const handleDesign = async () => {
    if (!prompt.trim()) return alert('Describe a schema requirement or paste DDL first.');
    setSchemaLoading(true);
    try {
      const result = await designSchema(prompt, 'SQL Server');
      setSchema(result);
    } catch (e) {
      alert(e.message);
    } finally {
      setSchemaLoading(false);
    }
  };

  const handleDownload = (type, filename) => {
    if (!currentSchema) return alert('Run DB Schema Agent first.');
    const text = currentSchema.artifacts[type] || '';
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyMigrationScript = () => {
    if (!currentSchema || !currentSchema.migration_script) {
      alert('No migration script to copy yet.');
      return;
    }
    
    navigator.clipboard.writeText(currentSchema.migration_script).then(() => {
      alert('Migration script copied to clipboard!');
    }).catch(() => {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = currentSchema.migration_script;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      alert('Migration script copied to clipboard!');
    });
  };

  const handleDownloadPDF = async () => {
    if (!currentSchema) return alert('Run DB Schema Agent first.');
    
    const erdElement = document.querySelector('.erd-diagram');
    if (!erdElement) return alert('ERD diagram not found.');
    
    try {
      const canvas = await html2canvas(erdElement, {
        backgroundColor: '#ffffff',
        scale: 2,
        useCORS: true
      });
      
      // Create a new window with the image for printing to PDF
      const imgData = canvas.toDataURL('image/png');
      const printWindow = window.open('', '_blank');
      printWindow.document.write(`
        <html>
          <head><title>ERD Diagram</title></head>
          <body style="margin:0; display:flex; justify-content:center; align-items:center; min-height:100vh;">
            <img src="${imgData}" style="max-width:100%; height:auto;" />
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.focus();
      
      // Trigger print dialog (user can save as PDF)
      setTimeout(() => printWindow.print(), 500);
    } catch (error) {
      alert('Failed to generate PDF: ' + error.message);
    }
  };

  return (
    <section className="tab-content">
      <div className="grid schema-layout">
        <article className="card">
          <div className="section-heading green">DB Schema Agent</div>
          <small className="hint" style={{ marginTop: 0, marginBottom: 8 }}>
            Describe a schema in plain English, or paste existing DDL to review it.
          </small>
          <label>Schema requirement or existing DDL</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            spellCheck={false}
            style={{ minHeight: 220 }}
          />
          <button className="primary schema-run" onClick={handleDesign} disabled={schemaLoading}>
            {schemaLoading ? 'Designing...' : 'Design / Review Schema'}
          </button>
        </article>

        <article className="card">
          <div className="section-heading blue">Tables &amp; Relationships</div>
          <div className="schema-list">
            {currentSchema ? (
              <>
                {currentSchema.tables.map((table) => (
                  <div key={table.name} className="schema-table">
                    <strong>{table.name}</strong>
                    <span>{table.columns.map(c => `${c.name} ${c.type}${c.role ? ` (${c.role})` : ''}`).join(', ')}</span>
                  </div>
                ))}
                {currentSchema.relationships.map((rel, i) => (
                  <div key={i} className="edge">
                    <strong>{rel.from}</strong>
                    <em>FK {rel.column}</em>
                    <strong>{rel.to}</strong>
                  </div>
                ))}
              </>
            ) : (
              <div className="schema-table"><strong>No schema yet</strong><span>Use DB Schema Agent to design or review a schema.</span></div>
            )}
          </div>
        </article>

        <article className="card">
          <div className="section-heading orange">Schema Quality Review</div>
          <div className="stack">
            {currentSchema ? currentSchema.quality_review.map((item, i) => (
              <div key={i} className="item">
                <span className="badge">{i + 1}</span>
                <div><strong>{item.title}</strong><p>{item.detail}</p></div>
                <span className={`pill ${item.severity}`}>{item.severity}</span>
              </div>
            )) : (
              <div className="item">
                <span className="badge">1</span>
                <div><strong>No schema review yet</strong><p>Schema quality findings appear after design/review.</p></div>
                <span className="pill Low">Low</span>
              </div>
            )}
          </div>
        </article>
      </div>

      <div className="grid two schema-results">
        <article className="card">
          <div className="section-heading green" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Migration Script</span>
            {currentSchema && (
              <button 
                onClick={handleCopyMigrationScript}
                style={{ 
                  padding: '6px 12px', 
                  border: '1px solid #dce3ef', 
                  borderRadius: '6px', 
                  background: '#fff', 
                  color: '#2f58ff', 
                  fontSize: '12px', 
                  fontWeight: '800', 
                  cursor: 'pointer' 
                }}
              >
                📋
              </button>
            )}
          </div>
          <pre className="code-output">{currentSchema ? currentSchema.migration_script : '-- Run DB Schema Agent first.'}</pre>
        </article>
        <article className="card">
          <div className="section-heading red">Rollback / ERD / Reports</div>
          <div className="outputs">{SCHEMA_OUTPUTS.map(({ type, title, desc, filename }) => (
            <button key={type} className="output-card" onClick={() => handleDownload(type, filename)}>
              <strong>{title}</strong>
              <span>{desc}</span>
              <small>Download</small>
            </button>
          ))}</div>
          <div className="section-heading blue" style={{ marginTop: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Entity Relationship Diagram</span>
            {currentSchema && (
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className="download-erd-btn" 
                  onClick={() => handleDownload('erd_summary', 'schema-erd.mmd')}
                  style={{ padding: '4px 8px', fontSize: '12px', background: '#007acc', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Download .mmd
                </button>
                <button 
                  className="download-pdf-btn" 
                  onClick={handleDownloadPDF}
                  style={{ padding: '4px 8px', fontSize: '12px', background: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
                >
                  Print to PDF
                </button>
              </div>
            )}
          </div>
          {currentSchema ? <ErdDiagram erdText={currentSchema.erd_summary} /> : (
            <div className="erd-diagram"><p className="erd-empty">Run DB Schema Agent to see the ERD diagram.</p></div>
          )}
        </article>
      </div>
    </section>
  );
}
