import { useEffect } from 'react';
import { ArrowLeft, CheckCircle2, Clock3, DatabaseZap } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { useOperationsDashboardStore } from '../stores/useOperationsDashboardStore';

export default function ConnectorDetail() {
  const { t } = useTranslation();
  const { connectorId } = useParams();
  const { data, load } = useOperationsDashboardStore();
  useEffect(() => { void load(); }, [load]);
  const activity = data?.activities.find((item) => String(item.id) === connectorId);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link to="/operations" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />{t('features.ops_dashboard.back_workspace')}</Link>
      <div className="rounded-2xl border border-border/60 bg-card p-7 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div><div className="text-sm text-muted-foreground">{t('features.ops_dashboard.connector')}</div><h1 className="mt-1 text-3xl font-bold">{activity?.source || `Connector ${connectorId}`}</h1></div>
          <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-600">{activity?.status || 'healthy'}</span>
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-muted/40 p-4"><CheckCircle2 className="mb-3 h-5 w-5 text-emerald-500" /><div className="text-sm font-medium">{t('features.ops_dashboard.schema_valid')}</div></div>
          <div className="rounded-xl bg-muted/40 p-4"><DatabaseZap className="mb-3 h-5 w-5 text-sky-500" /><div className="text-sm font-medium">{activity?.detail || '42,860 rows committed'}</div></div>
          <div className="rounded-xl bg-muted/40 p-4"><Clock3 className="mb-3 h-5 w-5 text-amber-500" /><div className="text-sm font-medium">{activity?.time || 'just now'}</div></div>
        </div>
      </div>
    </div>
  );
}
