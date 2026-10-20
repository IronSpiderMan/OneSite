import { useEffect } from 'react';
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { useOperationsDashboardStore } from '../stores/useOperationsDashboardStore';

const statusStyle = {
  healthy: { icon: CheckCircle2, className: 'bg-emerald-500/10 text-emerald-500' },
  syncing: { icon: RefreshCw, className: 'bg-sky-500/10 text-sky-500' },
  warning: { icon: AlertTriangle, className: 'bg-amber-500/10 text-amber-500' },
};

export default function RecentActivityWidget() {
  const { t } = useTranslation();
  const { data, loading, load } = useOperationsDashboardStore();

  useEffect(() => { void load(); }, [load]);

  if (loading && !data) {
    return <div className="flex h-48 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-1">
      {(data?.activities || []).map((activity) => {
        const status = statusStyle[activity.status];
        const Icon = status.icon;
        return (
          <div key={activity.id} className="flex items-start gap-3 rounded-xl px-2 py-3 transition-colors hover:bg-muted/50">
            <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${status.className}`}><Icon className={`h-4 w-4 ${activity.status === 'syncing' ? 'animate-spin' : ''}`} /></span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{activity.source}</div>
              <div className="mt-0.5 truncate text-xs text-muted-foreground">{activity.detail}</div>
            </div>
            <span className="shrink-0 text-[10px] text-muted-foreground">{activity.time}</span>
          </div>
        );
      })}
      <div className="pt-2 text-center text-xs text-muted-foreground">{t('features.ops_dashboard.mock_data_hint')}</div>
    </div>
  );
}
