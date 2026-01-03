export type OverviewDomainKey =
  | 'operations'
  | 'intelligence'
  | 'emotion'
  | 'memory'
  | 'agency'
  | 'security'
  | 'system';

export interface OverviewDomainCard {
  key: OverviewDomainKey;
  title: string;
  kpiLabel: string;
  kpiValue: string;
  secondary: { label: string; value: string }[];
  isImplemented: boolean; // true = real backend data, false = mock data
}

export interface OverviewEventItem {
  id: string;
  time: string; // ISO string or relative when wired to backend
  domain: OverviewDomainKey | 'overview';
  severity: 'info' | 'warning' | 'error';
  title: string;
  description?: string;
}

export interface OverviewMetrics {
  systemStatus: 'ok' | 'degraded' | 'attention';
  uptime: string;
  activeConversations: number;
  activeGoals: number;
  domains: OverviewDomainCard[];
  events: OverviewEventItem[];
}

// Placeholder data, easily replaced with real backend data provider later.
export const overviewStubData: OverviewMetrics = {
  systemStatus: 'ok',
  uptime: '3h 42m',
  activeConversations: 2,
  activeGoals: 5,
  domains: [
    {
      key: 'operations',
      title: 'Operations',
      kpiLabel: 'Healthy services',
      kpiValue: '4 / 4',
      secondary: [
        { label: 'Error rate (5m)', value: '0.2%' },
        { label: 'Jobs running', value: '3' },
      ],
      isImplemented: false,
    },
    {
      key: 'intelligence',
      title: 'Intelligence',
      kpiLabel: 'Models healthy',
      kpiValue: '7 / 7',
      secondary: [
        { label: 'LLM p95 latency', value: '1.2s' },
        { label: 'Extraction calls/min', value: '18' },
      ],
      isImplemented: false,
    },
    {
      key: 'emotion',
      title: 'Emotion',
      kpiLabel: 'Current state',
      kpiValue: 'Calm',
      secondary: [
        { label: 'Valence', value: '+0.42' },
        { label: 'Arousal', value: '0.31' },
      ],
      isImplemented: true, // Real backend integration
    },
    {
      key: 'memory',
      title: 'Memory & AMS',
      kpiLabel: 'Retrieval quality',
      kpiValue: '92%',
      secondary: [
        { label: 'Working items', value: '1,247' },
        { label: 'Semantic vectors', value: '45.2K' },
        { label: 'KG nodes', value: '892' },
      ],
      isImplemented: true,
    },
    {
      key: 'agency',
      title: 'Agency',
      kpiLabel: 'Active goals',
      kpiValue: '10',
      secondary: [
        { label: 'Curiosity level', value: 'Low' },
        { label: 'Lessons learned', value: '12' },
      ],
      isImplemented: true,
    },
    {
      key: 'security',
      title: 'Security',
      kpiLabel: 'Posture',
      kpiValue: 'Healthy',
      secondary: [
        { label: 'Master key age', value: '9d' },
        { label: 'Failed auth (24h)', value: '1' },
      ],
      isImplemented: false,
    },
    {
      key: 'system',
      title: 'System',
      kpiLabel: 'Versions aligned',
      kpiValue: 'Yes',
      secondary: [
        { label: 'Schema version', value: 'v33' },
        { label: 'Plugins', value: '3 active' },
      ],
      isImplemented: false,
    },
  ],
  events: [
    {
      id: 'evt-1',
      time: '2025-12-26T18:30:00Z',
      domain: 'operations',
      severity: 'warning',
      title: 'Scheduler job retry',
      description: 'Maintenance cleanup job retried 2 times, now succeeded.',
    },
    {
      id: 'evt-2',
      time: '2025-12-26T18:10:00Z',
      domain: 'agency',
      severity: 'info',
      title: 'New user-origin goal',
      description: 'Goal "Help plan weekend" activated (priority: medium).',
    },
    {
      id: 'evt-3',
      time: '2025-12-26T17:55:00Z',
      domain: 'security',
      severity: 'error',
      title: 'Failed login attempt',
      description: 'One failed JWT validation from unknown client.',
    },
  ],
};
