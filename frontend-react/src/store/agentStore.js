import { create } from 'zustand';

const useAgentStore = create((set) => ({
  mode: 'schema',
  analysisMode: 'static',
  schemaMode: 'static',
  currentAnalysis: null,
  currentSchema: null,
  primarySql: null,
  primaryDbType: 'SQL Server',
  primarySourceType: 'auto',
  selectedSource: 'auto',
  activeTab: 'diagnose',
  loading: false,
  schemaLoading: false,

  setMode: (mode) => set({ mode }),
  setAnalysisMode: (analysisMode) => set({ analysisMode }),
  setSchemaMode: (schemaMode) => set({ schemaMode }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedSource: (source) => set({ selectedSource: source }),
  setLoading: (loading) => set({ loading }),
  setSchemaLoading: (schemaLoading) => set({ schemaLoading }),

  setAnalysis: (analysis, sql, dbType, sourceType, preserveTab = false) => {
    const typeMap = {
      'Stored Procedure': 'Stored Procedure',
      'SQL Query': 'SQL Query',
      'View': 'View',
      'Function': 'Function',
      'DDL Script': 'DML Script',
      'DML Script': 'DML Script',
    };
    const updates = {
      currentAnalysis: analysis,
      primarySql: sql,
      primaryDbType: dbType,
      primarySourceType: sourceType,
      selectedSource: typeMap[analysis.summary.object_type] || 'auto',
    };
    
    // Only change tab if not preserving current tab
    if (!preserveTab) {
      updates.activeTab = 'diagnose';
    }
    
    set(updates);
  },

  setSchema: (schema) => set({ currentSchema: schema }),

  clearSession: () => set({
    currentAnalysis: null,
    currentSchema: null,
    primarySql: null,
    primaryDbType: 'SQL Server',
    primarySourceType: 'auto',
    selectedSource: 'auto',
    activeTab: 'diagnose',
    mode: 'schema',
    analysisMode: 'static',
    schemaMode: 'static',
  }),
}));

export default useAgentStore;
