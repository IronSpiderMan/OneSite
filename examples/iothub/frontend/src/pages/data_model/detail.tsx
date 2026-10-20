import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useDataModelStore } from '../../stores/useDataModelStore';
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

import { getDataSource } from '../../services/data_source';







import { getDevices } from '../../services/device';




const DataModelDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useDataModelStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "name": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "identifier": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "version": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "data_source_id": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    };
    const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
      const fp = fieldRolePerms[fieldName];
      if (!fp) return true;
      return (fp[userRole] || '').includes(perm);
    };
    
    // State to store resolved foreign key data
    
    const [data_sourceData, setDataSourceData] = useState<any>(null);
    

    // State for M2M data
    

    // State for Reverse M2M data
    

    // State for Reverse FK data (One-to-Many)
    
    
    
    const [devicesData, setDeviceData] = useState<any[]>([]);
    const [devicesTotal, setDeviceTotal] = useState(0);
    const [devicesPage, setDevicePage] = useState(1);
    const [devicesLoading, setDeviceLoading] = useState(false);
    
    
    

    

    useEffect(() => {
        if (id) {
            const itemId = parseInt(id);
            fetchItem(itemId).then((item) => {
                if (item) {
                    // Fetch FK data
                    
                    if (item.data_source_id) {
                        getDataSource(item.data_source_id).then(res => {
                             if (res) {
                                 setDataSourceData(res);
                             }
                        });
                    }
                    
                }
            });
            
            // Fetch M2M data
            

            // Fetch Reverse M2M data
            

            // Fetch Reverse FK data
            
            
            
            fetchDevices(itemId, 1);
            
            
            
        }
    }, [id, fetchItem]);

    

    

    
    
    
    const fetchDevices = async (itemId: number, page: number) => {
        setDeviceLoading(true);
        try {
            // Filter by foreign key
            const filters = { data_model_id: itemId };
            const result = await getDevices(page, 5, filters);
            setDeviceData(result.items);
            setDeviceTotal(result.total);
            setDevicePage(result.page);
        } catch (error) {
            console.error(error);
        } finally {
            setDeviceLoading(false);
        }
    };
    
    
    

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
                <h1 className="text-3xl font-bold tracking-tight">DataModel Details</h1>
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
                            <Label className="text-muted-foreground">{t('models.data_model.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('name', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.data_model.fields.name')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.name ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('identifier', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.data_model.fields.identifier')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.identifier ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('version', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.data_model.fields.version')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.version ?? '-')}
                                
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
                                <Label className="text-lg font-semibold">{t('models.data_source.name')}</Label>
                                <Badge variant="outline">ID: {currentItem.data_source_id}</Badge>
                            </div>
                            <div className="rounded-md border p-4">
                                { data_sourceData ? (
                                    <div className="space-y-2">
                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            <span className="text-muted-foreground">Display Name:</span>
                                            <span className="font-medium">{ data_sourceData.name }</span>
                                            
                                            {/* Show all readable fields for the target model */}
                                            
                                            
                                            
                                            { data_sourceData.id !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.data_source.fields.id')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(data_sourceData.id ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            
                                            
                                            { data_sourceData.type !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.data_source.fields.type')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(data_sourceData.type ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { data_sourceData.host !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.data_source.fields.host')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(data_sourceData.host ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { data_sourceData.port !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.data_source.fields.port')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(data_sourceData.port ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            { data_sourceData.description !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.data_source.fields.description')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(data_sourceData.description ?? '-')}
                                                    
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
                

                

                

                
                
                
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>{t('models.device.name')}s</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-md border">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>ID</TableHead>
                                        <TableHead>Device_Key</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    { devicesLoading ? (
                                        <TableRow>
                                            <TableCell colSpan={2} className="h-24 text-center">
                                                <Loader2 className="mx-auto h-6 w-6 animate-spin" />
                                            </TableCell>
                                        </TableRow>
                                    ) : devicesData.length > 0 ? (
                                        devicesData.map((item) => (
                                            <TableRow key={item.id}>
                                                <TableCell>{item.id}</TableCell>
                                                <TableCell>{item.device_key }</TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell colSpan={2} className="h-24 text-center">
                                                No devices found.
                                            </TableCell>
                                        </TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                        <div className="mt-4 flex items-center justify-end space-x-2">
                             <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchDevices(parseInt(id!), devicesPage - 1)}
                                disabled={ devicesPage <= 1 || devicesLoading}
                            >
                                Previous
                            </Button>
                            <span className="text-sm">
                                Page { devicesPage } of { Math.ceil(devicesTotal / 5) || 1 }
                            </span>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchDevices(parseInt(id!), devicesPage + 1)}
                                disabled={ devicesPage >= Math.ceil(devicesTotal / 5) || devicesLoading}
                            >
                                Next
                            </Button>
                        </div>
                    </CardContent>
                </Card>
                
                
                
            </div>
        </div>
    );
};

export default DataModelDetailPage;