const navItems = [
  ['Dashboard', 'D'],
  ['Analyze DB Object', 'A'],
  ['Stored Procedures', 'SP'],
  ['DB Schema Agent', 'DB'],
  ['Dependency Workspace', 'DW'],
  ['Index Advisor', 'IX'],
  ['Performance Monitor', 'PM'],
  ['Schema Explorer', 'SE'],
  ['Settings', 'S']
];

const tabs = [
  ['summaryView', 'Diagnose'],
  ['dependencyView', 'Dependencies'],
  ['optimizationView', 'Fix'],
  ['reportsView', 'Deploy']
];

const schemaTabs = [
  ['schemaView', 'Schema Agent']
];

const sampleProcedure = `CREATE OR ALTER PROCEDURE dbo.usp_ProcessCustomerOrders
  @CustomerId INT,
  @StartDate DATE,
  @Status VARCHAR(20)
AS
BEGIN
  SET NOCOUNT ON;

  CREATE TABLE #OrderWork
  (
    OrderId INT,
    CustomerId INT,
    OrderDate DATETIME,
    Status VARCHAR(20),
    TotalAmount DECIMAL(18,2)
  );

  INSERT INTO #OrderWork
  SELECT *
  FROM dbo.Orders o WITH (NOLOCK)
  INNER JOIN dbo.Customers c ON o.CustomerId = c.CustomerId
  LEFT JOIN dbo.OrderItems oi ON o.OrderId = oi.OrderId
  WHERE YEAR(o.OrderDate) >= YEAR(@StartDate)
    AND o.Status = @Status
    AND c.CustomerId = @CustomerId
  ORDER BY o.OrderDate DESC;

  DECLARE order_cursor CURSOR FOR
    SELECT OrderId FROM #OrderWork;

  OPEN order_cursor;
  FETCH NEXT FROM order_cursor INTO @CustomerId;
  WHILE @@FETCH_STATUS = 0
  BEGIN
    EXEC dbo.usp_UpdateOrderRisk @CustomerId;
    FETCH NEXT FROM order_cursor INTO @CustomerId;
  END

  CLOSE order_cursor;
  DEALLOCATE order_cursor;
END`;

const sampleSchemaPrompt = `Design a customer order management schema with customers, orders, order items, products, and payments. Include relationships, constraints, indexes, audit columns, migration script, rollback script, and identify schema quality issues.`;

let selectedSource = 'auto';
let currentAnalysis = null;
let currentSchema = null;
let primarySql = null;
let primaryDbType = null;
let primarySourceType = null;
let currentMode = 'analyze';

const $ = (id) => document.getElementById(id);

function init() {
  renderTabs();
  bindEvents();
  $('schemaPrompt').value = sampleSchemaPrompt;
  toast('Paste your SQL here or upload a .sql file to begin...');
  renderEmpty();
  setMode('analyze');
}

function renderNav() {
  $('sideNav').innerHTML = navItems.map(([name, icon], index) => `
    <button class="nav-item ${index === 1 ? 'active' : ''}" data-nav="${name}">
      <span class="nav-icon">${icon}</span>
      <span>${name}</span>
    </button>
  `).join('');
}

function renderTabs() {
  $('tabs').innerHTML = tabs.map(([id, name], index) => `
    <button class="tab-btn ${index === 0 ? 'active' : ''}" data-tab="${id}">${name}</button>
  `).join('');
}

