const API_BASE = '/api';
const FETCH_OPTS = { credentials: 'include' };

// Multi-Agent Analysis (Groq-powered)
export const analyzeMultiAgent = async (sql, dbType, analysisType = 'full_analysis') => {
  const response = await fetch(`${API_BASE}/analyze-multi-agent`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql, db_type: dbType, analysis_type: analysisType }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Multi-agent analysis failed');
  }
  return response.json();
};

// Check AI System Status
export const getMultiAgentStatus = async () => {
  const response = await fetch(`${API_BASE}/ai-status`, { ...FETCH_OPTS });
  if (!response.ok) {
    throw new Error('Failed to get AI status');
  }
  return response.json();
};

// Regular Analysis (rule-based, no AI)
export const analyzeSQL = async (sql, dbType, sourceType) => {
  const response = await fetch(`${API_BASE}/analyze`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql, db_type: dbType, source_type: sourceType }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Analysis failed');
  }
  return response.json();
};

export const addRelatedObject = async (sql, dbType, sourceType) => {
  const response = await fetch(`${API_BASE}/add-object`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql, db_type: dbType, source_type: sourceType }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Add object failed');
  }
  return response.json();
};

export const designSchema = async (prompt, dbType) => {
  const response = await fetch(`${API_BASE}/schema/design`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, db_type: dbType }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Schema design failed');
  }
  return response.json();
};

export const designSchemaAI = async (prompt, dbType) => {
  const response = await fetch(`${API_BASE}/schema/design-ai`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, db_type: dbType }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'AI schema design failed');
  }
  return response.json();
};

export const suggestDbName = async (prompt) => {
  const response = await fetch(`${API_BASE}/schema/suggest-db-name`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  const data = await response.json();
  return data.db_name || 'NewDatabaseDB';
};

export const executeInDB = async (connectionString, ddlScript) => {
  const response = await fetch(`${API_BASE}/db/execute`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ connection_string: connectionString, ddl_script: ddlScript }),
  });
  const data = await response.json();
  if (!data.success) throw new Error(data.detail || data.error || 'Execution failed');
  return data;
};

export const scanDatabase = async (connectionString) => {
  const response = await fetch(`${API_BASE}/db/scan`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ connection_string: connectionString }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Scan failed');
  return data;
};

export const fetchProcedure = async (connectionString, procedureName) => {
  const response = await fetch(`${API_BASE}/db/fetch-procedure`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ connection_string: connectionString, procedure_name: procedureName }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Fetch failed');
  return data;
};

export const deployOptimized = async (connectionString, optimizedSql, procedureName) => {
  const response = await fetch(`${API_BASE}/db/deploy-optimized`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ connection_string: connectionString, optimized_sql: optimizedSql, procedure_name: procedureName }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Deploy failed');
  return data;
};

export const fetchDeployLog = async (connectionString) => {
  const response = await fetch(`${API_BASE}/db/deploy-log`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ connection_string: connectionString }),
  });
  const data = await response.json();
  if (!response.ok) return {};
  return data;
};

export const resetSession = async () => {
  await fetch(`${API_BASE}/reset`, { ...FETCH_OPTS, method: 'POST' });
};

export const downloadArtifact = async (artifactType, analysis) => {
  const response = await fetch(`${API_BASE}/artifact`, {
    ...FETCH_OPTS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_type: artifactType, analysis }),
  });
  return response.text();
};
