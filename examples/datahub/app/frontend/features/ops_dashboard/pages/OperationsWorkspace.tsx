import { useEffect } from 'react';
import { ArrowRight, Database, Loader2, RadioTower, Workflow } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { useOperationsDashboardStore } from '../stores/useOperationsDashboardStore';

export default function OperationsWorkspace() {
  const { t } = useTranslation();
  const { data, loading, load } = useOperationsDashboardStore();

  useEffect(() => { void load(); }, [load]);

  if (loading && !data) {
    return <div className="flex h-64 items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-primary" /></div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="overflow-hidden rounded-2xl border border-border/60 bg-card p-7 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"><RadioTower className="h-3.5 w-3.5" />{t('features.ops_dashboard.workspace_kicker')}</div>
            <h1 className="text-3xl font-bold tracking-tight">{t('features.ops_dashboard.workspace_title')}</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{t('features.ops_dashboard.workspace_description')}</p>
          </div>
          <Link to="/public/datahub-status" className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted">{t('features.ops_dashboard.public_status')}</Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          { label: t('features.ops_dashboard.active_pipelines'), value: data?.activePipelines ?? 0, icon: Workflow },
          { label: t('features.ops_dashboard.records_today'), value: (data?.recordsToday ?? 0).toLocaleString(), icon: Database },
          { label: t('features.ops_dashboard.p95_latency'), value: `${data?.p95LatencyMs ?? 0} ms`, icon: RadioTower },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-2xl border border-border/60 bg-card p-5 shadow-sm">
            <Icon className="mb-4 h-5 w-5 text-primary" />
            <div className="text-2xl font-bold tabular-nums">{value}</div>
            <div className="mt-1 text-xs text-muted-foreground">{label}</div>
          </div>
        ))}
      </div>

      <section className="rounded-2xl border border-border/60 bg-card shadow-sm">
        <div className="border-b border-border/60 px-5 py-4"><h2 className="font-semibold">{t('features.ops_dashboard.connector_activity')}</h2></div>
        <div className="divide-y divide-border/60">
          {(data?.activities || []).map((activity) => (
            <Link key={activity.id} to={`/operations/connectors/${activity.id}`} className="flex items-center gap-4 px-5 py-4 transition-colors hover:bg-muted/50">
              <span className={`h-2.5 w-2.5 rounded-full ${activity.status === 'healthy' ? 'bg-emerald-500' : activity.status === 'warning' ? 'bg-amber-500' : 'bg-sky-500'}`} />
              <div className="min-w-0 flex-1"><div className="font-medium">{activity.source}</div><div className="truncate text-xs text-muted-foreground">{activity.detail}</div></div>
              <span className="text-xs text-muted-foreground">{activity.time}</span><ArrowRight className="h-4 w-4 text-muted-foreground" />
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
