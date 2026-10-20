import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Eye, Loader2, Save, Pencil, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useTagStore } from '../../stores/useTagStore';
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







import { getTagProducts } from '../../services/tag';






const TagDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useTagStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "name": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    };
    const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
      const fp = fieldRolePerms[fieldName];
      if (!fp) return true;
      return (fp[userRole] || '').includes(perm);
    };
    
    // State to store resolved foreign key data
    

    // State for M2M data
    

    // State for Reverse M2M data
    
    
    
    const [productsData, setProductsData] = useState<any[]>([]);
    const [productsTotal, setProductsTotal] = useState(0);
    const [productsPage, setProductsPage] = useState(1);
    const [productsLoading, setProductsLoading] = useState(false);
    
    
    

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
                    
                }
            });
            
            // Fetch M2M data
            

            // Fetch Reverse M2M data
            
            
            
            fetchTagProducts(itemId, 1);
            
            
            

            // Fetch Reverse FK data
            

            // Fetch Timeseries realtime data
            

            // Fetch Timeseries history data
            
        }
    }, [id, fetchItem]);

    

    
    
    
    const fetchTagProducts = async (itemId: number, page: number) => {
        setProductsLoading(true);
        try {
            const result = await getTagProducts(itemId, page, 5);
            setProductsData(result.items);
            setProductsTotal(result.total);
            setProductsPage(result.page);
        } catch (error) {
            console.error(error);
        } finally {
            setProductsLoading(false);
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
                <h1 className="text-3xl font-bold tracking-tight">Tag Details</h1>
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
                            <Label className="text-muted-foreground">{t('models.tag.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('name', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.tag.fields.name')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.name ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        
                    </CardContent>
                </Card>

                

                

                
                
                
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>{t('models.product.name')}s</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-md border">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        
                                        <TableHead>{t('models.product.fields.id')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.name')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.status')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.is_featured')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.category_id')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.variants')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.meta_data')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.created_at')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.cover_image')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.manual_file')}</TableHead>
                                        
                                        <TableHead>{t('models.product.fields.internal_note')}</TableHead>
                                        
                                        <TableHead className="w-16">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    { productsLoading ? (
                                        <TableRow>
                                            <TableCell colSpan={ 12 } className="h-24 text-center">
                                                <Loader2 className="mx-auto h-6 w-6 animate-spin" />
                                            </TableCell>
                                        </TableRow>
                                    ) : productsData.length > 0 ? (
                                        productsData.map((item) => (
                                            <TableRow key={item.id}>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.id === 'object' ? JSON.stringify(item.id) : String(item.id ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.name === 'object' ? JSON.stringify(item.name) : String(item.name ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    <Badge variant="outline">{item.status}</Badge>
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {item.is_featured ? 'Yes' : 'No'}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {item.category_id_label || (item.category_id ? `ID: ${item.category_id}` : '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.variants === 'object' ? JSON.stringify(item.variants) : String(item.variants ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.meta_data === 'object' ? JSON.stringify(item.meta_data) : String(item.meta_data ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {formatDateTime(item.created_at, timeZone)}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.cover_image === 'object' ? JSON.stringify(item.cover_image) : String(item.cover_image ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.manual_file === 'object' ? JSON.stringify(item.manual_file) : String(item.manual_file ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.internal_note === 'object' ? JSON.stringify(item.internal_note) : String(item.internal_note ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    <Button variant="ghost" size="icon" onClick={() => navigate(`/products/${item.id}`)}>
                                                        <Eye className="h-4 w-4" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell colSpan={ 12 } className="h-24 text-center">
                                                No products found.
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
                                onClick={() => fetchTagProducts(parseInt(id!), productsPage - 1)}
                                disabled={ productsPage <= 1 || productsLoading}
                            >
                                Previous
                            </Button>
                            <span className="text-sm">
                                Page { productsPage } of { Math.ceil(productsTotal / 5) || 1 }
                            </span>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchTagProducts(parseInt(id!), productsPage + 1)}
                                disabled={ productsPage >= Math.ceil(productsTotal / 5) || productsLoading}
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

export default TagDetailPage;