function setMode(mode) {
  currentMode = mode;
  const isAnalyze = mode === 'analyze';
  $('modeTitle').textContent = isAnalyze ? 'Analyze SQL Object' : 'DB Schema Agent';
  $('modeDesc').textContent = isAnalyze
    ? 'Paste a stored procedure, query, function, view, DDL, or DML \u2014 get a full diagnosis, optimization plan, and deployment package.'
    : 'Describe a schema in plain English or paste existing DDL \u2014 get tables, relationships, migration script, rollback, and ERD.';
  document.querySelector('.workspace').classList.toggle('schema-mode', !isAnalyze);
  $('modeAnalyzeNav').classList.toggle('active', isAnalyze);
  $('modeSchemaNav').classList.toggle('active', !isAnalyze);
  $('tabs').style.display = isAnalyze ? '' : 'none';
  document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
  if (isAnalyze) {
    $('summaryView').classList.add('active');
    document.querySelector('.input-panel').style.display = '';
  } else {
    $('schemaView').classList.add('active');
    document.querySelector('.input-panel').style.display = 'none';
  }
}

function bindEvents() {
  document.querySelectorAll('.choice').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.choice').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      selectedSource = button.dataset.source;
    });
  });

  document.querySelectorAll('.tab-btn').forEach((button) => {
    button.addEventListener('click', () => setTab(button.dataset.tab));
  });

  $('modeAnalyzeNav').addEventListener('click', () => setMode('analyze'));
  $('modeSchemaNav').addEventListener('click', () => setMode('schema'));

  $('analyzeBtn').addEventListener('click', analyze);
  $('addRelatedBtn').addEventListener('click', addRelatedObject);
  $('clearBtn').addEventListener('click', () => {
    $('sqlInput').value = '';
    primarySql = null;
    primaryDbType = null;
    primarySourceType = null;
    selectedSource = 'auto';
    document.querySelectorAll('.choice').forEach((item) => item.classList.toggle('active', item.dataset.source === 'auto'));
    toast('Input cleared');
  });
  $('uploadBtn').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', uploadFile);
  $('loadSampleBtn').addEventListener('click', () => {
    setMode('analyze');
    $('sqlInput').value = sampleProcedure;
    selectedSource = 'Stored Procedure';
    document.querySelectorAll('.choice').forEach((item) => item.classList.toggle('active', item.dataset.source === 'Stored Procedure'));
    toast('Sample stored procedure loaded — click Analyze Object to begin.');
  });
  $('saveReportBtn').addEventListener('click', () => downloadArtifact('db_review_report', 'db-review-report.md'));
  $('helpBtn').addEventListener('click', () => toast('Analyze mode: paste SQL and analyze. Schema mode: describe a schema and design it.'));
  $('newSessionBtn').addEventListener('click', async () => {
    await fetch('/api/reset', { method: 'POST' });
    currentAnalysis = null;
    currentSchema = null;
    primarySql = null;
    primaryDbType = null;
    primarySourceType = null;
    $('sqlInput').value = '';
    setMode('analyze');
    renderEmpty();
    toast('Session cleared — ready for a new analysis.');
  });
  $('designSchemaBtn').addEventListener('click', designSchema);
}

function highlightDetectedType(objectType) {
  const typeMap = {
    'Stored Procedure': 'Stored Procedure',
    'SQL Query':        'SQL Query',
    'View':             'View',
    'Function':         'Function',
    'DDL Script':       'DML Script',
    'DML Script':       'DML Script',
  };
  const match = typeMap[objectType];
  if (!match) return;
  document.querySelectorAll('.choice').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.source === match);
  });
  selectedSource = match;
}

function setTab(id) {
  document.querySelectorAll('.tab-btn').forEach((button) => button.classList.toggle('active', button.dataset.tab === id));
  document.querySelectorAll('.tab-view').forEach((view) => view.classList.toggle('active', view.id === id));
}

async function analyze() {
  const sql = $('sqlInput').value.trim();
  if (!sql) {
    toast('Paste SQL or upload a .sql file first.');
    return;
  }
  $('analyzeBtn').textContent = 'Analyzing...';
  try {
    currentAnalysis = await postJson('/api/analyze', {
      sql,
      db_type: $('dbType').value,
      source_type: selectedSource
    });
    primarySql = sql;
    primaryDbType = $('dbType').value;
    primarySourceType = selectedSource;
    renderAnalysis(currentAnalysis);
    highlightDetectedType(currentAnalysis.summary.object_type);
    toast(`Analyzed ${currentAnalysis.object.name}`);
  } catch (error) {
    toast(error.message);
  } finally {
    $('analyzeBtn').textContent = 'Analyze Object';
  }
}

