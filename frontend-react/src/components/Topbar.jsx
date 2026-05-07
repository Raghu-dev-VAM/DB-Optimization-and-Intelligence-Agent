import useAgentStore from '../store/agentStore';
import { resetSession } from '../api/agentApi';
import { downloadArtifact } from '../api/agentApi';

const titles = {
  analyze: 'Analyze SQL Object',
  schema: 'DB Schema Agent',
};

const descs = {
  analyze: 'Paste a stored procedure, query, function, view, DDL, or DML — get a full diagnosis, optimization plan, and deployment package.',
  schema: 'Describe a schema in plain English or paste existing DDL — get tables, relationships, migration script, rollback, and ERD.',
};

export default function Topbar() {
  const { mode, currentAnalysis, clearSession } = useAgentStore();

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
        <h1>{titles[mode]}</h1>
        <p>{descs[mode]}</p>
      </div>
      <div className="top-actions">
        <button className="ghost" onClick={handleNewSession}>New Session</button>
        <button className="ghost" onClick={handleSaveReport}>Save Report</button>
      </div>
    </header>
  );
}
