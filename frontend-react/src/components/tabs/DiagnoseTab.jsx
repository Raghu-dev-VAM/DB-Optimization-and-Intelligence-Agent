import useAgentStore from '../../store/agentStore';

const SEVERITY_CLASS = { High: 'High', Medium: 'Medium', Low: 'Low' };

function Pill({ severity }) {
  return <span className={`pill ${SEVERITY_CLASS[severity] || ''}`}>{severity}</span>;
}

function ItemCard({ num, title, text, severity }) {
  return (
    <div className="item">
      <span className="badge">{num}</span>
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
      {severity && <Pill severity={severity} />}
    </div>
  );
}

function RiskCard({ metrics, findings }) {
  const high = findings.filter(f => f.severity === 'High').length;
  const medium = findings.filter(f => f.severity === 'Medium').length;
  const low = findings.filter(f => f.severity === 'Low').length;
  const cls = metrics.risk_level === 'High' ? 'risk-high' : metrics.risk_level === 'Medium' ? 'risk-medium' : 'risk-low';
  return (
    <div className={`risk-card ${cls}`}>
      <div className="risk-label">Risk Level</div>
      <div className="risk-level">{metrics.risk_level}</div>
      <div className="risk-counts">
        <span className="pill High">{high} High</span>
        <span className="pill Medium">{medium} Medium</span>
        <span className="pill Low">{low} Low</span>
      </div>
      <div className="risk-potential">Improvement potential: {metrics.improvement_potential_pct}% after fixes</div>
      <div className="risk-note">Static analysis — validate with actual execution plan</div>
    </div>
  );
}

function MissingBanner({ missing, onGoToDeps }) {
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

function DeploymentReadiness({ findings }) {
  const high = findings.filter(f => f.severity === 'High' && f.title !== 'No major rule-based issue detected');
  const medium = findings.filter(f => f.severity === 'Medium');
  const ready = high.length === 0;
  return (
    <div className="deployment-readiness">
      <div className={`readiness-card ${ready ? 'ready-yes' : 'ready-no'}`}>
        <div className="readiness-status">
          {ready ? '✅ READY TO DEPLOY' : '❌ NOT READY — fix High issues first'}
        </div>
        {high.length > 0 && (
          <ul className="readiness-list">
            {high.map((f, i) => <li key={i}>{f.title}</li>)}
          </ul>
        )}
        {medium.length > 0 && (
          <>
            <div className="readiness-medium">⚠️ {medium.length} Medium issue{medium.length > 1 ? 's' : ''} recommended before deploy</div>
            <ul className="readiness-list muted">
              {medium.slice(0, 3).map((f, i) => <li key={i}>{f.title}</li>)}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

export default function DiagnoseTab() {
  const { currentAnalysis, setActiveTab } = useAgentStore();

  const summaryItems = currentAnalysis ? [
    ['Object Type', currentAnalysis.summary.object_type],
    ['Execution Type', currentAnalysis.summary.execution_type],
    ['Tables Involved', currentAnalysis.summary.tables_involved.join(', ') || 'None'],
    ['Joins Used', String(currentAnalysis.summary.joins_used.length)],
    ['Filters Applied', String(currentAnalysis.summary.filters_applied.length)],
    ['Group By', currentAnalysis.summary.group_by ? 'Yes' : 'No'],
    ['Order By', currentAnalysis.summary.order_by ? 'Yes' : 'No'],
    ['Missing Objects', currentAnalysis.summary.missing_references.length ? currentAnalysis.summary.missing_references.join(', ') : 'None'],
  ] : [];

  const impactItems = currentAnalysis ? [
    ['Affected Tables', currentAnalysis.impact.affected_tables.join(', ') || 'None'],
    ['Dependent Objects', currentAnalysis.impact.dependent_objects.join(', ') || 'None'],
    ['Missing Objects', currentAnalysis.impact.missing_objects.join(', ') || 'None'],
    ['Downstream', currentAnalysis.impact.downstream.join(', ')],
    ['Risk Level', currentAnalysis.impact.risk_level],
    ['Deployment Complexity', currentAnalysis.impact.deployment_complexity],
    ['Rollback', currentAnalysis.impact.rollback],
  ] : [];

  const findings = currentAnalysis ? currentAnalysis.findings : [];
  const suggestions = currentAnalysis ? currentAnalysis.suggestions : [];

  return (
    <section className="tab-content">
      {currentAnalysis && (
        <MissingBanner
          missing={currentAnalysis.summary.missing_references}
          onGoToDeps={() => setActiveTab('dependencies')}
        />
      )}

      <div className="grid two">
        <article className="card summary-card">
          <div className="section-heading blue">DB Object Summary</div>
          {summaryItems.length > 0 ? (
            <div className="summary-grid">
              {summaryItems.map(([label, value]) => (
                <div key={label} className="summary-cell">
                  <small>{label}</small>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          ) : <div className="summary-grid" />}
          <h3>What this object does</h3>
          <p className="explanation">
            {currentAnalysis ? currentAnalysis.summary.explanation : 'Paste a SQL object and run analysis.'}
          </p>
        </article>

        <article className="card metric-card">
          <div className="section-heading blue">Risk Overview</div>
          {currentAnalysis
            ? <RiskCard metrics={currentAnalysis.metrics} findings={findings} />
            : <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 8 }}>Risk overview appears after analysis.</div>
          }
        </article>
      </div>

      <div className="grid three">
        <article className="card">
          <div className="section-heading red">Top Performance Findings</div>
          <div className="stack">
            {findings.length > 0
              ? findings.slice(0, 6).map((f, i) => (
                  <ItemCard key={i} num={i + 1} title={f.title} text={f.detail} severity={f.severity} />
                ))
              : <ItemCard num={1} title="Waiting for SQL input" text="Paste a query or stored procedure and run analysis." severity="Low" />
            }
          </div>
        </article>
        <article className="card">
          <div className="section-heading green">Top Optimization Suggestions</div>
          <div className="stack">
            {suggestions.length > 0
              ? suggestions.slice(0, 6).map((s, i) => (
                  <ItemCard key={i} num={i + 1} title={s.title} text={s.recommendation} severity={s.impact} />
                ))
              : <ItemCard num={1} title="No suggestions yet" text="Recommendations appear after analysis." severity="Low" />
            }
          </div>
        </article>
        <article className="card">
          <div className="section-heading orange">Impact Analysis</div>
          <div className="stack compact">
            {impactItems.length > 0
              ? impactItems.map(([label, value], i) => (
                  <ItemCard key={i} num={i + 1} title={label} text={value} severity="" />
                ))
              : <ItemCard num={1} title="No impact yet" text="Risk and dependent objects appear after analysis." severity="Low" />
            }
          </div>
        </article>
      </div>

      {currentAnalysis && <DeploymentReadiness findings={findings} />}
    </section>
  );
}
