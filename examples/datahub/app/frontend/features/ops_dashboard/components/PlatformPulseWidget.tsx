import { useEffect } from 'react';
import { Activity, DatabaseZap, Gauge, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useOperationsDashboardStore } from '../stores/useOperationsDashboardStore';

const number = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });

export default function PlatformPulseWidget() {
  const { t } = useTranslation();
  const { data, loading, error, load } = useOperationsDashboardStore();

  useEffect(() => { void load(); }, [load]);

  if (loading && !data) {
    return <div className="flex h-48 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }
  if (error || !data) {
    return <div className="flex h-48 items-center justify-center text-sm text-destructive">{error || t('common.no_result')}</div>;
  }

  const maximum = Math.max(...data.throughput.map((point) => point.value));
  const summaries = [
    { label: t('features.ops_dashboard.active_pipelines'), value: data.activePipelines, icon: Activity, tone: 'text-emerald-500 bg-emerald-500/10' },
    { label: t('features.ops_dashboard.records_today'), value: number.format(data.recordsToday), icon: DatabaseZap, tone: 'text-sky-500 bg-sky-500/10' },
    { label: t('features.ops_dashboard.p95_latency'), value: `${data.p95LatencyMs} ms`, icon: Gauge, tone: 'text-amber-500 bg-amber-500/10' },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-3">
        {summaries.map(({ label, value, icon: Icon, tone }) => (
          <div key={label} className="rounded-xl border border-border/60 bg-background/50 p-4">
            <div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-lg ${tone}`}><Icon className="h-4 w-4" /></div>
            <div className="text-2xl font-semibold tabular-nums">{value}</div>
            <div className="mt-1 text-xs text-muted-foreground">{label}</div>
          </div>
        ))}
      </div>
      <div>
        <div className="mb-3 flex items-center justify-between text-xs text-muted-foreground">
          <span>{t('features.ops_dashboard.throughput')}</span>
          <span>{t('features.ops_dashboard.records_per_second')}</span>
        </div>
        <div className="flex h-28 items-end gap-2">
          {data.throughput.map((point) => (
            <div key={point.label} className="flex min-w-0 flex-1 flex-col items-center gap-2">
              <div className="w-full rounded-t-md bg-gradient-to-t from-primary/50 to-primary transition-opacity hover:opacity-80" style={{ height: `${Math.max(12, (point.value / maximum) * 88)}px` }} title={`${point.value}k/s`} />
              <span className="text-[10px] text-muted-foreground">{point.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
