import { RotateCcw, Download } from 'lucide-react';
import useAgentStore from '../store/agentStore';
import { resetSession } from '../api/agentApi';
import { downloadArtifact } from '../api/agentApi';

const titles = {
  analyze: 'Analyze SQL Object',
  schema: 'DB Schema Agent',
};

const descs = {
  analyze: 'Paste a stored procedure, query, function, view, DDL, or DML — get a full diagnosis, optimization plan, and deployment package.',
  schema: 'Describe your database in plain English — get tables, columns, relationships, ERD, quality review, and migration scripts.',
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
        <h1>
          {titles[mode]}
        </h1>
        <p>{mode === 'schema' ? descs.schema : descs[mode]}</p>
      </div>
      <div className="top-actions">
        <button className="ghost" onClick={handleNewSession}>
          <RotateCcw size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          New Session
        </button>
        <button className="ghost" onClick={handleSaveReport}>
          <Download size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Save Report
        </button>
      </div>
    </header>
  );
}
