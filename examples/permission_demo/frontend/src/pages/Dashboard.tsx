// frontend/src/pages/Dashboard.tsx
import React, { useEffect, useState } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';




















interface ChartData {
    labels: string[];
    values: number[];
    title: string;
}

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

const getDefaultStartTime = (): string => {
    const d = new Date();
    d.setDate(d.getDate() - 15);
    return d.toISOString().split('T')[0];
};

const MAX_SPAN_DAYS: Record<string, number> = {
    day: 30,
    week: 210,
    month: 900,
};

const validateDateSpan = (startTime: string, endTime: string, period: string): string | null => {
    if (!startTime || !endTime) return null;
    const start = new Date(startTime);
    const end = new Date(endTime);
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return null;
    if (end <= start) return 'End date must be after start date';
    const spanDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
    const maxSpan = MAX_SPAN_DAYS[period] || 30;
    if (spanDays > maxSpan) {
        return `Time span cannot exceed ${maxSpan} days for ${period} period`;
    }
    return null;
};

const formatLocalDateTime = (dateStr: string | null): string => {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString(undefined, {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    } catch {
        return dateStr;
    }
};

const formatInterval = (seconds: number): string => {
    if (seconds <= 0) return '';
    if (seconds < 60) return `Every ${seconds}s`;
    if (seconds < 3600) return `Every ${Math.floor(seconds / 60)}m`;
    return `Every ${Math.floor(seconds / 3600)}h`;
};

const DashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [chartsData, setChartsData] = useState<Record<string, ChartData>>({});
    const [loading, setLoading] = useState(true);
    const [chartPeriods, setChartPeriods] = useState<Record<string, { period: string; startTime: string; endTime: string }>>({});
    

    useEffect(() => {
        const fetchAllStats = async () => {
            setLoading(true);
            const results: Record<string, ChartData> = {};

            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            

            setChartsData(results);
            setLoading(false);
        };

        fetchAllStats();
    }, [chartPeriods]);

    

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    const chartModels: { moduleName: string; chartType: string; title: string; fullRow: boolean; hasTimeField?: boolean }[] = [
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    ];

    if (chartModels.length === 0 ) {
        return (
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <h1 className="text-3xl font-bold tracking-tight">
                        {t('menu.dashboard', 'Dashboard')}
                    </h1>
                </div>
                <div className="text-center py-12 text-muted-foreground">
                    {t('dashboard.no_visualizations', 'No visualizations or tasks configured')}
                </div>
            </div>
        );
    }

    const renderChart = (moduleName: string, chartType: string, title: string) => {
        const data = chartsData[moduleName];
        if (!data || !data.labels.length) {
            return (
                <div className="flex justify-center items-center h-64 text-muted-foreground">
                    {t('dashboard.no_data', 'No data available')}
                </div>
            );
        }

        const chartData = data.labels.map((label, index) => ({
            name: label,
            value: data.values[index],
        }));

        if (chartType === 'pie') {
            return (
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                        <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                            outerRadius={100}
                            fill="#8884d8"
                            dataKey="value"
                            name={title}
                        >
                            {chartData.map((_, index) => (
                                <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                    </PieChart>
                </ResponsiveContainer>
            );
        }

        if (chartType === 'line') {
            return (
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} name={title} />
                    </LineChart>
                </ResponsiveContainer>
            );
        }

        // Default to bar chart
        return (
            <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="value" fill="#3b82f6" name={title} />
                </BarChart>
            </ResponsiveContainer>
        );
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-3xl font-bold tracking-tight">
                    {t('menu.dashboard', 'Dashboard')}
                </h1>
            </div>

            {chartModels.length > 0 && (
                <div className="grid gap-6 md:grid-cols-2">
                    {chartModels.map((chart) => (
                        <div key={chart.moduleName} className={`rounded-xl border bg-card text-card-foreground shadow-sm p-6${chart.fullRow ? ' md:col-span-2' : ''}`}>
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-semibold">
                                    {t(`models.${chart.moduleName}.name`, chart.title) as string}
                                </h3>
                                {chart.hasTimeField && (
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="date"
                                            className="border rounded-md px-2 py-1.5 text-xs"
                                            value={(chartPeriods[chart.moduleName] || { period: 'day', startTime: getDefaultStartTime(), endTime: '' }).startTime}
                                            onChange={(e) => {
                                                const newStart = e.target.value;
                                                setChartPeriods(prev => {
                                                    const cur = prev[chart.moduleName] || { period: 'day', startTime: getDefaultStartTime(), endTime: '' };
                                                    if (newStart && cur.endTime) {
                                                        const err = validateDateSpan(newStart, cur.endTime, cur.period);
                                                        if (err) { toast.error(err); return prev; }
                                                    }
                                                    return { ...prev, [chart.moduleName]: { ...cur, startTime: newStart } };
                                                });
                                            }}
                                        />
                                        <span className="text-xs text-muted-foreground">—</span>
                                        <input
                                            type="date"
                                            className="border rounded-md px-2 py-1.5 text-xs"
                                            value={(chartPeriods[chart.moduleName] || { period: 'day', startTime: getDefaultStartTime(), endTime: '' }).endTime}
                                            onChange={(e) => {
                                                const newEnd = e.target.value;
                                                setChartPeriods(prev => {
                                                    const cur = prev[chart.moduleName] || { period: 'day', startTime: getDefaultStartTime(), endTime: '' };
                                                    if (cur.startTime && newEnd) {
                                                        const err = validateDateSpan(cur.startTime, newEnd, cur.period);
                                                        if (err) { toast.error(err); return prev; }
                                                    }
                                                    return { ...prev, [chart.moduleName]: { ...cur, endTime: newEnd } };
                                                });
                                            }}
                                        />
                                        <select
                                            className="border rounded-md px-2 py-1.5 text-xs"
                                            value={(chartPeriods[chart.moduleName] || { period: 'day', startTime: getDefaultStartTime(), endTime: '' }).period}
                                            onChange={(e) => {
                                                const newPeriod = e.target.value;
                                                setChartPeriods(prev => ({
                                                    ...prev,
                                                    [chart.moduleName]: { period: newPeriod, startTime: getDefaultStartTime(), endTime: '' },
                                                }));
                                            }}
                                        >
                                            <option value="day">{t('dashboard.period_day', 'Daily')}</option>
                                            <option value="week">{t('dashboard.period_week', 'Weekly')}</option>
                                            <option value="month">{t('dashboard.period_month', 'Monthly')}</option>
                                        </select>
                                    </div>
                                )}
                            </div>
                            {renderChart(chart.moduleName, chart.chartType, chart.title)}
                        </div>
                    ))}
                </div>
            )}

            
        </div>
    );
};

export default DashboardPage;