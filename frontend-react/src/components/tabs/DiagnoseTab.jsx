import { useState } from 'react';
import useAgentStore from '../../store/agentStore';
import { downloadArtifact } from '../../api/agentApi';
import { jsPDF } from 'jspdf';

function HealthScore({ metrics, findings }) {
  const score = Math.max(0, 100 - metrics.risk_score);
  const high = findings.filter(f => f.severity === 'High').length;
  const medium = findings.filter(f => f.severity === 'Medium').length;
  const low = findings.filter(f => f.severity === 'Low').length;
  const color = score >= 70 ? '#07936f' : score >= 40 ? '#d97706' : '#cf263f';
  const bg = score >= 70 ? '#f0fdf4' : score >= 40 ? '#fff7ed' : '#fff1f2';
  const border = score >= 70 ? '#bbf7d0' : score >= 40 ? '#fed7aa' : '#fecdd3';
  const label = score >= 70 ? 'Good' : score >= 40 ? 'Needs Work' : 'Critical';

  return (
    <div style={{ padding: 20, borderRadius: 10, background: bg, border: `1px solid ${border}`, textAlign: 'center' }}>
      <div style={{ fontSize: 11, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#67738a', marginBottom: 6 }}>
        Health Score
      </div>
      <div style={{ fontSize: 52, fontWeight: 900, color, lineHeight: 1 }}>{score}</div>
      <div style={{ fontSize: 13, fontWeight: 700, color, marginTop: 4, marginBottom: 14 }}>{label}</div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span className="pill High">{high} High</span>
        <span className="pill Medium">{medium} Medium</span>
        <span className="pill Low">{low} Low</span>
      </div>
      <div style={{ marginTop: 12, fontSize: 11, color: '#67738a', fontStyle: 'italic' }}>
        Based on {findings.length} rule-based checks
      </div>
    </div>
  );
}

function WhatItDoes({ summary }) {
  return (
    <div style={{ padding: 20, borderRadius: 10, background: '#f8faff', border: '1px solid #dce3ef', height: '100%' }}>
      <div style={{ fontSize: 11, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#67738a', marginBottom: 12 }}>
        What This Object Does
      </div>
      <p style={{ margin: '0 0 16px', color: '#344054', lineHeight: 1.6, fontSize: 14 }}>
        {summary.ai_summary || summary.explanation}
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
        {[
          ['Type', summary.object_type],
          ['Database', summary.db_type],
          ['Tables', (summary.tables_involved || []).length + ' involved'],
          ['Joins', (summary.joins_used || []).length + ' used'],
          ['Missing Deps', (summary.missing_references || []).length || 'None'],
          ['Execution', summary.execution_type],
        ].map(([label, value]) => (
          <div key={label} style={{ padding: '8px 10px', background: '#fff', borderRadius: 7, border: '1px solid #dce3ef' }}>
            <div style={{ fontSize: 11, color: '#67738a' }}>{label}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#172033', marginTop: 2, wordBreak: 'break-word' }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FindingRow({ num, finding }) {
  const colors = { High: '#cf263f', Medium: '#d97706', Low: '#07936f' };
  const bgs = { High: '#fff1f2', Medium: '#fff7ed', Low: '#f0fdf4' };
  const borders = { High: '#fecdd3', Medium: '#fed7aa', Low: '#bbf7d0' };
  const color = colors[finding.severity] || '#67738a';
  const bg = bgs[finding.severity] || '#f8faff';
  const border = borders[finding.severity] || '#dce3ef';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '28px 1fr auto', gap: 10, alignItems: 'start', padding: '12px 14px', border: `1px solid ${border}`, borderRadius: 8, background: bg }}>
      <div style={{ display: 'grid', placeItems: 'center', width: 26, height: 26, borderRadius: '50%', background: '#fff', color, fontWeight: 900, fontSize: 12, border: `1px solid ${border}` }}>
        {num}
      </div>
      <div>
        <div style={{ fontWeight: 800, fontSize: 13, color: '#172033' }}>{finding.title}</div>
        <div style={{ marginTop: 4, fontSize: 12, color: '#4b5567', lineHeight: 1.5 }}>{finding.detail}</div>
        {finding.ai_explanation && (
          <div style={{ marginTop: 6, fontSize: 12, color: '#1e40af', lineHeight: 1.5, fontStyle: 'italic' }}>
            💡 {finding.ai_explanation}
          </div>
        )}
        {finding.evidence && (
          <code style={{ display: 'inline-block', marginTop: 6, padding: '2px 8px', background: 'rgba(0,0,0,0.05)', borderRadius: 4, fontSize: 11, color: '#344054' }}>
            {finding.evidence}
          </code>
        )}
      </div>
      <span className={`pill ${finding.severity}`}>{finding.severity}</span>
    </div>
  );
}

function BeforeAfter({ original, optimized }) {
  const [tab, setTab] = useState('optimized');
  const copy = (text) => navigator.clipboard.writeText(text);

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {['optimized', 'original'].map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: '5px 14px', borderRadius: 6, border: '1px solid #dce3ef',
                background: tab === t ? '#2f58ff' : '#fff',
                color: tab === t ? '#fff' : '#344054',
                fontWeight: 700, fontSize: 12, cursor: 'pointer'
              }}
            >
              {t === 'optimized' ? '✅ Optimized' : '📄 Original'}
            </button>
          ))}
        </div>
        <button className="copy-btn" onClick={() => copy(tab === 'optimized' ? optimized : original)}>
          Copy
        </button>
      </div>
      <pre className="code-output" style={{ minHeight: 300 }}>
        {tab === 'optimized' ? optimized : original}
      </pre>
    </div>
  );
}

