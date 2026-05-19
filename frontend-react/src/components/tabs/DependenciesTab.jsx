import { useState } from 'react';
import useAgentStore from '../../store/agentStore';
import { addRelatedObject, analyzeSQL } from '../../api/agentApi';

function DepGraph({ depMap }) {
  if (!depMap || !depMap.edges.length) {
    return <p style={{ color: '#67738a', fontSize: 13, padding: '20px 0', textAlign: 'center' }}>No dependency edges yet.</p>;
  }

  const { nodes, edges } = depMap;
  const nodeW = 140, nodeH = 32, colGap = 60, rowGap = 45;
  const procs = nodes.filter(n => n.type !== 'Table');
  const tables = nodes.filter(n => n.type === 'Table');

  const positions = {};
  procs.forEach((n, i) => { positions[n.id.toLowerCase()] = { x: 15, y: 15 + i * (nodeH + rowGap) }; });
  tables.forEach((n, i) => { positions[n.id.toLowerCase()] = { x: 15 + nodeW + colGap, y: 15 + i * (nodeH + rowGap) }; });

  const totalW = nodeW * 2 + colGap + 30;
  const totalH = Math.max(procs.length, tables.length, 1) * (nodeH + rowGap) + 60;
  const colorMap = { known: '#2f58ff', missing: '#cf263f', referenced: '#07936f' };

  return (
    <svg width={totalW} height={totalH} style={{ display: 'block', minWidth: totalW, minHeight: totalH, flexShrink: 0 }}>
        <defs>
          <marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#94a3b8" />
          </marker>
        </defs>
        {edges.map((edge, i) => {
          const from = positions[edge.from.toLowerCase()];
          const to = positions[edge.to.toLowerCase()];
          if (!from || !to) return null;
          const x1 = from.x + nodeW, y1 = from.y + nodeH / 2;
          const x2 = to.x, y2 = to.y + nodeH / 2;
          const mx = (x1 + x2) / 2;
          return (
            <g key={i}>
              <path d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`} fill="none" stroke="#94a3b8" strokeWidth="1.5" markerEnd="url(#arr)" />
              <text x={mx} y={(y1 + y2) / 2 - 4} textAnchor="middle" fontSize="9" fill="#67738a">{edge.kind}</text>
            </g>
          );
        })}
        {[...procs, ...tables].map((node) => {
          const pos = positions[node.id.toLowerCase()];
          if (!pos) return null;
          const color = colorMap[node.status] || '#67738a';
          const isTable = node.type === 'Table';
          const label = node.id.length > 16 ? node.id.slice(0, 14) + '…' : node.id;
          return (
            <g key={node.id}>
              <rect x={pos.x} y={pos.y} width={nodeW} height={nodeH} rx="5" fill={isTable ? '#f0fdf4' : '#eef2ff'} stroke={color} strokeWidth="1.5" />
              <text x={pos.x + 8} y={pos.y + 12} fontSize="10" fontWeight="700" fill={color}>{node.type}</text>
              <text x={pos.x + 8} y={pos.y + 24} fontSize="11" fill="#172033">{label}</text>
            </g>
          );
        })}
      </svg>
  );
}

export default function DependenciesTab() {
  const [relatedSql, setRelatedSql] = useState('');
  const [adding, setAdding] = useState(false);
  const { currentAnalysis, primarySql, primaryDbType, primarySourceType, setAnalysis, setActiveTab } = useAgentStore();

  if (!currentAnalysis) {
    return <div className="empty-state"><p>Run an analysis first to see dependencies.</p></div>;
  }

  const { dependency_map, summary } = currentAnalysis;
  const objects = dependency_map.nodes.filter(n => n.status === 'known' || n.type !== 'Table');
  const missing = summary.missing_references;

  const handleAdd = async () => {
    if (!relatedSql.trim()) return alert('Paste the referenced object definition first.');
    setAdding(true);
    try {
      await addRelatedObject(relatedSql, primaryDbType || 'SQL Server', 'auto');
      setRelatedSql('');
      if (primarySql) {
        const updated = await analyzeSQL(primarySql, primaryDbType, primarySourceType);
        setAnalysis(updated, primarySql, primaryDbType, primarySourceType, true);
      }
    } catch (e) {
      alert(e.message);
    } finally {
      setAdding(false);
    }
  };

  return (
    <section className="tab-content">
      <div className="grid dependency-layout">
        <article className="card">
          <div className="section-heading blue">Object Memory</div>
          <div className="memory-list">
            {objects.length ? objects.map((n) => (
              <div key={n.id} className="memory-object">
                <strong>{n.id}</strong>
                <span>{n.type} | {n.status}</span>
              </div>
            )) : <div className="memory-object"><strong>No objects yet</strong></div>}
          </div>
        </article>

        <article className="card">
          <div className="section-heading orange">Missing Referenced Objects</div>
          <div className="stack">
            {missing.length ? missing.map((name, i) => (
              <div key={i} className="item">
                <span className="badge">{i + 1}</span>
                <div><strong>{name}</strong><p>Paste this referenced object below to complete analysis.</p></div>
                <span className="pill High">High</span>
              </div>
            )) : (
              <div className="item">
                <span className="badge">✓</span>
                <div><strong>No missing references</strong><p>All referenced procedures are known.</p></div>
                <span className="pill Low">Low</span>
              </div>
            )}
          </div>
          <div className="add-object">
            <label>Paste referenced procedure/function</label>
            <textarea
              value={relatedSql}
              onChange={(e) => setRelatedSql(e.target.value)}
              spellCheck={false}
              style={{ minHeight: 160 }}
            />
            <button className="primary" onClick={handleAdd} disabled={adding}>
              {adding ? 'Adding...' : 'Add To Dependency Workspace'}
            </button>
          </div>
        </article>

        <article className="card" style={{ overflow: 'visible' }}>
          <div className="section-heading green">Dependency Map</div>
          <div className="dependency-map" style={{ overflow: 'auto', width: '100%', maxHeight: '500px' }}>
            <DepGraph depMap={dependency_map} />
          </div>
        </article>
      </div>
    </section>
  );
}
