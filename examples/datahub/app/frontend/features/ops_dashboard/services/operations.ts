export type ThroughputPoint = {
  label: string;
  value: number;
};

export type RecentActivity = {
  id: number;
  source: string;
  detail: string;
  status: 'healthy' | 'syncing' | 'warning';
  time: string;
};

export type OperationsSnapshot = {
  activePipelines: number;
  recordsToday: number;
  p95LatencyMs: number;
  throughput: ThroughputPoint[];
  activities: RecentActivity[];
};

const MOCK_SNAPSHOT: OperationsSnapshot = {
  activePipelines: 18,
  recordsToday: 2_846_291,
  p95LatencyMs: 184,
  throughput: [
    { label: '08:00', value: 42 },
    { label: '10:00', value: 58 },
    { label: '12:00', value: 51 },
    { label: '14:00', value: 76 },
    { label: '16:00', value: 68 },
    { label: '18:00', value: 91 },
    { label: '20:00', value: 83 },
  ],
  activities: [
    { id: 1, source: 'CRM CDC', detail: '128,420 rows committed', status: 'healthy', time: '2 min' },
    { id: 2, source: 'IoT Gateway', detail: 'Schema evolution detected', status: 'warning', time: '8 min' },
    { id: 3, source: 'ERP Orders', detail: 'Incremental sync in progress', status: 'syncing', time: '12 min' },
    { id: 4, source: 'Object Storage', detail: 'Daily partition published', status: 'healthy', time: '28 min' },
  ],
};

export async function getOperationsSnapshot(): Promise<OperationsSnapshot> {
  // The example deliberately uses deterministic mock data so it can be viewed
  // without adding a matching backend endpoint.
  await new Promise((resolve) => window.setTimeout(resolve, 280));
  return MOCK_SNAPSHOT;
}
