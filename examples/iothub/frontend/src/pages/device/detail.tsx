import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useDeviceStore } from '../../stores/useDeviceStore';
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

import { getDataModel } from '../../services/data_model';






const DeviceDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useDeviceStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "name": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "device_key": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "status": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "data_model_id": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    };
    const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
      const fp = fieldRolePerms[fieldName];
      if (!fp) return true;
      return (fp[userRole] || '').includes(perm);
    };
    
    // State to store resolved foreign key data
    
    const [data_modelData, setDataModelData] = useState<any>(null);
    

    // State for M2M data
    

    // State for Reverse M2M data
    

    // State for Reverse FK data (One-to-Many)
    

    

    useEffect(() => {
        if (id) {
            const itemId = parseInt(id);
            fetchItem(itemId).then((item) => {
                if (item) {
                    // Fetch FK data
                    
                    if (item.data_model_id) {
                        getDataModel(item.data_model_id).then(res => {
                             if (res) {
                                 setDataModelData(res);
                             }
                        });
                    }
                    
                }
            });
            
            // Fetch M2M data
            

            // Fetch Reverse M2M data
            

            // Fetch Reverse FK data
            
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
                <h1 className="text-3xl font-bold tracking-tight">Device Details</h1>
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
                            <Label className="text-muted-foreground">{t('models.device.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('name', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.device.fields.name')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.name ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('device_key', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.device.fields.device_key')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.device_key ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('status', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.device.fields.status')}</Label>
                            <div className="font-medium">
                                
                                <Badge variant="outline">{currentItem.status}</Badge>
                                
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
                                <Label className="text-lg font-semibold">{t('models.data_model.name')}</Label>
                                <Badge variant="outline">ID: {currentItem.data_model_id}</Badge>
                            </div>
                            <div className="rounded-md border p-4">
                                { data_modelData ? (
                                    <div className="space-y-2">
                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            <span className="text-muted-foreground">Display Name:</span>
                                            <span className="font-medium">{ data_modelData.identifier }</span>
                                            
                                            {/* Show all readable fields for the target model */}
                                            
                                            
                                            
                                            { data_modelData.id !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.data_model.fields.id')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(data_modelData.id ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { data_modelData.name !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.data_model.fields.name')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(data_modelData.name ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            
                                            
                                            { data_modelData.version !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.data_model.fields.version')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(data_modelData.version ?? '-')}
                                                    
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

export default DeviceDetailPage;