async function addRelatedObject() {
  const sql = $('relatedSql').value.trim();
  if (!sql) {
    toast('Paste the referenced object definition first.');
    return;
  }
  $('addRelatedBtn').textContent = 'Adding...';
  try {
    const added = await postJson('/api/add-object', {
      sql,
      db_type: $('dbType').value,
      source_type: 'auto'
    });
    $('relatedSql').value = '';
    toast(`Added ${added.object.name} to object memory. Re-analyzing primary object...`);

    if (primarySql) {
      currentAnalysis = await postJson('/api/analyze', {
        sql: primarySql,
        db_type: primaryDbType,
        source_type: primarySourceType
      });
      renderAnalysis(currentAnalysis);
      setTab('summaryView');
      highlightDetectedType(currentAnalysis.summary.object_type);
      toast(`Complete — ${added.object.name} resolved. Showing updated analysis for ${currentAnalysis.object.name}.`);
    } else {
      renderAnalysis(added);
      setTab('dependencyView');
      toast(`Added ${added.object.name} to object memory`);
    }
  } catch (error) {
    toast(error.message);
  } finally {
    $('addRelatedBtn').textContent = 'Add To Dependency Workspace';
  }
}

function uploadFile(event) {
  const file = event.target.files[0];
  event.target.value = '';
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    $('sqlInput').value = String(reader.result || '');
    toast(`${file.name} loaded`);
  };
  reader.readAsText(file);
}

async function showHistory() {
  const history = await fetch('/api/history').then((res) => res.json());
  if (!history.length) {
    toast('No history yet. Run an analysis first.');
    return;
  }
  currentAnalysis = history[0];
  setMode('analyze');
  renderAnalysis(currentAnalysis);
  setTab('summaryView');
  toast(`Loaded latest history item: ${currentAnalysis.object.name}`);
}

async function designSchema() {
  const prompt = $('schemaPrompt').value.trim();
  if (!prompt) {
    toast('Describe a schema requirement or paste DDL first.');
    return;
  }
  $('designSchemaBtn').textContent = 'Designing...';
  try {
    currentSchema = await postJson('/api/schema/design', {
      prompt,
      db_type: $('dbType').value
    });
    renderSchema(currentSchema);
    toast(`Schema Agent produced ${currentSchema.tables.length} table(s) and ${currentSchema.relationships.length} relationship(s)`);
  } catch (error) {
    toast(error.message);
  } finally {
    $('designSchemaBtn').textContent = 'Design / Review Schema';
  }
}

function renderAnalysis(data) {
  renderSummary(data);
  renderRiskCard(data.metrics, data.findings);
  renderFindings(data.findings);
  renderSuggestions(data.suggestions);
  renderImpact(data.impact);
  renderDeploymentReadiness(data.findings, data.suggestions);
  renderMissingRefBanner(data.summary.missing_references);
  renderDependencies(data);
  renderOptimization(data);
  renderPlan(data.execution_plan);
  renderOutputs();
}

function renderSummary(data) {
  const summary = data.summary;
  const values = [
    ['Object Type', summary.object_type],
    ['Execution Type', summary.execution_type],
    ['Tables Involved', summary.tables_involved.join(', ') || 'None detected'],
    ['Joins Used', String(summary.joins_used.length)],
    ['Filters Applied', String(summary.filters_applied.length)],
    ['Group By', summary.group_by ? 'Yes' : 'No'],
    ['Order By', summary.order_by ? 'Yes' : 'No'],
    ['Missing Objects', summary.missing_references.length ? summary.missing_references.join(', ') : 'None']
  ];
  $('summaryGrid').innerHTML = values.map(([label, value]) => `
    <div class="summary-cell"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>
  `).join('');
  $('explanation').textContent = summary.explanation;
}

