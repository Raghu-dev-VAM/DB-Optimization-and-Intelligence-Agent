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
          <span className="nav-icon">A</span>
          <span>Analyze</span>
        </button>
        <button
          className={`nav-item ${mode === 'schema' ? 'active' : ''}`}
          onClick={() => setMode('schema')}
        >
          <span className="nav-icon">S</span>
          <span>Schema Agent</span>
        </button>
      </nav>
      <button
        className="feedback"
        onClick={() => {
          useAgentStore.getState().setMode('analyze');
          document.dispatchEvent(new CustomEvent('loadSample'));
        }}
      >
        Load Sample SP
      </button>
    </aside>
  );
}
