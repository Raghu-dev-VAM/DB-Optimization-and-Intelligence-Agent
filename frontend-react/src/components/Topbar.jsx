import useAgentStore from '../store/agentStore';
import { resetSession } from '../api/agentApi';
import { downloadArtifact } from '../api/agentApi';

const titles = {
  analyze: 'Analyze SQL Object',
  schema: 'DB Schema Agent',
};

const descs = {
  analyze: 'Paste a stored procedure, query, function, view, DDL, or DML — get a full diagnosis, optimization plan, and deployment package.',
  schema: {
    ai: 'Describe your database in plain English — AI will design tables, columns, relationships, ERD and quality review.',
    static: 'Describe your database in plain English — get a static schema design with tables, columns, relationships, and ERD.',
  },
};

export default function Topbar() {
  const { mode, currentAnalysis, clearSession, analysisMode, schemaMode } = useAgentStore();

  const handleNewSession = async () => {
    await resetSession();
    clearSession();
    document.dispatchEvent(new CustomEvent('clearInput'));
  };

  const handleSaveReport = async () => {
    if (!currentAnalysis) return alert('Run an analysis first.');
    const text = await downloadArtifact('db_review_report', currentAnalysis);
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'db-review-report.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <header className="topbar">
      <div>
        <h1>
          {titles[mode]}
          {mode === 'analyze' && (
            <span style={{ marginLeft: 10, fontSize: 13, fontWeight: 500, padding: '2px 8px', borderRadius: 4, background: analysisMode === 'ai' ? '#eef2ff' : '#f0fdf4', color: analysisMode === 'ai' ? '#2f58ff' : '#07936f', verticalAlign: 'middle' }}>
              {analysisMode === 'ai' ? '🤖 AI Analysis' : '⚡ Quick Analysis'}
            </span>
          )}
          {mode === 'schema' && (
            <span style={{ marginLeft: 10, fontSize: 13, fontWeight: 500, padding: '2px 8px', borderRadius: 4, background: schemaMode === 'ai' ? '#eef2ff' : '#f0fdf4', color: schemaMode === 'ai' ? '#2f58ff' : '#07936f', verticalAlign: 'middle' }}>
              {schemaMode === 'ai' ? '🤖 AI Schema' : '⚡ Quick Schema'}
            </span>
          )}
        </h1>
        <p>{mode === 'schema' ? descs.schema[schemaMode] : descs[mode]}</p>
      </div>
      <div className="top-actions">
        <button className="ghost" onClick={handleNewSession}>New Session</button>
        <button className="ghost" onClick={handleSaveReport}>Save Report</button>
      </div>
    </header>
  );
}
