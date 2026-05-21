import { useState } from 'react';
import { scanDatabase, fetchProcedure, deployOptimized, analyzeSQL } from '../../api/agentApi';
import useAgentStore from '../../store/agentStore';

const STEPS = ['Connect', 'Pick SP', 'Optimize', 'Deploy'];

function StepBar({ current }) {
  return (
    <div style={{ display: 'flex', gap: 0, marginBottom: 20 }}>
      {STEPS.map((label, i) => {
        const done    = i < current;
        const active  = i === current;
        const color   = done ? '#07936f' : active ? '#2f58ff' : '#94a3b8';
        const bg      = done ? '#f0fdf4' : active ? '#eef2ff' : '#f8faff';
        const border  = done ? '#bbf7d0' : active ? '#a8b8ff' : '#dce3ef';
        return (
          <div key={label} style={{ flex: 1, textAlign: 'center', padding: '8px 4px', background: bg, border: `1px solid ${border}`, borderRight: i < STEPS.length - 1 ? 'none' : undefined, borderRadius: i === 0 ? '7px 0 0 7px' : i === STEPS.length - 1 ? '0 7px 7px 0' : 0 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {done ? '✓ ' : `${i + 1}. `}{label}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function LiveDbTab() {
  const [connStr, setConnStr]         = useState('Server=.\\SQLEXPRESS;Database=;Trusted_Connection=True;TrustServerCertificate=True;');
  const [scanResult, setScanResult]   = useState(null);
  const [scanning, setScanning]       = useState(false);
  const [selectedSp, setSelectedSp]   = useState(null);
  const [spSource, setSpSource]       = useState('');
  const [loadingSp, setLoadingSp]     = useState(false);
  const [analyzing, setAnalyzing]     = useState(false);
  const [optimizedSql, setOptimizedSql] = useState('');
  const [analysis, setAnalysis]       = useState(null);
  const [deploying, setDeploying]     = useState(false);
  const [deployStatus, setDeployStatus] = useState(null);
  const [filter, setFilter]           = useState('all'); // 'all' | 'slow'
  const [step, setStep]               = useState(0);

  const { setAnalysis: storeAnalysis, setActiveTab, setMode } = useAgentStore();

  // ── Step 1: Connect & Scan ────────────────────────────────────────────────
  const handleScan = async () => {
    if (!connStr.trim()) return alert('Paste a connection string first.');
    const dbMatch = connStr.match(/Database=([^;]*)/i);
    if (!dbMatch || !dbMatch[1].trim()) return alert('Database name is required. Add Database=YourDatabaseName; to the connection string.');
    setScanning(true);
    setScanResult(null);
    setSelectedSp(null);
    setSpSource('');
    setOptimizedSql('');
    setAnalysis(null);
    setDeployStatus(null);
    try {
      const result = await scanDatabase(connStr);
      setScanResult(result);
      setStep(1);
    } catch (e) {
      alert(`Connection failed: ${e.message}`);
    } finally {
      setScanning(false);
    }
  };

  // ── Step 2: Pick SP → load source ────────────────────────────────────────
  const handlePickSp = async (sp) => {
    setSelectedSp(sp);
    setSpSource('');
    setOptimizedSql('');
    setAnalysis(null);
    setDeployStatus(null);
    setLoadingSp(true);
    try {
      const result = await fetchProcedure(connStr, sp.procedure_name);
      setSpSource(result.source_code.replace(/\r\n/g, '\n').replace(/\r/g, '\n'));
      setStep(2);
    } catch (e) {
      alert(`Failed to load SP: ${e.message}`);
    } finally {
      setLoadingSp(false);
    }
  };

  // ── Step 3: Analyze & Optimize ────────────────────────────────────────────
  const handleAnalyze = async () => {
    if (!spSource.trim()) return;
    setAnalyzing(true);
    setOptimizedSql('');
    setDeployStatus(null);
    try {
      const result = await analyzeSQL(spSource, 'SQL Server', 'Stored Procedure');
      setAnalysis(result);
      const rawSql = (result.optimized_sql || '')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .replace(/\\n/g, '\n')
        .replace(/\\t/g, '\t')
        .replace(/\\r/g, '');
      setOptimizedSql(rawSql);
      // Also push into main store so Diagnose/Fix tabs show results
      storeAnalysis(result, spSource, 'SQL Server', 'Stored Procedure');
      setStep(3);
    } catch (e) {
      alert(`Analysis failed: ${e.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Step 4: Deploy ────────────────────────────────────────────────────────
  const handleDeploy = async () => {
    if (!optimizedSql.trim()) return alert('No optimized SQL to deploy.');
    if (!window.confirm(`Deploy optimized version of "${selectedSp?.procedure_name}" to SQL Server?\n\nThis will run CREATE OR ALTER PROCEDURE on your live database.`)) return;
    setDeploying(true);
    setDeployStatus(null);
    try {
      const result = await deployOptimized(connStr, optimizedSql, selectedSp?.procedure_name);
      setDeployStatus({ type: 'success', message: result.message });
      setStep(4);
    } catch (e) {
      setDeployStatus({ type: 'error', message: `❌ ${e.message}` });
    } finally {
      setDeploying(false);
    }
  };

  const displayedSps = scanResult
    ? (filter === 'slow'
        ? scanResult.stored_procedures.filter(sp => sp.is_slow)
        : scanResult.stored_procedures)
    : [];

  return (
    <section className="tab-content">
      <StepBar current={step > 3 ? 3 : step} />

      {/* ── Step 1: Connection ── */}
      <article className="card" style={{ marginBottom: 12 }}>
        <div className="section-heading blue">Step 1 — Connect to SQL Server</div>
        <label style={{ fontSize: 12, color: '#67738a' }}>Connection String</label>
        <textarea
          value={connStr}
          onChange={e => setConnStr(e.target.value)}
          spellCheck={false}
          rows={2}
          style={{ width: '100%', padding: 8, border: '1px solid #dce3ef', borderRadius: 6, fontSize: 12, fontFamily: 'monospace', marginBottom: 10, resize: 'vertical' }}
          placeholder="Server=.\SQLEXPRESS;Database=MyDb;Trusted_Connection=True;TrustServerCertificate=True;"
        />
        <button className="primary" onClick={handleScan} disabled={scanning} style={{ minWidth: 160 }}>
          {scanning ? 'Scanning...' : '🔍 Connect & Scan Database'}
        </button>

        {scanResult && (
          <div style={{ display: 'flex', gap: 10, marginTop: 14, flexWrap: 'wrap' }}>
            {[
              ['Stored Procedures', scanResult.summary.total_procedures, '#2f58ff', '#eef2ff'],
              ['Slow Procedures',   scanResult.summary.slow_procedures,  '#cf263f', '#fff1f2'],
              ['Tables',            scanResult.summary.total_tables,     '#07936f', '#f0fdf4'],
              ['Indexes',           scanResult.summary.total_indexes,    '#d97706', '#fff7ed'],
            ].map(([label, val, color, bg]) => (
              <div key={label} style={{ flex: '1 1 120px', padding: '10px 14px', background: bg, borderRadius: 8, border: `1px solid ${color}22` }}>
                <div style={{ fontSize: 22, fontWeight: 900, color }}>{val}</div>
                <div style={{ fontSize: 11, color: '#67738a', marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>
        )}
      </article>

      {/* ── Step 2: Pick SP ── */}
      {scanResult && (
        <article className="card" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div className="section-heading orange">Step 2 — Pick a Stored Procedure</div>
            <div style={{ display: 'flex', gap: 6 }}>
              {['all', 'slow'].map(f => (
                <button key={f} onClick={() => setFilter(f)} style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid #dce3ef', background: filter === f ? '#2f58ff' : '#fff', color: filter === f ? '#fff' : '#344054', fontWeight: 700, fontSize: 12, cursor: 'pointer' }}>
                  {f === 'all' ? `All (${scanResult.summary.total_procedures})` : `🔴 Slow (${scanResult.summary.slow_procedures})`}
                </button>
              ))}
            </div>
          </div>

          <div style={{ maxHeight: 320, overflowY: 'auto', display: 'grid', gap: 6 }}>
            {displayedSps.length === 0 && (
              <div style={{ color: '#67738a', fontSize: 13, padding: '20px 0', textAlign: 'center' }}>
                {filter === 'slow' ? 'No slow procedure stats yet — run the SPs first to populate sys.dm_exec_procedure_stats.' : 'No stored procedures found.'}
              </div>
            )}
            {displayedSps.map((sp) => (
              <div
                key={sp.procedure_name}
                onClick={() => handlePickSp(sp)}
                style={{
                  display: 'grid', gridTemplateColumns: '1fr auto auto', alignItems: 'center', gap: 10,
                  padding: '10px 14px', border: `1px solid ${selectedSp?.procedure_name === sp.procedure_name ? '#a8b8ff' : '#dce3ef'}`,
                  borderRadius: 8, background: selectedSp?.procedure_name === sp.procedure_name ? '#eef2ff' : sp.is_slow ? '#fff8f8' : '#f8faff',
                  cursor: 'pointer', transition: 'all 0.15s',
                }}
              >
                <div>
                  <div style={{ fontWeight: 800, fontSize: 13, color: '#172033' }}>
                    {sp.schema_name}.{sp.procedure_name}
                  </div>
                  <div style={{ fontSize: 11, color: '#67738a', marginTop: 2 }}>
                    Modified: {sp.modified_at?.slice(0, 10)} · {sp.source_length} chars
                  </div>
                </div>
                {sp.is_slow && (
                  <div style={{ fontSize: 11, fontWeight: 800, color: '#cf263f', background: '#fff1f2', padding: '2px 8px', borderRadius: 999, border: '1px solid #fecdd3' }}>
                    SLOW
                  </div>
                )}
                <button className="secondary" style={{ fontSize: 12, padding: '4px 12px' }}
                  onClick={e => { e.stopPropagation(); handlePickSp(sp); }}>
                  {loadingSp && selectedSp?.procedure_name === sp.procedure_name ? 'Loading...' : 'Select →'}
                </button>
              </div>
            ))}
          </div>
        </article>
      )}

      {/* ── Step 3: Source + Analyze ── */}
      {spSource && (
        <article className="card" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div className="section-heading green">
              Step 3 — {selectedSp?.procedure_name} · Source Code
            </div>
            <button className="primary" onClick={handleAnalyze} disabled={analyzing} style={{ minWidth: 180 }}>
              {analyzing ? 'Analyzing...' : '⚡ Analyze & Optimize'}
            </button>
          </div>
          <pre className="code-output" style={{ minHeight: 200, maxHeight: 320, whiteSpace: 'pre', overflowX: 'auto' }}>{spSource}</pre>

          {analysis && (
            <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid #dce3ef' }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'center' }}>
                <div style={{ fontSize: 12, fontWeight: 900, textTransform: 'uppercase', color: '#67738a', letterSpacing: '0.05em' }}>
                  Optimized SQL
                </div>
                <button className="copy-btn" onClick={() => navigator.clipboard.writeText(optimizedSql)}>Copy</button>
                <button className="secondary" style={{ fontSize: 12, padding: '4px 12px' }}
                  onClick={() => { setMode('analyze'); setActiveTab('diagnose'); }}>
                  View Full Diagnosis →
                </button>
              </div>
              <textarea
                value={optimizedSql}
                onChange={e => setOptimizedSql(e.target.value)}
                spellCheck={false}
                style={{ width: '100%', minHeight: 260, padding: 12, border: '1px solid #dce3ef', borderRadius: 8, background: '#f8faff', fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6, resize: 'vertical', whiteSpace: 'pre', overflowWrap: 'normal', overflowX: 'auto' }}
              />
              <div style={{ marginTop: 8, fontSize: 12, color: '#67738a', fontStyle: 'italic' }}>
                ✏️ You can edit the optimized SQL above before deploying.
              </div>

              {/* Quick findings summary */}
              <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                {['High', 'Medium', 'Low'].map(sev => {
                  const count = (analysis.findings || []).filter(f => f.severity === sev).length;
                  return count > 0 ? <span key={sev} className={`pill ${sev}`}>{count} {sev}</span> : null;
                })}
                {analysis.ai_status && (
                  <span style={{ fontSize: 11, color: '#0c4a6e', background: '#f0f9ff', padding: '2px 8px', borderRadius: 999, border: '1px solid #bae6fd' }}>
                    {analysis.ai_status}
                  </span>
                )}
              </div>
            </div>
          )}
        </article>
      )}

      {/* ── Step 4: Deploy ── */}
      {optimizedSql && (
        <article className="card">
          <div className="section-heading red" style={{ marginBottom: 12 }}>Step 4 — Deploy to SQL Server</div>
          <div style={{ padding: '14px 18px', background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 8, marginBottom: 14, fontSize: 13, color: '#92400e' }}>
            ⚠️ This will run <strong>CREATE OR ALTER PROCEDURE</strong> on your live database. Review the optimized SQL above before deploying.
          </div>
          <button
            onClick={handleDeploy}
            disabled={deploying}
            style={{ padding: '10px 24px', background: deploying ? '#94a3b8' : '#16a34a', color: '#fff', border: 'none', borderRadius: 7, fontWeight: 800, fontSize: 14, cursor: deploying ? 'not-allowed' : 'pointer' }}
          >
            {deploying ? 'Deploying...' : `🚀 Deploy "${selectedSp?.procedure_name}" to SQL Server`}
          </button>

          {deployStatus && (
            <div style={{ marginTop: 14, padding: '12px 16px', borderRadius: 8, fontSize: 13, fontWeight: 700, background: deployStatus.type === 'success' ? '#f0fdf4' : '#fff1f2', color: deployStatus.type === 'success' ? '#15803d' : '#cf263f', border: `1px solid ${deployStatus.type === 'success' ? '#bbf7d0' : '#fecdd3'}` }}>
              {deployStatus.message}
              {deployStatus.type === 'success' && (
                <div style={{ marginTop: 8, fontSize: 12, fontWeight: 400, color: '#047857' }}>
                  Open SSMS → Expand Stored Procedures → Refresh → You will see the updated procedure.
                </div>
              )}
            </div>
          )}
        </article>
      )}
    </section>
  );
}
