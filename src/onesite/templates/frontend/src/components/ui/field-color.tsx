import type { ReactNode } from 'react';

export const FIELD_COLORS = {
  gray: 'text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-950/40 border-gray-200 dark:border-gray-800',
  red: 'text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800',
  orange: 'text-orange-700 dark:text-orange-300 bg-orange-50 dark:bg-orange-950/40 border-orange-200 dark:border-orange-800',
  amber: 'text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800',
  yellow: 'text-yellow-700 dark:text-yellow-300 bg-yellow-50 dark:bg-yellow-950/40 border-yellow-200 dark:border-yellow-800',
  lime: 'text-lime-700 dark:text-lime-300 bg-lime-50 dark:bg-lime-950/40 border-lime-200 dark:border-lime-800',
  green: 'text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-950/40 border-green-200 dark:border-green-800',
  emerald: 'text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800',
  teal: 'text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/40 border-teal-200 dark:border-teal-800',
  cyan: 'text-cyan-700 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-950/40 border-cyan-200 dark:border-cyan-800',
  sky: 'text-sky-700 dark:text-sky-300 bg-sky-50 dark:bg-sky-950/40 border-sky-200 dark:border-sky-800',
  blue: 'text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800',
  indigo: 'text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-800',
  violet: 'text-violet-700 dark:text-violet-300 bg-violet-50 dark:bg-violet-950/40 border-violet-200 dark:border-violet-800',
  purple: 'text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800',
  pink: 'text-pink-700 dark:text-pink-300 bg-pink-50 dark:bg-pink-950/40 border-pink-200 dark:border-pink-800',
  rose: 'text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800',
} as const;

export const ROW_COLORS = {
  gray: 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-950/40 dark:hover:bg-gray-900/50',
  red: 'bg-red-50 hover:bg-red-100 dark:bg-red-950/40 dark:hover:bg-red-900/50',
  orange: 'bg-orange-50 hover:bg-orange-100 dark:bg-orange-950/40 dark:hover:bg-orange-900/50',
  amber: 'bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 dark:hover:bg-amber-900/50',
  yellow: 'bg-yellow-50 hover:bg-yellow-100 dark:bg-yellow-950/40 dark:hover:bg-yellow-900/50',
  lime: 'bg-lime-50 hover:bg-lime-100 dark:bg-lime-950/40 dark:hover:bg-lime-900/50',
  green: 'bg-green-50 hover:bg-green-100 dark:bg-green-950/40 dark:hover:bg-green-900/50',
  emerald: 'bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/50',
  teal: 'bg-teal-50 hover:bg-teal-100 dark:bg-teal-950/40 dark:hover:bg-teal-900/50',
  cyan: 'bg-cyan-50 hover:bg-cyan-100 dark:bg-cyan-950/40 dark:hover:bg-cyan-900/50',
  sky: 'bg-sky-50 hover:bg-sky-100 dark:bg-sky-950/40 dark:hover:bg-sky-900/50',
  blue: 'bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/40 dark:hover:bg-blue-900/50',
  indigo: 'bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/40 dark:hover:bg-indigo-900/50',
  violet: 'bg-violet-50 hover:bg-violet-100 dark:bg-violet-950/40 dark:hover:bg-violet-900/50',
  purple: 'bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/40 dark:hover:bg-purple-900/50',
  pink: 'bg-pink-50 hover:bg-pink-100 dark:bg-pink-950/40 dark:hover:bg-pink-900/50',
  rose: 'bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 dark:hover:bg-rose-900/50',
} as const;

type Color = keyof typeof FIELD_COLORS;
type Condition = { field?: string; eq?: unknown; ne?: unknown; in?: unknown[]; gt?: number; gte?: number; lt?: number; lte?: number };
export type FieldColorConfig = Color | { rules: { when: Condition; color: Color }[]; default?: Color };

export function resolveFieldColor(config: FieldColorConfig, field: string, record: Record<string, unknown>, canRead: (field: string) => boolean): Color | undefined {
  if (typeof config === 'string') return config;
  for (const { when, color } of config.rules) {
    const target = when.field ?? field;
    if (!canRead(target) || !Object.prototype.hasOwnProperty.call(record, target) || record[target] === undefined) continue;
    const actual = record[target];
    if ('eq' in when && actual === when.eq) return color;
    if ('ne' in when && actual !== when.ne) return color;
    if ('in' in when && when.in?.includes(actual)) return color;
    if (typeof actual !== 'number' || !Number.isFinite(actual)) continue;
    if ('gt' in when && actual > when.gt!) return color;
    if ('gte' in when && actual >= when.gte!) return color;
    if ('lt' in when && actual < when.lt!) return color;
    if ('lte' in when && actual <= when.lte!) return color;
  }
  return config.default;
}

export function FieldColor({ config, field, record, canRead, badge = false, children }: {
  config?: FieldColorConfig | null; field: string; record: Record<string, unknown>;
  canRead: (field: string) => boolean; badge?: boolean; children: ReactNode;
}) {
  const color = config ? resolveFieldColor(config, field, record, canRead) : undefined;
  const classes = color ? FIELD_COLORS[color] : '';
  return <span className={badge
    ? `inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${color ? classes : 'bg-muted text-foreground'}`
    : classes.split(' ').filter(value => value.startsWith('text-') || value.startsWith('dark:text-')).join(' ')}>{children}</span>;
}

export function resolveRowColorClass(config: FieldColorConfig, record: Record<string, unknown>, canRead: (field: string) => boolean): string {
  const color = resolveFieldColor(config, '', record, canRead);
  return color ? ROW_COLORS[color] : '';
}
