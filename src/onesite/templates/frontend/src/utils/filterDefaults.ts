/** Resolve defaults in local calendar time; never evaluate user expressions. */
export function resolveFilterDefault(value: any, now = new Date()): any {
  if (!value || typeof value !== 'object' || Array.isArray(value) || !value.period) return value;
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(start);
  switch (value.period) {
    case 'yesterday': start.setDate(start.getDate() - 1); end.setDate(end.getDate() - 1); break;
    case 'this_week': start.setDate(start.getDate() - (start.getDay() + 6) % 7); end.setTime(start.getTime()); end.setDate(end.getDate() + 6); break;
    case 'last_week': start.setDate(start.getDate() - (start.getDay() + 6) % 7 - 7); end.setTime(start.getTime()); end.setDate(end.getDate() + 6); break;
    case 'this_month': start.setDate(1); end.setMonth(end.getMonth() + 1, 0); break;
    case 'last_month': start.setMonth(start.getMonth() - 1, 1); end.setDate(0); break;
    case 'last_7_days': start.setDate(start.getDate() - 6); break;
    case 'last_30_days': start.setDate(start.getDate() - 29); break;
  }
  const format = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  return { start: `${format(start)}T00:00:00`, end: `${format(end)}T23:59:59` };
}

export function visualizationFilterDefaults(spec: { filters: Array<{ key: string; type: string; default?: any }> }): Record<string, any> {
  return Object.fromEntries(spec.filters.filter(f => f.default != null).map(f => {
    const value = resolveFilterDefault(f.default);
    return [f.key, f.type === 'select' ? String(value) : f.type === 'multi_select' ? value.map(String) : value];
  }));
}
