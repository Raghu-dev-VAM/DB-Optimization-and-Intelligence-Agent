import useAgentStore from '../../store/agentStore';

export default function FixTab() {
  const { currentAnalysis } = useAgentStore();

  if (!currentAnalysis) {
    return <div className="empty-state"><p>Run an analysis first to see optimization outputs.</p></div>;
  }

  const { optimized_sql, index_scripts, execution_plan } = currentAnalysis;

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <section className="tab-content">
      <div className="grid two">
        <article className="card">
          <div className="section-heading-row">
            <div className="section-heading green">Optimized Query / Procedure Draft</div>
            <button className="copy-btn" onClick={() => copyToClipboard(optimized_sql)}>Copy</button>
          </div>
          <pre className="code-output">{optimized_sql || '-- Run analysis first.'}</pre>
        </article>
        <article className="card">
          <div className="section-heading-row">
            <div className="section-heading blue">Index Recommendation Scripts</div>
            <button className="copy-btn" onClick={() => copyToClipboard((index_scripts || []).join('\n\n'))}>Copy</button>
          </div>
          <pre className="code-output">{(index_scripts || []).join('\n\n') || '-- No index scripts generated.'}</pre>
        </article>
      </div>

      <article className="card" style={{ marginTop: 10 }}>
        <div className="section-heading blue">Execution Plan Review</div>
        <div className="plan-list">
          {execution_plan.operators.map((op, i) => (
            <div key={i} className="plan-op">
              <strong>{op.operator} <span className={`pill ${op.risk}`}>{op.risk}</span></strong>
              <p>{op.note}</p>
            </div>
          ))}
          <div className="plan-op"><strong>Statistics</strong><p>{execution_plan.statistics}</p></div>
          <div className="plan-op"><strong>Memory Grant</strong><p>{execution_plan.memory_grant}</p></div>
        </div>
      </article>
    </section>
  );
}
