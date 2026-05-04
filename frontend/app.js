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
  ['summaryView', 'Summary'],
  ['dependencyView', 'Dependencies'],
  ['optimizationView', 'Optimization'],
  ['planView', 'Execution Plan'],
  ['reportsView', 'Reports'],
  ['schemaView', 'DB Schema Agent']
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

const $ = (id) => document.getElementById(id);

function init() {
  renderNav();
  renderTabs();
  bindEvents();
  $('sqlInput').value = sampleProcedure;
  $('schemaPrompt').value = sampleSchemaPrompt;
  toast('Sample stored procedure loaded. Run analysis to begin.');
  renderEmpty();
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

  document.querySelectorAll('.nav-item').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      routeNav(button.dataset.nav);
    });
  });

  $('analyzeBtn').addEventListener('click', analyze);
  $('addRelatedBtn').addEventListener('click', addRelatedObject);
  $('clearBtn').addEventListener('click', () => {
    $('sqlInput').value = '';
    toast('Input cleared');
  });
  $('uploadBtn').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', uploadFile);
  $('loadSampleBtn').addEventListener('click', () => {
    $('sqlInput').value = sampleProcedure;
    selectedSource = 'Stored Procedure';
    document.querySelectorAll('.choice').forEach((item) => item.classList.toggle('active', item.dataset.source === 'Stored Procedure'));
    toast('Sample stored procedure loaded');
  });
  $('historyBtn').addEventListener('click', showHistory);
  $('saveReportBtn').addEventListener('click', () => downloadArtifact('db_review_report', 'db-review-report.md'));
  $('helpBtn').addEventListener('click', () => toast('Paste a SQL object, analyze it, then add missing referenced procedures from the Dependencies tab.'));
  $('designSchemaBtn').addEventListener('click', designSchema);
}

function routeNav(name) {
  const tabByNav = {
    'DB Schema Agent': 'schemaView',
    'Dependency Workspace': 'dependencyView',
    'Index Advisor': 'optimizationView',
    'Performance Monitor': 'summaryView',
    'Schema Explorer': 'dependencyView',
    'Stored Procedures': 'dependencyView',
    'Dashboard': 'summaryView',
    'Analyze DB Object': 'summaryView',
    'Settings': 'reportsView'
  };
  setTab(tabByNav[name] || 'summaryView');
  toast(`${name} opened`);
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
    renderAnalysis(currentAnalysis);
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
    currentAnalysis = await postJson('/api/add-object', {
      sql,
      db_type: $('dbType').value,
      source_type: 'auto'
    });
    $('relatedSql').value = '';
    renderAnalysis(currentAnalysis);
    setTab('dependencyView');
    toast(`Added ${currentAnalysis.object.name} to object memory`);
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
  renderAnalysis(currentAnalysis);
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
    setTab('schemaView');
    toast(`Schema Agent produced ${currentSchema.tables.length} table(s) and ${currentSchema.relationships.length} relationship(s)`);
  } catch (error) {
    toast(error.message);
  } finally {
    $('designSchemaBtn').textContent = 'Design / Review Schema';
  }
}

function renderAnalysis(data) {
  renderSummary(data);
  renderMetrics(data.metrics);
  renderFindings(data.findings);
  renderSuggestions(data.suggestions);
  renderImpact(data.impact);
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

function renderMetrics(metrics) {
  const values = [
    ['Execution Time', `${metrics.execution_time_ms} ms`, `${metrics.improvement_potential_pct}% can improve`],
    ['CPU Usage', `${metrics.cpu_usage_pct}%`, metrics.risk_level],
    ['Logical Reads', number(metrics.logical_reads), 'Can be reduced'],
    ['Rows Returned', number(metrics.rows_returned), 'Estimated'],
    ['Index Usage', `${metrics.index_usage_pct}%`, 'Can be improved'],
    ['Query Cost', metrics.query_cost, metrics.confidence]
  ];
  $('metricsGrid').innerHTML = values.map(([label, value, note]) => `
    <div class="metric"><small>${escapeHtml(label)}</small><strong>${escapeHtml(String(value))}</strong><em>${escapeHtml(String(note))}</em></div>
  `).join('');
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

  const edges = data.dependency_map.edges;
  $('dependencyMap').innerHTML = edges.length ? edges.map((edge) => `
    <div class="edge">
      <strong>${escapeHtml(edge.from)}</strong>
      <em>${escapeHtml(edge.kind)}</em>
      <strong>${escapeHtml(edge.to)}</strong>
    </div>
  `).join('') : '<div class="memory-object"><strong>No dependency edges yet</strong><span>Stored procedure calls, joins, and table references will appear here.</span></div>';
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
  $('erdSummary').textContent = schema.erd_summary;
  renderSchemaOutputs();
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

function renderEmpty() {
  $('summaryGrid').innerHTML = '';
  $('metricsGrid').innerHTML = '';
  $('findingsList').innerHTML = itemTemplate(1, 'Waiting for SQL input', 'Paste a query or stored procedure and run analysis.', 'Low');
  $('suggestionsList').innerHTML = itemTemplate(1, 'No suggestions yet', 'Recommendations appear after analysis.', 'Low');
  $('impactList').innerHTML = itemTemplate(1, 'No impact yet', 'Risk and dependent objects appear after analysis.', 'Low');
  $('memoryList').innerHTML = '<div class="memory-object"><strong>No objects yet</strong><span>Run analysis to populate memory.</span></div>';
  $('missingList').innerHTML = itemTemplate(1, 'No missing references yet', 'Nested procedure calls will appear here.', 'Low');
  $('dependencyMap').innerHTML = '<div class="memory-object"><strong>No dependency map yet</strong><span>Analyze a SQL object to create the first map.</span></div>';
  $('optimizedSql').textContent = '-- Run analysis first.';
  $('indexScripts').textContent = '-- Run analysis first.';
  $('planList').innerHTML = '';
  renderOutputs();
  $('schemaTables').innerHTML = '<div class="schema-table"><strong>No schema yet</strong><span>Use DB Schema Agent to design or review a schema.</span></div>';
  $('schemaReview').innerHTML = itemTemplate(1, 'No schema review yet', 'Schema quality findings appear after design/review.', 'Low');
  $('migrationScript').textContent = '-- Run DB Schema Agent first.';
  $('erdSummary').textContent = 'erDiagram';
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