function renderRiskCard(metrics, findings) {
  const high = findings.filter(f => f.severity === 'High').length;
  const medium = findings.filter(f => f.severity === 'Medium').length;
  const low = findings.filter(f => f.severity === 'Low').length;
  const levelClass = metrics.risk_level === 'High' ? 'risk-high' : metrics.risk_level === 'Medium' ? 'risk-medium' : 'risk-low';
  $('metricsGrid').innerHTML = `
    <div class="risk-card ${levelClass}">
      <div class="risk-label">Risk Level</div>
      <div class="risk-level">${escapeHtml(metrics.risk_level)}</div>
      <div class="risk-counts">
        <span class="pill High">${high} High</span>
        <span class="pill Medium">${medium} Medium</span>
        <span class="pill Low">${low} Low</span>
      </div>
      <div class="risk-potential">Improvement potential: ${escapeHtml(String(metrics.improvement_potential_pct))}% after fixes</div>
      <div class="risk-note">Static analysis — validate with actual execution plan</div>
    </div>
  `;
}

function renderFindings(findings) {
  $('findingsList').innerHTML = findings.slice(0, 6).map((item, index) => itemTemplate(index + 1, item.title, item.detail, item.severity)).join('');
}

function renderSuggestions(suggestions) {
  $('suggestionsList').innerHTML = suggestions.slice(0, 6).map((item, index) => itemTemplate(index + 1, item.title, item.recommendation, item.impact)).join('');
}

function renderImpact(impact) {
  const values = [
    ['Affected Tables', impact.affected_tables.join(', ') || 'None detected'],
    ['Dependent Objects', impact.dependent_objects.join(', ') || 'None detected'],
    ['Missing Objects', impact.missing_objects.join(', ') || 'None'],
    ['Downstream', impact.downstream.join(', ')],
    ['Risk Level', impact.risk_level],
    ['Deployment Complexity', impact.deployment_complexity],
    ['Rollback', impact.rollback]
  ];
  $('impactList').innerHTML = values.map(([label, value], index) => itemTemplate(index + 1, label, value, '')).join('');
}

function renderDependencies(data) {
  const objects = data.dependency_map.nodes.filter((node) => node.status === 'known' || node.type !== 'Table');
  $('memoryList').innerHTML = objects.length ? objects.map((node) => `
    <div class="memory-object">
      <strong>${escapeHtml(node.id)}</strong>
      <span>${escapeHtml(node.type)} | ${escapeHtml(node.status)}</span>
    </div>
  `).join('') : '<div class="memory-object"><strong>No objects yet</strong><span>Run analysis to populate memory.</span></div>';

  const missing = data.summary.missing_references;
  $('missingList').innerHTML = missing.length ? missing.map((name, index) => itemTemplate(index + 1, name, 'Paste this referenced object below to complete dependency-aware analysis.', 'High')).join('') : itemTemplate(1, 'No missing references', 'All detected referenced procedures are already known in this session.', 'Low');

  renderDepGraph(data.dependency_map);
}

