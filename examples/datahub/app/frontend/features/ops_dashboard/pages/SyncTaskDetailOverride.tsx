import { ArrowLeft, CalendarClock, PlayCircle, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

export default function SyncTaskDetailOverride() {
  const { t } = useTranslation();
  const { id } = useParams();
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Link to="/sync_tasks" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />{t('features.ops_dashboard.back_sync_tasks')}</Link>
      <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/10 via-card to-card p-7 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4"><div><div className="text-sm text-muted-foreground">{t('features.ops_dashboard.custom_override')}</div><h1 className="mt-1 text-3xl font-bold">Sync Task #{id}</h1></div><span className="rounded-full bg-sky-500/10 px-3 py-1 text-xs font-medium text-sky-500">Running</span></div>
        <div className="mt-8 grid gap-4 md:grid-cols-3"><div className="rounded-xl border border-border/60 bg-background/60 p-4"><RefreshCw className="mb-3 h-5 w-5 text-primary" /><div className="font-medium">Incremental sync</div><div className="mt-1 text-xs text-muted-foreground">84% completed</div></div><div className="rounded-xl border border-border/60 bg-background/60 p-4"><CalendarClock className="mb-3 h-5 w-5 text-amber-500" /><div className="font-medium">Every 30 minutes</div><div className="mt-1 text-xs text-muted-foreground">Next run at 21:30</div></div><div className="rounded-xl border border-border/60 bg-background/60 p-4"><PlayCircle className="mb-3 h-5 w-5 text-emerald-500" /><div className="font-medium">1.28M rows</div><div className="mt-1 text-xs text-muted-foreground">Processed in current run</div></div></div>
      </div>
    </div>
  );
}
