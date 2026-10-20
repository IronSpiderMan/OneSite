import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Eye, Loader2, Save, Pencil, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useBookStore } from '../../stores/useBookStore';
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


import { getAuthor } from '../../services/author';




import { getBookSubjects } from '../../services/book';






const BookDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useBookStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "title": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "published_at": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "author_id": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    };
    const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
      const fp = fieldRolePerms[fieldName];
      if (!fp) return true;
      return (fp[userRole] || '').includes(perm);
    };
    
    // State to store resolved foreign key data
    
    const [authorData, setAuthorData] = useState<any>(null);
    

    // State for M2M data
    
    
    const [subject_idsData, setSubjectData] = useState<any[]>([]);
    const [subject_idsTotal, setSubjectTotal] = useState(0);
    const [subject_idsPage, setSubjectPage] = useState(1);
    const [subject_idsLoading, setSubjectLoading] = useState(false);
    
    

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
                    
                    if (item.author_id) {
                        getAuthor(item.author_id).then(res => {
                             if (res) {
                                 setAuthorData(res);
                             }
                        });
                    }
                    
                }
            });
            
            // Fetch M2M data
            
            
            fetchSubjects(itemId, 1);
            
            

            // Fetch Reverse M2M data
            

            // Fetch Reverse FK data
            

            // Fetch Timeseries realtime data
            

            // Fetch Timeseries history data
            
        }
    }, [id, fetchItem]);

    
    
    const fetchSubjects = async (itemId: number, page: number) => {
        setSubjectLoading(true);
        try {
            const result = await getBookSubjects(itemId, page, 5); // Small page size for detail view
            setSubjectData(result.items);
            setSubjectTotal(result.total);
            setSubjectPage(result.page);
        } catch (error) {
            console.error(error);
        } finally {
            setSubjectLoading(false);
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
                <h1 className="text-3xl font-bold tracking-tight">Book Details</h1>
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
                            <Label className="text-muted-foreground">{t('models.book.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('title', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.book.fields.title')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.title ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('published_at', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.book.fields.published_at')}</Label>
                            <div className="font-medium">
                                
                                <span className="text-muted-foreground">{formatDateTime(currentItem.published_at, timeZone)}</span>
                                
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
                                <Label className="text-lg font-semibold">{t('models.author.name')}</Label>
                                <Badge variant="outline">ID: {currentItem.author_id}</Badge>
                            </div>
                            <div className="rounded-md border p-4">
                                { authorData ? (
                                    <div className="space-y-2">
                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            <span className="text-muted-foreground">Display Name:</span>
                                            <span className="font-medium">{ authorData.name }</span>
                                            
                                            {/* Show all readable fields for the target model */}
                                            
                                            
                                            
                                            { authorData.id !== undefined && (
                                                <>
                                                <span className="text-muted-foreground">{t('models.author.fields.id')}:</span>
                                                <span className="font-medium">
                                                    
                                                    {String(authorData.id ?? '-')}
                                                    
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
                        <CardTitle>{t('models.subject.name')}s</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="rounded-md border">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        
                                        <TableHead>{t('models.subject.fields.id')}</TableHead>
                                        
                                        <TableHead>{t('models.subject.fields.title')}</TableHead>
                                        
                                        <TableHead className="w-16">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    { subject_idsLoading ? (
                                        <TableRow>
                                            <TableCell colSpan={ 3 } className="h-24 text-center">
                                                <Loader2 className="mx-auto h-6 w-6 animate-spin" />
                                            </TableCell>
                                        </TableRow>
                                    ) : subject_idsData.length > 0 ? (
                                        subject_idsData.map((item) => (
                                            <TableRow key={item.id}>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.id === 'object' ? JSON.stringify(item.id) : String(item.id ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    
                                                    {typeof item.title === 'object' ? JSON.stringify(item.title) : String(item.title ?? '-')}
                                                    
                                                </TableCell>
                                                
                                                <TableCell>
                                                    <Button variant="ghost" size="icon" onClick={() => navigate(`/subjects/${item.id}`)}>
                                                        <Eye className="h-4 w-4" />
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow>
                                            <TableCell colSpan={ 3 } className="h-24 text-center">
                                                No subjects found.
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
                                onClick={() => fetchSubjects(parseInt(id!), subject_idsPage - 1)}
                                disabled={ subject_idsPage <= 1 || subject_idsLoading}
                            >
                                Previous
                            </Button>
                            <span className="text-sm">
                                Page { subject_idsPage } of { Math.ceil(subject_idsTotal / 5) || 1 }
                            </span>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => fetchSubjects(parseInt(id!), subject_idsPage + 1)}
                                disabled={ subject_idsPage >= Math.ceil(subject_idsTotal / 5) || subject_idsLoading}
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

export default BookDetailPage;