function renderDepGraph(depMap) {
  const svg = $('depGraph');
  if (!svg) return;
  const { nodes, edges } = depMap;
  if (!edges.length) {
    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#67738a" font-size="13" dy=".3em">No dependency edges yet. Analyze a SQL object to build the map.</text>';
    return;
  }

  const nodeW = 148, nodeH = 36, colGap = 80, rowGap = 54;
  const procs = nodes.filter(n => n.type !== 'Table');
  const tables = nodes.filter(n => n.type === 'Table');

  const positions = {};
  procs.forEach((n, i) => { positions[n.id.toLowerCase()] = { x: 20, y: 20 + i * (nodeH + rowGap) }; });
  tables.forEach((n, i) => { positions[n.id.toLowerCase()] = { x: 20 + nodeW + colGap, y: 20 + i * (nodeH + rowGap) }; });

  const totalH = Math.max(procs.length, tables.length) * (nodeH + rowGap) + 20;
  svg.setAttribute('height', Math.max(totalH, 120));

  const colorMap = { known: '#2f58ff', missing: '#cf263f', referenced: '#07936f' };

  let markup = '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#94a3b8"/></marker></defs>';

  edges.forEach(edge => {
    const from = positions[edge.from.toLowerCase()];
    const to = positions[edge.to.toLowerCase()];
    if (!from || !to) return;
    const x1 = from.x + nodeW, y1 = from.y + nodeH / 2;
    const x2 = to.x, y2 = to.y + nodeH / 2;
    const mx = (x1 + x2) / 2;
    markup += `<path d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}" fill="none" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arr)"/>`;
    const label = edge.kind;
    markup += `<text x="${mx}" y="${(y1 + y2) / 2 - 4}" text-anchor="middle" font-size="10" fill="#67738a">${escapeHtml(label)}</text>`;
  });

  [...procs, ...tables].forEach(node => {
    const pos = positions[node.id.toLowerCase()];
    if (!pos) return;
    const color = colorMap[node.status] || '#67738a';
    const isTable = node.type === 'Table';
    markup += `<rect x="${pos.x}" y="${pos.y}" width="${nodeW}" height="${nodeH}" rx="6" fill="${isTable ? '#f0fdf4' : '#eef2ff'}" stroke="${color}" stroke-width="1.5"/>`;
    markup += `<text x="${pos.x + 10}" y="${pos.y + 13}" font-size="11" font-weight="700" fill="${color}">${escapeHtml(node.type)}</text>`;
    const label = node.id.length > 18 ? node.id.slice(0, 16) + '\u2026' : node.id;
    markup += `<text x="${pos.x + 10}" y="${pos.y + 27}" font-size="12" fill="#172033">${escapeHtml(label)}</text>`;
  });

  svg.innerHTML = markup;
}

function renderOptimization(data) {
  $('optimizedSql').textContent = data.optimized_sql || '-- Run analysis first.';
  $('indexScripts').textContent = (data.index_scripts || []).join('\n\n') || '-- No index scripts generated.';
}

function renderPlan(plan) {
  $('planList').innerHTML = plan.operators.map((item) => `
    <div class="plan-op">
      <strong>${escapeHtml(item.operator)} <span class="pill ${escapeHtml(item.risk)}">${escapeHtml(item.risk)}</span></strong>
      <p>${escapeHtml(item.note)}</p>
    </div>
  `).join('') + `
    <div class="plan-op"><strong>Statistics</strong><p>${escapeHtml(plan.statistics)}</p></div>
    <div class="plan-op"><strong>Memory Grant</strong><p>${escapeHtml(plan.memory_grant)}</p></div>
  `;
}

function renderOutputs() {
  const outputs = [
    ['optimized_sql', 'Optimized SQL', 'Draft optimized SQL or stored procedure with review notes.', 'optimized-sql.sql'],
    ['index_script', 'Index Recommendation', 'Generated index scripts based on filters and joins.', 'index-recommendations.sql'],
    ['execution_plan_analysis', 'Execution Plan Analysis', 'Plan-operator risks and validation notes.', 'execution-plan-analysis.md'],
    ['test_data_generator', 'Test Data Generator', 'Representative test-data guidance.', 'test-data-generator.sql'],
    ['db_review_report', 'DB Review Report', 'Complete findings, risk, impact, and recommendations.', 'db-review-report.md'],
    ['comparison_report', 'Before vs After Report', 'Expected changes and improvement areas.', 'comparison-report.md']
  ];
  $('outputsGrid').innerHTML = outputs.map(([type, title, desc, filename]) => `
    <button class="output-card" data-artifact="${type}" data-filename="${filename}">
      <strong>${title}</strong>
      <span>${desc}</span>
      <small>Download</small>
    </button>
  `).join('');
  document.querySelectorAll('.output-card').forEach((button) => {
    button.addEventListener('click', () => downloadArtifact(button.dataset.artifact, button.dataset.filename));
  });
}

