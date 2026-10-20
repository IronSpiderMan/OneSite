import { Activity, ArrowRight, CheckCircle2, Database } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function PublicStatus() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12 text-slate-100">
      <div className="mx-auto max-w-4xl">
        <div className="flex items-center justify-between"><div className="flex items-center gap-2 font-semibold"><Database className="h-5 w-5 text-cyan-400" />DataHub Status</div><Link to="/login" className="inline-flex items-center gap-2 text-sm text-cyan-300">Sign in <ArrowRight className="h-4 w-4" /></Link></div>
        <div className="mt-20 text-center"><span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-4 py-1.5 text-sm text-emerald-300"><CheckCircle2 className="h-4 w-4" />All systems operational</span><h1 className="mt-6 text-4xl font-bold tracking-tight">Data services are healthy</h1><p className="mt-3 text-slate-400">This public Feature route does not require an authenticated application layout.</p></div>
        <div className="mt-12 grid gap-4 md:grid-cols-3">{['Ingestion API', 'Query Engine', 'Metadata Catalog'].map((service, index) => <div key={service} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><div className="flex items-center justify-between"><Activity className="h-5 w-5 text-cyan-400" /><span className="text-xs text-emerald-300">Operational</span></div><div className="mt-5 font-medium">{service}</div><div className="mt-1 text-xs text-slate-500">{[99.99, 99.97, 100][index]}% uptime · 30 days</div></div>)}</div>
      </div>
    </main>
  );
}
