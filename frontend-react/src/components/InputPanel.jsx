import { useState, useEffect, useRef } from 'react';
import useAgentStore from '../store/agentStore';
import { analyzeSQL, analyzeMultiAgent, getMultiAgentStatus } from '../api/agentApi';

const SAMPLE_PROCEDURE = `CREATE OR ALTER PROCEDURE dbo.usp_ProcessCustomerOrders
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

const SOURCE_TYPES = [
  { label: 'Auto Detect', value: 'auto' },
  { label: 'Stored Procedure', value: 'Stored Procedure' },
  { label: 'View', value: 'View' },
  { label: 'Function', value: 'Function' },
  { label: 'DDL / DML', value: 'DML Script' },
];

const DB_TYPES = ['SQL Server', 'PostgreSQL', 'Oracle'];

export default function InputPanel() {
  const [sql, setSql] = useState('');
  const [dbType, setDbType] = useState('SQL Server');
  const [aiStatus, setAiStatus] = useState(null);
  const fileRef = useRef();

  const { selectedSource, setSelectedSource, setAnalysis, setLoading, loading, setActiveTab, currentAnalysis, analysisMode, setAnalysisMode } = useAgentStore();

  // Check AI status on component mount
  useEffect(() => {
    const checkAiStatus = async () => {
      try {
        const status = await getMultiAgentStatus();
        setAiStatus(status);
      } catch (error) {
        console.log('Multi-agent not available:', error.message);
        setAiStatus({ status: 'Not Available', error: error.message });
      }
    };
    checkAiStatus();
  }, []);

  useEffect(() => {
    const loadHandler = () => {
      setSql(SAMPLE_PROCEDURE);
      setSelectedSource('Stored Procedure');
    };
    const clearHandler = () => {
      setSql('');
      setSelectedSource('auto');
    };
    document.addEventListener('loadSample', loadHandler);
    document.addEventListener('clearInput', clearHandler);
    return () => {
      document.removeEventListener('loadSample', loadHandler);
      document.removeEventListener('clearInput', clearHandler);
    };
  }, []);

  const handleAnalyze = async () => {
    if (!sql.trim()) return alert('Paste SQL or upload a .sql file first.');
    setLoading(true);
    try {
      let result;
      if (analysisMode === 'ai') {
        if (!aiStatus?.connected) {
          throw new Error('AI is not available. Check your Groq API key and connection, or switch to Quick Analysis.');
        }
        result = await analyzeMultiAgent(sql, dbType, 'full_analysis');
      } else {
        result = await analyzeSQL(sql, dbType, selectedSource);
      }
      setAnalysis(result, sql, dbType, selectedSource);
      setActiveTab('diagnose');
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setSql('');
    setSelectedSource('auto');
  };

  const handleUpload = (e) => {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setSql(String(reader.result || ''));
    reader.readAsText(file);
  };

  return (
    <section className="input-panel card">
      <div className="panel-title">
        <strong>Input Source</strong>
      </div>

      <label>Input Method</label>
      <div className="radio-grid">
        {SOURCE_TYPES.map(({ label, value }) => (
          <button
            key={value}
            className={`choice ${selectedSource === value ? 'active' : ''}`}
            onClick={() => setSelectedSource(value)}
          >
            {label}
          </button>
        ))}
      </div>

      <label htmlFor="dbType">Database Type</label>
      <select id="dbType" value={dbType} onChange={(e) => setDbType(e.target.value)}>
        {DB_TYPES.map((t) => <option key={t}>{t}</option>)}
      </select>

      {/* AI Analysis Mode Selection */}
      <label>Analysis Mode</label>
      {aiStatus !== null && (
        <div style={{
          marginBottom: '10px',
          padding: '10px 12px',
          borderRadius: '6px',
          border: '1px solid',
          fontSize: '12px',
          lineHeight: '1.5',
          borderColor: aiStatus.connected ? '#bbf7d0' : '#fecdd3',
          background: aiStatus.connected ? '#f0fdf4' : '#fff1f2',
          color: aiStatus.connected ? '#07936f' : '#cf263f',
        }}>
          <span style={{
            display: 'inline-block',
            marginBottom: '6px',
            padding: '3px 10px',
            borderRadius: '999px',
            border: '1px solid',
            fontSize: '11px',
            fontWeight: '700',
            borderColor: aiStatus.connected ? '#bbf7d0' : '#fecdd3',
            background: aiStatus.connected ? '#dcfce7' : '#ffe4e6',
            color: aiStatus.connected ? '#07936f' : '#cf263f',
          }}>
            {aiStatus.connected ? '🤖 AI Connected' : 'AI Unavailable'}
          </span>
          <div style={{ marginTop: '6px' }}>
            {aiStatus.connected
              ? 'AI is available. Select AI Analysis for AI powered analysis. Or continue with Quick Analysis for instant rule-based results.'
              : 'AI is unavailable. Check your LLM API key, token limits, or internet connection. Switch to Quick Analysis to continue without AI.'}
          </div>
        </div>
      )}
      <div className="mode-buttons">
        <button
          className={`choice ${analysisMode === 'static' ? 'active' : ''}`}
          onClick={() => setAnalysisMode('static')}
        >
          Quick Analysis
        </button>
        <button
          className={`choice ${analysisMode === 'ai' ? 'active' : ''}`}
          onClick={() => setAnalysisMode('ai')}
          disabled={aiStatus !== null && !aiStatus.connected}
        >
          AI Analysis
        </button>
      </div>

      <div className="editor-label">
        <label htmlFor="sqlInput">DB Object / Query / Script</label>
        <button onClick={handleClear}>Clear</button>
      </div>
      <textarea
        id="sqlInput"
        spellCheck={false}
        placeholder="Paste your SQL here or upload a .sql file to begin..."
        value={sql}
        onChange={(e) => setSql(e.target.value)}
      />
      <input ref={fileRef} type="file" accept=".sql,.txt" hidden onChange={handleUpload} />
      <small className="hint">
        Paste a stored procedure, query, function, view, DDL, or DML script.
        If it calls another procedure, the agent will ask for that object too.
      </small>

      <div className="button-row">
        <button className="primary" onClick={handleAnalyze} disabled={loading}>
          {loading ? 'Analyzing...' : analysisMode === 'ai' ? '🚀 AI Analyze' : 'Quick Analyze'}
        </button>
        <button className="secondary" onClick={() => fileRef.current.click()}>
          Upload .sql
        </button>
      </div>


    </section>
  );
}
