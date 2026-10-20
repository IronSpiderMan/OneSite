import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Eye, Loader2, Save, Pencil, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useNotificationStore } from '../../stores/useNotificationStore';
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


import { getUser } from '../../services/user';







const NotificationDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useNotificationStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "title": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "summary": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "content": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "created_at": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "is_read": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "user_id": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    };
    const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
      const fp = fieldRolePerms[fieldName];
      if (!fp) return true;
      return (fp[userRole] || '').includes(perm);
    };
    
    // State to store resolved foreign key data
    
    const [userData, setUserData] = useState<any>(null);
    

    // State for M2M data
    

    // State for Reverse M2M data
    

    // State for Reverse FK data (One-to-Many)
    

    

    const calcStartTime = (range: string): string | undefined => {
        const ms: Record<string, number> = { '1h': 3600000, '6h': 21600000, '24h': 86400000 };
        const m = ms[range];
        return m ? new Date(Date.now() - m).toISOString() : undefined;
    };

    

    

    useEffect(() => {
        if (id) {
            const itemId = parseInt(id);
            fetchItem(itemId).then((item) => {
                if (item) {
                    // Fetch FK data
                    
                    if (item.user_id) {
                        getUser(item.user_id).then(res => {
                             if (res) {
                                 setUserData(res);
                             }
                        });
                    }
                    
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
                <h1 className="text-3xl font-bold tracking-tight">Notification Details</h1>
              </div>

              <div className="flex items-center gap-2">
                

                
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
                            <Label className="text-muted-foreground">{t('models.notification.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('title', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.notification.fields.title')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.title ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('summary', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.notification.fields.summary')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.summary ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('content', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.notification.fields.content')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.content ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('created_at', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.notification.fields.created_at')}</Label>
                            <div className="font-medium">
                                
                                <span className="text-muted-foreground">{formatDateTime(currentItem.created_at, timeZone)}</span>
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('is_read', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.notification.fields.is_read')}</Label>
                            <div className="font-medium">
                                
                                <Badge variant={currentItem.is_read ? "default" : "secondary"}>
                                    {currentItem.is_read ? 'Yes' : 'No'}
                                </Badge>
                                
                            </div>
                        </div>
                        )}
                        
                        
                        
                        
                    </CardContent>
                </Card>

                
                <Card>
                    <CardHeader>
                        <CardTitle>Related Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        
                        <div>
                            <div className="mb-2 flex items-center justify-between">
                                <Label className="text-lg font-semibold">{t('models.user.name')}</Label>
                                <Badge variant="outline">ID: {currentItem.user_id}</Badge>
                            </div>
                            <div className="rounded-md border p-4">
                                { userData ? (
                                    <div className="space-y-2">
                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            <span className="text-muted-foreground">Display Name:</span>
                                            <span className="font-medium">{ userData.email }</span>
                                            
                                            {/* Show all readable fields for the target model */}
                                            
                                            
                                            
                                            
                                            
                                            { userData.full_name !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.user.fields.full_name')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(userData.full_name ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { userData.avatar !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.user.fields.avatar')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(userData.avatar ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { userData.is_active !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.user.fields.is_active')}:</span>
                                                <span className="font-medium">
                                                    
                                                    { userData.is_active ? 'Yes' : 'No' }
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { userData.role !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.user.fields.role')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(userData.role ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { userData.id !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.user.fields.id')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(userData.id ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { userData.created_at !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.user.fields.created_at')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(userData.created_at ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { userData.updated_at !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.user.fields.updated_at')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(userData.updated_at ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex items-center space-x-2 text-muted-foreground">
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        <span>Loading related data...</span>
                                    </div>
                                )}
                            </div>
                        </div>
                        
                        
                    </CardContent>
                </Card>
                

                

                

                

                
            </div>
        </div>
    );
};

export default NotificationDetailPage;