import { useState, useEffect, useRef } from 'react';
import useAgentStore from '../../store/agentStore';
import { designSchema, designSchemaAI, getMultiAgentStatus } from '../../api/agentApi';
import mermaid from 'mermaid';
import html2canvas from 'html2canvas';

mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'antiscript' });

const SAMPLE_PROMPT = `Design a customer order management schema with customers, orders, order items, products, and payments. Include relationships, constraints, indexes, audit columns, migration script, rollback script, and identify schema quality issues.`;

const SCHEMA_OUTPUTS = [
  { type: 'rollback_script', title: 'Rollback Script', desc: 'Drop generated schema objects in safe order.', filename: 'schema-rollback.sql' },
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
  const [aiStatus, setAiStatus] = useState(null);
  const [copied, setCopied] = useState(false);
  const { currentSchema, setSchema, schemaLoading, setSchemaLoading, schemaMode, setSchemaMode } = useAgentStore();

  useEffect(() => {
    const checkAiStatus = async () => {
      try {
        const status = await getMultiAgentStatus();
        setAiStatus(status);
      } catch {
        setAiStatus({ connected: false });
      }
    };
    checkAiStatus();
  }, []);

  const handleDesign = async () => {
    if (!prompt.trim()) return alert('Describe a schema requirement or paste DDL first.');
    setSchemaLoading(true);
    try {
      let result;
      if (schemaMode === 'ai') {
        if (!aiStatus?.connected) {
          throw new Error('AI is not available. Check your LLM API key and connection, or switch to Quick Schema.');
        }
        result = await designSchemaAI(prompt, 'SQL Server');
      } else {
        result = await designSchema(prompt, 'SQL Server');
      }
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
          {/* AI status description */}
          {aiStatus !== null && (
            <div style={{
              marginBottom: '10px',
              padding: '10px 12px',
              borderRadius: '6px',
              border: '1px solid',
              fontSize: '12px',
              lineHeight: '1.5',
              borderColor: aiStatus.connected ? '#bbf7d0' : '#fecdd3',
              background: aiStatus.connected ? '#f0fdf4' : '#fff1f2',
              color: aiStatus.connected ? '#07936f' : '#cf263f',
            }}>
              <span style={{
                display: 'inline-block',
                marginBottom: '6px',
                padding: '3px 10px',
                borderRadius: '999px',
                border: '1px solid',
                fontSize: '11px',
                fontWeight: '700',
                borderColor: aiStatus.connected ? '#bbf7d0' : '#fecdd3',
                background: aiStatus.connected ? '#dcfce7' : '#ffe4e6',
                color: aiStatus.connected ? '#07936f' : '#cf263f',
              }}>
                {aiStatus.connected ? '🤖 AI Connected' : 'AI Unavailable'}
              </span>
              <div style={{ marginTop: '6px' }}>
              {aiStatus.connected
                ? 'AI is available. Select AI Schema for AI-powered table design, relationships, and quality review. Or continue with Quick Schema for instant rule-based results.'
                : 'AI is unavailable. Check your LLM API key, token limits, or internet connection. Switch to Quick Schema to continue without AI.'}
              </div>
            </div>
          )}

          {/* Mode toggle */}
          <label>Schema Mode</label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <button
              className={`choice ${schemaMode === 'static' ? 'active' : ''}`}
              onClick={() => setSchemaMode('static')}
            >
              Quick Schema
            </button>
            <button
              className={`choice ${schemaMode === 'ai' ? 'active' : ''}`}
              onClick={() => setSchemaMode('ai')}
              disabled={aiStatus !== null && !aiStatus.connected}
            >
              AI Schema
            </button>
          </div>

          {/* Mode info */}
          <div className="analysis-info" style={{ marginBottom: 8 }}>
            {schemaMode === 'ai' ? (
              <small className="ai-info">🤖 <strong>AI Schema:</strong> AI designs tables, columns, relationships, and quality review from your description.</small>
            ) : (
              <small className="regular-info">⚡ <strong>Quick Schema:</strong> Rule-based keyword matching.</small>
            )}
          </div>

          <label>Schema requirement or existing DDL</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            spellCheck={false}
            style={{ minHeight: 220 }}
          />
          <button className="primary schema-run" onClick={handleDesign} disabled={schemaLoading}>
            {schemaLoading ? 'Designing...' : schemaMode === 'ai' ? '🚀 AI Design Schema' : 'Design / Review Schema'}
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