function renderSchema(schema) {
  $('schemaTables').innerHTML = schema.tables.map((table) => `
    <div class="schema-table">
      <strong>${escapeHtml(table.name)}</strong>
      <span>${table.columns.map((col) => `${escapeHtml(col.name)} ${escapeHtml(col.type)}${col.role ? ` (${escapeHtml(col.role)})` : ''}`).join(', ')}</span>
    </div>
  `).join('') + (schema.relationships.length ? schema.relationships.map((rel) => `
    <div class="edge">
      <strong>${escapeHtml(rel.from)}</strong>
      <em>FK ${escapeHtml(rel.column)}</em>
      <strong>${escapeHtml(rel.to)}</strong>
    </div>
  `).join('') : '');
  $('schemaReview').innerHTML = schema.quality_review.map((item, index) => itemTemplate(index + 1, item.title, item.detail, item.severity)).join('');
  $('migrationScript').textContent = schema.migration_script;
  renderErd(schema.erd_summary);
  renderSchemaOutputs();
}

async function renderErd(erdText) {
  const container = $('erdDiagram');
  if (!erdText || !erdText.trim() || erdText.trim() === 'erDiagram') {
    container.innerHTML = '<p class="erd-empty">No relationships to diagram yet.</p>';
    return;
  }
  try {
    if (window.mermaid) {
      window.mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });
      const id = 'erd' + Date.now();
      const { svg } = await window.mermaid.render(id, erdText.trim());
      container.innerHTML = svg;
    } else {
      container.innerHTML = `<pre class="code-output small-code">${escapeHtml(erdText)}</pre>`;
    }
  } catch (e) {
    console.error('Mermaid error:', e, '\nERD text:', erdText);
    container.innerHTML = `<pre class="code-output small-code">${escapeHtml(erdText)}</pre>`;
  }
}

function renderSchemaOutputs() {
  const outputs = [
    ['ddl_script', 'DDL Script', 'Create tables, keys, relationships, and indexes.', 'schema-migration.sql'],
    ['rollback_script', 'Rollback Script', 'Drop generated schema objects in safe order.', 'schema-rollback.sql'],
    ['erd_summary', 'ERD Summary', 'Mermaid ERD relationship summary.', 'schema-erd.mmd'],
    ['schema_review_report', 'Schema Review Report', 'Quality, relationships, impact, and scripts.', 'schema-review-report.md'],
    ['migration_plan', 'Migration Plan', 'Deployment sequence and validation checklist.', 'schema-migration-plan.md']
  ];
  $('schemaOutputs').innerHTML = outputs.map(([type, title, desc, filename]) => `
    <button class="output-card" data-schema-artifact="${type}" data-filename="${filename}">
      <strong>${title}</strong>
      <span>${desc}</span>
      <small>Download</small>
    </button>
  `).join('');
  document.querySelectorAll('[data-schema-artifact]').forEach((button) => {
    button.addEventListener('click', () => downloadSchemaArtifact(button.dataset.schemaArtifact, button.dataset.filename));
  });
}

function renderDeploymentReadiness(findings, suggestions) {
  const high = findings.filter(f => f.severity === 'High' && f.title !== 'No major rule-based issue detected');
  const medium = findings.filter(f => f.severity === 'Medium');
  const ready = high.length === 0;
  const statusClass = ready ? 'ready-yes' : 'ready-no';
  const statusIcon = ready ? '✅' : '❌';
  const statusText = ready ? 'READY TO DEPLOY' : 'NOT READY — fix High issues first';
  const highLines = high.map(f => `<li>${escapeHtml(f.title)}</li>`).join('');
  const medLines = medium.slice(0, 3).map(f => `<li>${escapeHtml(f.title)}</li>`).join('');
  $('deploymentReadiness').innerHTML = `
    <div class="readiness-card ${statusClass}">
      <div class="readiness-status">${statusIcon} ${escapeHtml(statusText)}</div>
      ${high.length ? `<ul class="readiness-list">${highLines}</ul>` : ''}
      ${medium.length ? `<div class="readiness-medium">⚠️ ${medium.length} Medium issue${medium.length > 1 ? 's' : ''} recommended before deploy</div><ul class="readiness-list muted">${medLines}</ul>` : ''}
    </div>
  `;
}

