import { create } from 'zustand';

const useAgentStore = create((set) => ({
  mode: 'analyze',
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
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedSource: (source) => set({ selectedSource: source }),
  setLoading: (loading) => set({ loading }),
  setSchemaLoading: (schemaLoading) => set({ schemaLoading }),

  setAnalysis: (analysis, sql, dbType, sourceType) => {
    const typeMap = {
      'Stored Procedure': 'Stored Procedure',
      'SQL Query': 'SQL Query',
      'View': 'View',
      'Function': 'Function',
      'DDL Script': 'DML Script',
      'DML Script': 'DML Script',
    };
    set({
      currentAnalysis: analysis,
      primarySql: sql,
      primaryDbType: dbType,
      primarySourceType: sourceType,
      selectedSource: typeMap[analysis.summary.object_type] || 'auto',
      activeTab: 'diagnose',
    });
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
    mode: 'analyze',
  }),
}));

export default useAgentStore;
