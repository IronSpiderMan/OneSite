export type CustomFeatureData = {
  items: unknown[];
  total: number;
};

export async function getOpsDashboardData(): Promise<CustomFeatureData> {
  return { items: [], total: 0 };
}