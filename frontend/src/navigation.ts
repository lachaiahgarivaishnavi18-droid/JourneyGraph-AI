export const groups = [
    { name: 'Overview', icon: 'dashboard', pages: ['Dashboard', 'Customer Journey Overview', 'Business KPIs', 'Recent Activities'] },
    { name: 'Customer Management', icon: 'customers', pages: ['Customer Directory', 'Customer Profile', 'Customer Segmentation', 'Customer Behavior Analysis', 'Customer Lifetime Value'] },
    { name: 'Journey Analytics', icon: 'journey', pages: ['Journey Explorer', 'Journey Timeline', 'Journey Funnel Analysis', 'Conversion Path Analysis', 'Drop-off Analysis', 'Cross-Channel Analysis', 'Cohort Analysis'] },
    { name: 'Temporal Knowledge Graph', icon: 'graph', pages: ['Knowledge Graph Explorer', 'Temporal Graph Timeline', 'Entity Relationship Explorer', 'Historical Graph Comparison', 'Graph Pattern Discovery'] },
    { name: 'Multi-Agent Intelligence', icon: 'agents', pages: ['AI Agent Dashboard', 'Customer Profiling Agent', 'Journey Tracking Agent', 'Temporal Graph Agent', 'Behavior Analysis Agent', 'Segmentation Agent', 'Prediction Agent', 'Recommendation Agent', 'Insight Generation Agent', 'Orchestrator Agent'] },
    { name: 'AI Insights', icon: 'insights', pages: ['Customer Journey Insights', 'Churn Risk Analysis', 'Conversion Prediction', 'Product Recommendation', 'Next Best Action', 'Natural Language Analytics'] },
    { name: 'Reports', icon: 'reports', pages: ['Analytics Reports', 'Customer Reports', 'Journey Reports', 'Agent Execution Reports', 'Export Center'] },
    { name: 'Administration', icon: 'settings', pages: ['Data Import', 'Data Sources', 'LLM Configuration', 'Agent Configuration', 'System Settings', 'Audit Logs'] }
];
export const slug = (text: string) => text.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-');
export const pages = groups.flatMap(g => g.pages);
