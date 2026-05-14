const API_BASE = '/api';
const TEST_MODE = false; // Set to false to use normal API

// Multi-Agent Analysis (Groq-powered)
export const analyzeMultiAgent = async (sql, dbType, analysisType = 'full_analysis') => {
  const response = await fetch(`${API_BASE}/analyze-multi-agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      sql, 
      db_type: dbType, 
      analysis_type: analysisType 
    }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Multi-agent analysis failed');
  }
  return response.json();
};

// Check AI System Status
export const getMultiAgentStatus = async () => {
  const response = await fetch(`${API_BASE}/ai-status`);
  if (!response.ok) {
    throw new Error('Failed to get AI status');
  }
  return response.json();
};

// Regular Analysis (Static + Basic AI)
export const analyzeSQL = async (sql, dbType, sourceType) => {
  const endpoint = TEST_MODE ? 'http://127.0.0.1:8021/api/test-analyze' : `${API_BASE}/analyze`;
  
  const response = await fetch(endpoint, {
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

export const resetSession = async () => {
  await fetch(`${API_BASE}/reset`, { method: 'POST' });
};

export const downloadArtifact = async (artifactType, analysis) => {
  const response = await fetch(`${API_BASE}/artifact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_type: artifactType, analysis }),
  });
  return response.text();
};
