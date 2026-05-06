const API_BASE = '/api';

export const analyzeSQL = async (sql, dbType, sourceType) => {
  const response = await fetch(`${API_BASE}/analyze`, {
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
