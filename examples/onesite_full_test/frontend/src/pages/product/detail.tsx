import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Eye, Loader2, Save, Pencil, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useProductStore } from '../../stores/useProductStore';
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


import { getCategory } from '../../services/category';




import { getProductTags } from '../../services/product';






const ProductDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useProductStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "name": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "status": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "is_featured": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "category_id": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "variants": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "meta_data": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "created_at": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "cover_image": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "manual_file": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "import_source": {"admin": "c", "developer": "c", "user": "c"},
    
    
    
      "internal_note": {"admin": "cru", "developer": "cru", "user": "cru"},
    
    
    };
    const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
      const fp = fieldRolePerms[fieldName];
      if (!fp) return true;
      return (fp[userRole] || '').includes(perm);
    };
    
    // State to store resolved foreign key data
    
    const [categoryData, setCategoryData] = useState<any>(null);
    

    // State for M2M data
    
    
    const [tag_idsData, setTagData] = useState<any[]>([]);
    const [tag_idsTotal, setTagTotal] = useState(0);
    const [tag_idsPage, setTagPage] = useState(1);
    const [tag_idsLoading, setTagLoading] = useState(false);
    
    

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
                    
                    if (item.category_id) {
                        getCategory(item.category_id).then(res => {
                             if (res) {
                                 setCategoryData(res);
                             }
                        });
                    }
                    
                }
            });
            
            // Fetch M2M data
            
            
            fetchTags(itemId, 1);
            
            

            // Fetch Reverse M2M data
            

            // Fetch Reverse FK data
            

            // Fetch Timeseries realtime data
            

            // Fetch Timeseries history data
            
        }
    }, [id, fetchItem]);

    
    
    const fetchTags = async (itemId: number, page: number) => {
        setTagLoading(true);
        try {
            const result = await getProductTags(itemId, page, 5); // Small page size for detail view
            setTagData(result.items);
            setTagTotal(result.total);
            setTagPage(result.page);
        } catch (error) {
            console.error(error);
        } finally {
            setTagLoading(false);
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
                <h1 className="text-3xl font-bold tracking-tight">Product Details</h1>
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
                            <Label className="text-muted-foreground">{t('models.product.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('name', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.name')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.name ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('status', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.status')}</Label>
                            <div className="font-medium">
                                
                                <Badge variant="outline">{currentItem.status}</Badge>
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('is_featured', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.is_featured')}</Label>
                            <div className="font-medium">
                                
                                <Badge variant={currentItem.is_featured ? "default" : "secondary"}>
                                    {currentItem.is_featured ? 'Yes' : 'No'}
                                </Badge>
                                
                            </div>
                        </div>
                        )}
                        
                        
                        
                        {hasFieldPerm('variants', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.variants')}</Label>
                            <div className="font-medium">
                                
                                <pre className="whitespace-pre-wrap break-words rounded-md border bg-muted/40 p-2 text-sm">
                                    {currentItem.variants !== undefined && currentItem.variants !== null
                                      ? JSON.stringify(currentItem.variants, null, 2)
                                      : '-'}
                                </pre>
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('meta_data', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.meta_data')}</Label>
                            <div className="font-medium">
                                
                                <pre className="whitespace-pre-wrap break-words rounded-md border bg-muted/40 p-2 text-sm">
                                    {currentItem.meta_data !== undefined && currentItem.meta_data !== null
                                      ? JSON.stringify(currentItem.meta_data, null, 2)
                                      : '-'}
                                </pre>
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('created_at', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.created_at')}</Label>
                            <div className="font-medium">
                                
                                <span className="text-muted-foreground">{formatDateTime(currentItem.created_at, timeZone)}</span>
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('cover_image', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.cover_image')}</Label>
                            <div className="font-medium">
                                
                                {currentItem.cover_image ? (
                                    <div className="relative aspect-video w-full max-w-sm overflow-hidden rounded-lg border bg-muted">
                                        <img
                                            src={currentItem.cover_image}
                                            alt="cover_image"
                                            className="h-full w-full object-cover"
                                        />
                                    </div>
                                ) : (
                                    <span className="text-muted-foreground italic">No image</span>
                                )}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('manual_file', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.manual_file')}</Label>
                            <div className="font-medium">
                                
                                {currentItem.manual_file ? (
                                    <FileUpload
                                        value={currentItem.manual_file}
                                        onChange={() => {}}
                                        readOnly={true}
                                        allowDownload={ false }
                                    />
                                ) : (
                                    <span className="text-muted-foreground italic">No file</span>
                                )}
                                
                            </div>
                        </div>
                        )}
                        
                        
                        
                        {hasFieldPerm('internal_note', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.product.fields.internal_note')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.internal_note ?? '-')}
                                
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
                                <Label className="text-lg font-semibold">{t('models.category.name')}</Label>
                                <Badge variant="outline">ID: {currentItem.category_id}</Badge>
                            </div>
                            <div className="rounded-md border p-4">
                                { categoryData ? (
                                    <div className="space-y-2">
                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            <span className="text-muted-foreground">Display Name:</span>
                                            <span className="font-medium">{ categoryData.name }</span>
                                            
                                            {/* Show all readable fields for the target model */}
                                            
                                            
                                            
                                            { categoryData.id !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.category.fields.id')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(categoryData.id ?? '-')}
                                                    
                                                </span>
                                                </>
                                            )}
                                            
                                            
                                            
                                            
                                            
                                            { categoryData.description !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.category.fields.description')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(categoryData.description ?? '-')}
                                                    
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
                        <CardTitle>{t('models.tag.name')}s</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-md border">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        
                                        <TableHead>{t('models.tag.fields.id')}</TableHead>
                                        
                                        <TableHead>{t('models.tag.fields.name')}</TableHead>
                                        
                                        <TableHead className="w-16">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    { tag_idsLoading ? (
                                        <TableRow>
                                            <TableCell colSpan={ 3 } className="h-24 text-center">
                                                <Loader2 className="mx-auto h-6 w-6 animate-spin" />
                                            </TableCell>
                                        </TableRow>
                                    ) : tag_idsData.length > 0 ? (
                                        tag_idsData.map((item) => (
                                            <TableRow key={item.id}>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.id === 'object' ? JSON.stringify(item.id) : String(item.id ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.name === 'object' ? JSON.stringify(item.name) : String(item.name ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    <Button variant="ghost" size="icon" onClick={() => navigate(`/tags/${item.id}`)}>
                                                        <Eye className="h-4 w-4" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell colSpan={ 3 } className="h-24 text-center">
                                                No tags found.
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
                                onClick={() => fetchTags(parseInt(id!), tag_idsPage - 1)}
                                disabled={ tag_idsPage <= 1 || tag_idsLoading}
                            >
                                Previous
                            </Button>
                            <span className="text-sm">
                                Page { tag_idsPage } of { Math.ceil(tag_idsTotal / 5) || 1 }
                            </span>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchTags(parseInt(id!), tag_idsPage + 1)}
                                disabled={ tag_idsPage >= Math.ceil(tag_idsTotal / 5) || tag_idsLoading}
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

export default ProductDetailPage;