import { useState, useEffect, useRef } from 'react';
import useAgentStore from '../../store/agentStore';
import { designSchema, suggestDbName, executeInDB } from '../../api/agentApi';
import mermaid from 'mermaid';
import html2canvas from 'html2canvas';

mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'antiscript' });

const SAMPLE_PROMPT = `Design a customer order management schema with customers, orders, order items, products, and payments. Include relationships, constraints, indexes, audit columns, migration script, rollback script, and identify schema quality issues.`;

const SCHEMA_OUTPUTS = [
  { type: 'rollback_script', title: 'Rollback Script', desc: 'Drop generated schema objects in safe order.', filename: 'schema-rollback.sql' },
  { type: 'schema_review_report', title: 'Schema Review Report', desc: 'Quality, relationships, impact, and scripts.', filename: 'schema-review-report.md' },
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


const DB_TYPES = ['SQL Server'];

export default function SchemaTab() {
  const [prompt, setPrompt] = useState(SAMPLE_PROMPT);
  const [dbType, setDbType] = useState('SQL Server');
  const [copied, setCopied] = useState(false);
  const [connStr, setConnStr] = useState('Server=.\\SQLEXPRESS;Database=;Trusted_Connection=True;TrustServerCertificate=True;');
  const [dbStatus, setDbStatus] = useState(null);
  const [dbExecuting, setDbExecuting] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [previewTitle, setPreviewTitle] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [previewCopied, setPreviewCopied] = useState(false);
  const { currentSchema, setSchema, schemaLoading, setSchemaLoading } = useAgentStore();

  const handleDesign = async () => {
    if (!prompt.trim()) return alert('Describe a schema requirement or paste DDL first.');
    setSchemaLoading(true);
    setDbStatus(null);
    try {
      const result = await designSchema(prompt, dbType);
      setSchema(result);
      try {
        const suggested = await suggestDbName(prompt);
        // inject suggested db name into connection string
        setConnStr(prev => prev.replace(/Database=[^;]*/i, `Database=${suggested}`));
      } catch { /* keep existing */ }
    } catch (e) {
      alert(e.message);
    } finally {
      setSchemaLoading(false);
    }
  };

  const handleExecuteInDB = async () => {
    if (!currentSchema) return alert('Run DB Schema Agent first to generate a schema.');
    if (!connStr.trim()) return alert('Paste a connection string first.');
    setDbExecuting(true);
    setDbStatus(null);
    try {
      const result = await executeInDB(connStr, currentSchema.migration_script);
      setDbStatus({ type: 'success', message: result.message });
    } catch (e) {
      setDbStatus({ type: 'error', message: `❌ ${e.message}` });
    } finally {
      setDbExecuting(false);
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
    if (!currentSchema || !currentSchema.migration_script) return;
    const text = currentSchema.migration_script;
    navigator.clipboard.writeText(text).catch(() => {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    });
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
          <label>Database Type</label>
          <select value={dbType} onChange={(e) => setDbType(e.target.value)} style={{ marginBottom: 10 }}>
            {DB_TYPES.map(t => <option key={t}>{t}</option>)}
          </select>
          <label>Schema requirement or existing DDL</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            spellCheck={false}
            style={{ minHeight: 220 }}
          />
          <button className="primary schema-run" onClick={handleDesign} disabled={schemaLoading}>
            {schemaLoading ? 'Designing...' : 'Design Schema'}
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
            <span>DDL Script</span>
            <small style={{ color: '#666', fontWeight: 400, fontSize: '12px' }}>Create tables, keys, relationships, and indexes.</small>
            {currentSchema && (
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  onClick={handleCopyMigrationScript}
                  style={{ padding: '6px 12px', border: '1px solid #dce3ef', borderRadius: '6px', background: '#fff', color: copied ? '#07936f' : '#2f58ff', fontSize: '12px', fontWeight: '800', cursor: 'pointer', transition: 'color 0.2s' }}
                >
                  {copied ? 'Copied ✓' : '📋'}
                </button>
                <button 
                  onClick={() => handleDownload('ddl_script', 'schema-migration.sql')}
                  style={{ padding: '6px 12px', border: '1px solid #dce3ef', borderRadius: '6px', background: '#fff', color: '#2f58ff', fontSize: '12px', fontWeight: '800', cursor: 'pointer' }}
                >
                  ⬇ Download
                </button>
              </div>
            )}
          </div>
          <pre className="code-output">{currentSchema ? currentSchema.migration_script : '-- Run DB Schema Agent first.'}</pre>

          {/* Execute in DB panel — SQL Server only */}
          {dbType === 'SQL Server' && (
          <div style={{ marginTop: 16, borderTop: '1px solid #e5e7eb', paddingTop: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10, color: '#1e293b' }}>⚡ Execute in SQL Server</div>
            <label style={{ fontSize: 11, color: '#64748b' }}>Connection String</label>
            <textarea
              value={connStr}
              onChange={e => setConnStr(e.target.value)}
              spellCheck={false}
              rows={3}
              style={{ width: '100%', padding: '8px', border: '1px solid #dce3ef', borderRadius: 6, fontSize: 12, fontFamily: 'monospace', marginBottom: 8, resize: 'vertical' }}
              placeholder="Server=.\SQLEXPRESS;Database=MyDb;Trusted_Connection=True;TrustServerCertificate=True;"
            />
            <button
              onClick={handleExecuteInDB}
              disabled={dbExecuting || !currentSchema}
              style={{ padding: '8px 18px', background: dbExecuting ? '#94a3b8' : '#16a34a', color: '#fff', border: 'none', borderRadius: 6, fontWeight: 700, fontSize: 13, cursor: dbExecuting ? 'not-allowed' : 'pointer' }}
            >
              {dbExecuting ? 'Executing...' : '🚀 Execute in SQL Server'}
            </button>
            {dbStatus && (
              <div style={{ marginTop: 10, padding: '8px 12px', borderRadius: 6, fontSize: 12, background: dbStatus.type === 'success' ? '#f0fdf4' : '#fff1f2', color: dbStatus.type === 'success' ? '#15803d' : '#cf263f', border: `1px solid ${dbStatus.type === 'success' ? '#bbf7d0' : '#fecdd3'}` }}>
                {dbStatus.message}
              </div>
            )}
          </div>
          )}
        </article>
        <article className="card">
          <div className="section-heading blue" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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

      <div className="grid two" style={{ marginTop: 10 }}>
        {SCHEMA_OUTPUTS.map(({ type, title, desc, filename }) => (
          <article key={type} className="card">
            <div className="section-heading-row">
              <div className="section-heading red">{title}</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="view-btn" onClick={() => {
                  const text = currentSchema?.artifacts[type] || '';
                  setPreviewTitle(title);
                  setPreviewContent(text);
                  setShowPreview(true);
                }}>View</button>
                <button className="download-btn" onClick={() => handleDownload(type, filename)}>⬇️ Download</button>
              </div>
            </div>
            <p style={{ fontSize: 12, color: '#67738a', margin: '4px 0 0' }}>{desc}</p>
          </article>
        ))}
      </div>
      {showPreview && (
        <article className="card" style={{ marginTop: 10 }}>
          <div className="section-heading-row">
            <div className="section-heading green">{previewTitle} Preview</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="copy-btn" onClick={() => {
                navigator.clipboard.writeText(previewContent);
                setPreviewCopied(true);
                setTimeout(() => setPreviewCopied(false), 2000);
              }}>{previewCopied ? 'Copied ✓' : 'Copy'}</button>
              <button className="copy-btn" onClick={() => setShowPreview(false)}>✕ Close</button>
            </div>
          </div>
          <pre className="code-output">{previewContent}</pre>
        </article>
      )}
    </section>
  );
}
