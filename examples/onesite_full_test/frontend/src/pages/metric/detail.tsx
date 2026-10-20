import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Eye, Loader2, Save, Pencil, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useMetricStore } from '../../stores/useMetricStore';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Label } from '../../components/ui/label';
import { formatDateTime, formatTime, getUserTimeZone } from '../../lib/datetime';
import { Separator } from '../../components/ui/separator';
import { FileUpload } from '../../components/ui/file-upload';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';








const MetricDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useMetricStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "name": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "value": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "recorded_at": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    };
    const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
      const fp = fieldRolePerms[fieldName];
      if (!fp) return true;
      return (fp[userRole] || '').includes(perm);
    };
    
    // State to store resolved foreign key data
    

    // State for M2M data
    

    // State for Reverse M2M data
    

    // State for Reverse FK data (One-to-Many)
    

    

    const calcStartTime = (range: string): string | undefined => {
        const ms: Record<string, number> = { '1h': 3600000, '6h': 21600000, '24h': 86400000 };
        const m = ms[range];
        return m ? new Date(Date.now() - m).toISOString() : undefined;
    };

    

    
    const [autoRefresh, setAutoRefresh] = useState(true);
    const [refreshInterval, setRefreshInterval] = useState(2000);

    useEffect(() => {
        let interval: ReturnType<typeof setInterval>;
        if (autoRefresh && id) {
            interval = setInterval(() => {
                const itemId = parseInt(id);
                fetchItem(itemId);
            }, refreshInterval);
        }
        return () => clearInterval(interval);
    }, [autoRefresh, refreshInterval, id, fetchItem]);
    

    useEffect(() => {
        if (id) {
            const itemId = parseInt(id);
            fetchItem(itemId).then((item) => {
                if (item) {
                    // Fetch FK data
                    
                }
            });
            
            // Fetch M2M data
            

            // Fetch Reverse M2M data
            

            // Fetch Reverse FK data
            

            // Fetch Timeseries realtime data
            

            // Fetch Timeseries history data
            
        }
    }, [id, fetchItem]);

    

    

    

    

    if (loading && !currentItem) {
        return (
            <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin" />
            </div>
        );
    }

    if (!currentItem) {
        return (
            <div className="flex flex-col items-center justify-center space-y-4">
                <div className="text-xl font-semibold">Item not found</div>
                <Button onClick={() => navigate(-1)}>Go Back</Button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <h1 className="text-3xl font-bold tracking-tight">Metric Details</h1>
              </div>

              <div className="flex items-center gap-2">
                

                
              </div>

              
              <div className="flex items-center gap-2">
                 <span className="text-sm text-muted-foreground">{t('common.auto_refresh')}</span>
                 <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} />
                 {autoRefresh && (
                    <Select value={String(refreshInterval)} onValueChange={(v) => setRefreshInterval(Number(v))}>
                        <SelectTrigger className="w-[100px] h-8">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="1000">1s</SelectItem>
                            <SelectItem value="5000">5s</SelectItem>
                            <SelectItem value="10000">10s</SelectItem>
                            <SelectItem value="30000">30s</SelectItem>
                        </SelectContent>
                    </Select>
                 )}
              </div>
              
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle>Basic Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        
                        
                        
                        {hasFieldPerm('id', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.metric.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('name', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.metric.fields.name')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.name ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('value', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.metric.fields.value')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.value ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('recorded_at', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.metric.fields.recorded_at')}</Label>
                            <div className="font-medium">
                                
                                <span className="text-muted-foreground">{formatDateTime(currentItem.recorded_at, timeZone)}</span>
                                
                            </div>
                        </div>
                        )}
                        
                        
                    </CardContent>
                </Card>

                

                

                

                

                
            </div>
        </div>
    );
};

export default MetricDetailPage;