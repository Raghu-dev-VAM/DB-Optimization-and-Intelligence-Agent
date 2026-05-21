import useAgentStore from './store/agentStore';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import InputPanel from './components/InputPanel';
import DiagnoseTab from './components/tabs/DiagnoseTab';
import DependenciesTab from './components/tabs/DependenciesTab';
import FixTab from './components/tabs/FixTab';
import DeployTab from './components/tabs/DeployTab';
import SchemaTab from './components/tabs/SchemaTab';
import LiveDbTab from './components/tabs/LiveDbTab';

const TABS = [
  { id: 'diagnose', label: 'Diagnose' },
  { id: 'dependencies', label: 'Dependencies' },
  { id: 'fix', label: 'Optimization' },
  { id: 'deploy', label: 'Download' },
];

const TAB_COMPONENTS = {
  diagnose: DiagnoseTab,
  dependencies: DependenciesTab,
  fix: FixTab,
  deploy: DeployTab,
};

export default function App() {
  const { mode, activeTab, setActiveTab } = useAgentStore();
  const ActiveTab = TAB_COMPONENTS[activeTab] || DiagnoseTab;

  return (
    <>
      <Sidebar />
      <main className="shell">
        <Topbar />
        <section className={`workspace ${mode === 'schema' || mode === 'livedb' ? 'schema-mode' : ''}`}>
          {mode === 'analyze' && <InputPanel />}
          <section className="main-panel">
            {mode === 'analyze' && (
              <div className="tabs">
                {TABS.map(({ id, label }) => (
                  <button
                    key={id}
                    className={`tab-btn ${activeTab === id ? 'active' : ''}`}
                    onClick={() => setActiveTab(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
            {mode === 'analyze' ? <ActiveTab /> : mode === 'livedb' ? <LiveDbTab /> : <SchemaTab />}
          </section>
        </section>
      </main>
    </>
  );
}