function DeployBanner({ findings, onDownload, downloading }) {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 20,
      padding: '18px 22px', borderRadius: 10,
      background: '#f0fdf4', border: '1px solid #bbf7d0'
    }}>
      <div>
        <div style={{ fontSize: 15, fontWeight: 900, color: '#07936f', marginBottom: 6 }}>
          ✅ Ready to Deploy
        </div>
        <div style={{ fontSize: 13, color: '#047857' }}>
          No blocking issues found. Review medium findings before deploying to production.
        </div>
      </div>
      <button
        className="primary"
        style={{ whiteSpace: 'nowrap', minWidth: 160 }}
        onClick={onDownload}
        disabled={downloading}
      >
        {downloading ? 'Preparing...' : '📥 Download Report'}
      </button>
    </div>
  );
}

function MissingDepsBanner({ missing, onGoToDeps }) {
  if (!missing || missing.length === 0) return null;
  return (
    <div className="missing-banner">
      <span>
        ⚠️ Missing {missing.length > 1 ? 'dependencies' : 'dependency'} detected:{' '}
        <strong>{missing.join(', ')}</strong> — paste in Dependencies tab to complete analysis.
      </span>
      <button onClick={onGoToDeps}>Go to Dependencies →</button>
    </div>
  );
}

function AIFallbackBanner({ analysis }) {
  if (!analysis) return null;
  if (analysis.fallback_used) {
    return (
      <div className="ai-status-banner ai-fallback">
        <div className="ai-status-content">
          <span className="ai-status-text">⚠️ {analysis.fallback_message || 'AI unavailable — showing rule-based results.'}</span>
        </div>
      </div>
    );
  }
  if (analysis.ai_enhanced) {
    return (
      <div className="ai-status-banner ai-enhanced">
        <div className="ai-status-content">
          <span className="ai-status-text">{analysis.ai_status}</span>
        </div>
      </div>
    );
  }
  return null;
}

export default function DiagnoseTab() {
  const { currentAnalysis, primarySql, setActiveTab } = useAgentStore();
  const [downloading, setDownloading] = useState(false);

  if (!currentAnalysis) {
    return (
      <div className="empty-state">
        <p style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>No analysis yet</p>
        <p>Paste a SQL query, stored procedure, view, or function and click Analyze.</p>
      </div>
    );
  }

  const findings = currentAnalysis.findings || [];
  const suggestions = currentAnalysis.suggestions || [];
  const metrics = currentAnalysis.metrics || {};
  const summary = { ...currentAnalysis.summary, ai_summary: currentAnalysis.ai_summary } || {};

  // Sort findings — High first
  const sortedFindings = [...findings].sort((a, b) => {
    const order = { High: 0, Medium: 1, Low: 2 };
    return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
  });

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const text = await downloadArtifact('db_review_report', currentAnalysis);
      const doc = new jsPDF({ unit: 'pt', format: 'a4' });
      const margin = 40;
      const maxWidth = doc.internal.pageSize.getWidth() - margin * 2;
      const lineHeight = 14;
      let y = margin;
      text.split('\n').forEach((line) => {
        doc.splitTextToSize(line, maxWidth).forEach((wline) => {
          if (y > doc.internal.pageSize.getHeight() - margin) { doc.addPage(); y = margin; }
          if (line.startsWith('# ')) { doc.setFontSize(16); doc.setFont('helvetica', 'bold'); }
          else if (line.startsWith('## ')) { doc.setFontSize(13); doc.setFont('helvetica', 'bold'); }
          else { doc.setFontSize(10); doc.setFont('helvetica', 'normal'); }
          doc.text(wline.replace(/^#+\s*/, ''), margin, y);
          y += lineHeight;
        });
      });
      doc.save(`db-review-${summary.object_name || 'report'}.pdf`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section className="tab-content">
      <AIFallbackBanner analysis={currentAnalysis} />
      <MissingDepsBanner
        missing={summary.missing_references || []}
        onGoToDeps={() => setActiveTab('dependencies')}
      />

      {/* Step 1 — Health Score + What it does */}
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 12, marginBottom: 12 }}>
        <HealthScore metrics={metrics} findings={findings} />
        <WhatItDoes summary={summary} />
      </div>

      {/* Step 2 — What's Wrong */}
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="section-heading red">What's Wrong</div>
        {sortedFindings.length > 0 ? (
          <div style={{ display: 'grid', gap: 8 }}>
            {sortedFindings.map((f, i) => (
              <FindingRow key={i} num={i + 1} finding={f} />
            ))}
          </div>
        ) : (
          <div style={{ color: '#67738a', fontSize: 13, padding: '12px 0' }}>No issues detected.</div>
        )}

        {/* Top suggestions inline */}
        {suggestions.length > 0 && (
          <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid #dce3ef' }}>
            <div style={{ fontSize: 11, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#67738a', marginBottom: 10 }}>
              Recommended Fixes
            </div>
            <div style={{ display: 'grid', gap: 7 }}>
              {suggestions.slice(0, 4).map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '10px 12px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8 }}>
                  <span style={{ fontSize: 14 }}>✅</span>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 13 }}>{s.title}</div>
                    <div style={{ fontSize: 12, color: '#4b5567', marginTop: 3 }}>{s.recommendation}</div>
                  </div>
                  <span className={`pill ${s.impact}`} style={{ flexShrink: 0 }}>{s.impact}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>


    </section>
  );
}
