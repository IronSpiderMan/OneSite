import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Eye, Loader2, Save, Pencil, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useUserProfileStore } from '../../stores/useUserProfileStore';
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








const UserProfileDetailPage: React.FC = () => {
    const { t } = useTranslation();
    const timeZone = getUserTimeZone();
    const { id } = useParams<{ id: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { fetchItem, currentItem, loading } = useUserProfileStore();
    const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
    const rolePermissions: Record<string, string> = {"admin": "cru", "developer": "crud", "user": "cru"};
    const userPerms = rolePermissions[userRole] || '';
    const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

    // Field-level role-based permissions (Layer 2)
    const fieldRolePerms: Record<string, Record<string, string>> = {
    
    
      "id": {"admin": "r", "developer": "r", "user": "r"},
    
    
    
      "display_name": {"admin": "cru", "developer": "cru", "user": "cru"},
    
    
    
      "avatar": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "bio": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
    
    
    
      "phone": {"admin": "amin-rcu", "developer": "amin-rcu", "user": "amin-rcu"},
    
    
    
      "ssn": {"admin": "eveloper-r", "developer": "eveloper-r", "user": "eveloper-r"},
    
    
    
      "internal_note": {"admin": "u", "developer": "rcu", "user": "cru"},
    
    
    
      "loyalty_points": {"admin": "cru", "developer": "rcu", "user": "r"},
    
    
    
      "id_document": {"admin": "eveloper-rcu", "developer": "eveloper-rcu", "user": "eveloper-rcu"},
    
    
    
      "created_at": {"admin": "r", "developer": "r", "user": "r"},
    
    
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
                <h1 className="text-3xl font-bold tracking-tight">UserProfile Details</h1>
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
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.id')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.id ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('display_name', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.display_name')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.display_name ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('avatar', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.avatar')}</Label>
                            <div className="font-medium">
                                
                                {currentItem.avatar ? (
                                    <div className="relative aspect-video w-full max-w-sm overflow-hidden rounded-lg border bg-muted">
                                        <img
                                            src={currentItem.avatar}
                                            alt="avatar"
                                            className="h-full w-full object-cover"
                                        />
                                    </div>
                                ) : (
                                    <span className="text-muted-foreground italic">No image</span>
                                )}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('bio', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.bio')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.bio ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('phone', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.phone')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.phone ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('ssn', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.ssn')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.ssn ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('internal_note', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.internal_note')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.internal_note ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('loyalty_points', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.loyalty_points')}</Label>
                            <div className="font-medium">
                                
                                {String(currentItem.loyalty_points ?? '-')}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('id_document', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.id_document')}</Label>
                            <div className="font-medium">
                                
                                {currentItem.id_document ? (
                                    <FileUpload
                                        value={currentItem.id_document}
                                        onChange={() => {}}
                                        readOnly={true}
                                        allowDownload={ true }
                                    />
                                ) : (
                                    <span className="text-muted-foreground italic">No file</span>
                                )}
                                
                            </div>
                        </div>
                        )}
                        
                        {hasFieldPerm('created_at', 'r') && (
                        <div className="space-y-1">
                            <Label className="text-muted-foreground">{t('models.user_profile.fields.created_at')}</Label>
                            <div className="font-medium">
                                
                                <span className="text-muted-foreground">{formatDateTime(currentItem.created_at, timeZone)}</span>
                                
                            </div>
                        </div>
                        )}
                        
                        
                    </CardContent>
                </Card>

                

                

                

                

                
            </div>
        </div>
    );
};

export default UserProfileDetailPage;