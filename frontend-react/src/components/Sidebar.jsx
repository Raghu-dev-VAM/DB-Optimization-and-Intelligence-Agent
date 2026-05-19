import { Database, Search, FlaskConical } from 'lucide-react';
import useAgentStore from '../store/agentStore';

export default function Sidebar() {
  const { mode, setMode } = useAgentStore();

  return (
    <aside className="sidebar">
      <div className="brand-mark">
        <span className="db-icon"></span>
      </div>

      <nav className="side-nav">
        <button
          className={`nav-item ${mode === 'analyze' ? 'active' : ''}`}
          onClick={() => setMode('analyze')}
        >
          <span className="nav-icon"><Search size={13} /></span>
          <span>Analyze</span>
        </button>
        <button
          className={`nav-item ${mode === 'schema' ? 'active' : ''}`}
          onClick={() => setMode('schema')}
        >
          <span className="nav-icon"><Database size={13} /></span>
          <span>Schema Agent</span>
        </button>
      </nav>

      {mode === 'analyze' && (
        <button
          className="feedback"
          onClick={() => document.dispatchEvent(new CustomEvent('loadSample'))}
        >
          <FlaskConical size={13} style={{ marginRight: 5, flexShrink: 0 }} />
          Load Sample SP
        </button>
      )}
    </aside>
  );
}