function renderMissingRefBanner(missing) {
  const banner = $('missingRefBanner');
  if (!missing || missing.length === 0) {
    banner.style.display = 'none';
    return;
  }
  banner.style.display = 'flex';
  banner.innerHTML = `
    <span>⚠️ Missing dependenc${missing.length > 1 ? 'ies' : 'y'} detected: <strong>${missing.map(escapeHtml).join(', ')}</strong> — paste in Dependencies tab to complete analysis.</span>
    <button onclick="setTab('dependencyView')">Go to Dependencies →</button>
  `;
}

function renderEmpty() {
  $('summaryGrid').innerHTML = '';
  $('metricsGrid').innerHTML = '';
  $('deploymentReadiness').innerHTML = '';
  $('missingRefBanner').style.display = 'none';
  $('findingsList').innerHTML = itemTemplate(1, 'Waiting for SQL input', 'Paste a query or stored procedure and run analysis.', 'Low');
  $('suggestionsList').innerHTML = itemTemplate(1, 'No suggestions yet', 'Recommendations appear after analysis.', 'Low');
  $('impactList').innerHTML = itemTemplate(1, 'No impact yet', 'Risk and dependent objects appear after analysis.', 'Low');
  $('memoryList').innerHTML = '<div class="memory-object"><strong>No objects yet</strong><span>Run analysis to populate memory.</span></div>';
  $('missingList').innerHTML = itemTemplate(1, 'No missing references yet', 'Nested procedure calls will appear here.', 'Low');
  const svg = $('depGraph');
  if (svg) svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#67738a" font-size="13" dy=".3em">No dependency map yet. Analyze a SQL object to build the map.</text>';
  $('optimizedSql').textContent = '-- Run analysis first.';
  $('indexScripts').textContent = '-- Run analysis first.';
  $('planList').innerHTML = '';
  renderOutputs();
  $('schemaTables').innerHTML = '<div class="schema-table"><strong>No schema yet</strong><span>Use DB Schema Agent to design or review a schema.</span></div>';
  $('schemaReview').innerHTML = itemTemplate(1, 'No schema review yet', 'Schema quality findings appear after design/review.', 'Low');
  $('migrationScript').textContent = '-- Run DB Schema Agent first.';
  $('erdDiagram').innerHTML = '<p class="erd-empty">Run DB Schema Agent to see the ERD diagram.</p>';
  renderSchemaOutputs();
}

function itemTemplate(num, title, text, severity) {
  return `
    <div class="item">
      <span class="badge">${num}</span>
      <div><strong>${escapeHtml(title)}</strong><p>${escapeHtml(text || '')}</p></div>
      ${severity ? `<span class="pill ${escapeHtml(severity)}">${escapeHtml(severity)}</span>` : ''}
    </div>
  `;
}

async function downloadArtifact(type, filename) {
  if (!currentAnalysis) {
    toast('Run an analysis before downloading reports.');
    return;
  }
  const text = await fetch('/api/artifact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_type: type, analysis: currentAnalysis })
  }).then((res) => res.text());
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
  toast(`${filename} downloaded`);
}

function downloadSchemaArtifact(type, filename) {
  if (!currentSchema) {
    toast('Run DB Schema Agent before downloading schema outputs.');
    return;
  }
  const text = currentSchema.artifacts[type] || '';
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
  toast(`${filename} downloaded`);
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function toast(message) {
  $('toast').textContent = message;
}

function number(value) {
  return new Intl.NumberFormat().format(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

init();
