import useAgentStore from '../../store/agentStore';

export default function FixTab() {
  const { currentAnalysis } = useAgentStore();

  if (!currentAnalysis) {
    return <div className="empty-state"><p>Run an analysis first to see optimization outputs.</p></div>;
  }

  const { optimized_sql, index_scripts } = currentAnalysis;

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


    </section>
  );
}
