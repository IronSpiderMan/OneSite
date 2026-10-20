import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useDataSourceStore } from '../../stores/useDataSourceStore';
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







import { getDataModels } from '../../services/data_model';




const DataSourceDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useDataSourceStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "name": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "type": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "host": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "port": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "description": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
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
    
    
    
    const [data_modelsData, setDataModelData] = useState<any[]>([]);
    const [data_modelsTotal, setDataModelTotal] = useState(0);
    const [data_modelsPage, setDataModelPage] = useState(1);
    const [data_modelsLoading, setDataModelLoading] = useState(false);
    
    
    

    

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
            
            
            
            fetchDataModels(itemId, 1);
            
            
            
        }
    }, [id, fetchItem]);

    

    

    
    
    
    const fetchDataModels = async (itemId: number, page: number) => {
        setDataModelLoading(true);
        try {
            // Filter by foreign key
            const filters = { data_source_id: itemId };
            const result = await getDataModels(page, 5, filters);
            setDataModelData(result.items);
            setDataModelTotal(result.total);
            setDataModelPage(result.page);
        } catch (error) {
            console.error(error);
        } finally {
            setDataModelLoading(false);
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
                <h1 className="text-3xl font-bold tracking-tight">DataSource Details</h1>
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
                            <Label className="text-muted-foreground">{t('models.data_source.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('name', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.data_source.fields.name')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.name ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('type', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.data_source.fields.type')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.type ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('host', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.data_source.fields.host')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.host ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('port', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.data_source.fields.port')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.port ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('description', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.data_source.fields.description')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.description ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                    </CardContent>
                </Card>

                

                

                

                
                
                
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>{t('models.data_model.name')}s</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-md border">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>ID</TableHead>
                                        <TableHead>Identifier</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    { data_modelsLoading ? (
                                        <TableRow>
                                            <TableCell colSpan={2} className="h-24 text-center">
                                                <Loader2 className="mx-auto h-6 w-6 animate-spin" />
                                            </TableCell>
                                        </TableRow>
                                    ) : data_modelsData.length > 0 ? (
                                        data_modelsData.map((item) => (
                                            <TableRow key={item.id}>
                                                <TableCell>{item.id}</TableCell>
                                                <TableCell>{item.identifier }</TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell colSpan={2} className="h-24 text-center">
                                                No datamodels found.
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
                                onClick={() => fetchDataModels(parseInt(id!), data_modelsPage - 1)}
                                disabled={ data_modelsPage <= 1 || data_modelsLoading}
                            >
                                Previous
                            </Button>
                            <span className="text-sm">
                                Page { data_modelsPage } of { Math.ceil(data_modelsTotal / 5) || 1 }
                            </span>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchDataModels(parseInt(id!), data_modelsPage + 1)}
                                disabled={ data_modelsPage >= Math.ceil(data_modelsTotal / 5) || data_modelsLoading}
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

export default DataSourceDetailPage;