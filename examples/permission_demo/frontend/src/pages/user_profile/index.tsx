import React, { useState, useEffect, useRef } from 'react';
import { Plus, Pencil, Trash2, Loader2, Eye, Trash } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { 
    UserProfile
    
    
    
    
} from '../../services/user_profile';

import { useUserProfileStore } from '../../stores/useUserProfileStore';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { JsonInput } from '../../components/ui/json-input';
import { JsonModelEditor, JsonModelArrayEditor } from '../../components/ui/json-model-editor';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';

import { Modal } from '../../components/ui/modal';

import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { ImageUpload } from '../../components/ui/image-upload';
import { FileUpload } from '../../components/ui/file-upload';
import { FileInput } from '../../components/ui/file-input';
import { SearchableSelect } from '../../components/ui/searchable-select';
import { LinkTableOrderedSelect } from '../../components/ui/link-table-ordered-select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../../components/ui/alert-dialog';
import { TimePicker } from '../../components/ui/time-picker';
import { formatDateTime, formatTime, getUserTimeZone } from '../../lib/datetime';



const UserProfilePage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, loading, fetchData, refreshData, fetchItem, createItem, updateItem, deleteItem, bulkDeleteItem } = useUserProfileStore();
  const timeZone = getUserTimeZone();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [searchValues, setSearchValues] = useState<Record<string, any>>({});
  const [gotoPageInput, setGotoPageInput] = useState('');
  
  

  // Role-based permissions
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
    if (!fp) return true; // no restrictions = allowed
    return (fp[userRole] || '').includes(perm);
  };

  

  // User model special handling: user role can only access /me
  

  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  

  const { register, handleSubmit, reset, setValue, control } = useForm();

  

  useEffect(() => {
    
    fetchData();
    
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync page input with current page from store
  const storePage = useUserProfileStore(state => state.page);
  useEffect(() => {
    setGotoPageInput(String(storePage));
  }, [storePage]);

  const handleCreate = () => {
    
    setEditingId(null);
    reset();
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    setIsModalOpen(true);
    
  };

  

  

  

  

  const handleEdit = async (record: UserProfile) => {
    
    setEditingId(record.id);
    const full = await fetchItem(record.id);
    const item = full || record;
    // Set form values
    
    
    setValue('id', item.id);
    
    
    
    setValue('display_name', item.display_name);
    
    
    
    setValue('avatar', item.avatar);
    
    
    
    setValue('bio', item.bio);
    
    
    
    setValue('phone', item.phone);
    
    
    
    setValue('ssn', item.ssn);
    
    
    
    setValue('internal_note', item.internal_note);
    
    
    
    setValue('loyalty_points', item.loyalty_points);
    
    
    
    setValue('id_document', item.id_document);
    
    
    
    setValue('created_at', item.created_at);
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    setIsModalOpen(true);
    
  };

  const requestDelete = (id: number) => {
    setDeleteId(id);
    setDeleteOpen(true);
  };

  const confirmDelete = async () => {
    if (!deleteId) return;
    setIsDeleting(true);
    try {
      await deleteItem(deleteId);
      toast.success(t('toast.delete_success', 'Deleted'));
      
    } catch (error: any) {
      const detail = error?.response?.data?.detail || t('toast.delete_failed', 'Delete failed');
      toast.error(detail);
      console.error(error);
    } finally {
      setIsDeleting(false);
      setDeleteOpen(false);
      setDeleteId(null);
    }
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === data.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(data.map((item) => item.id));
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const confirmBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    setIsBulkDeleting(true);
    try {
      await bulkDeleteItem(selectedIds);
      toast.success(t('toast.delete_success', 'Deleted'));
      setSelectedIds([]);
      
    } catch (error: any) {
      const detail = error?.response?.data?.detail || t('toast.delete_failed', 'Delete failed');
      toast.error(detail);
      console.error(error);
    } finally {
      setIsBulkDeleting(false);
      setBulkDeleteOpen(false);
    }
  };

  
  const onSubmit = async (values: any) => {
    try {
      
      if (editingId) {
        await updateItem(editingId, values);
        toast.success(t('toast.update_success', 'Updated'));
      } else {
        await createItem(values);
        toast.success(t('toast.create_success', 'Created'));
      }
      setIsModalOpen(false);
      
    } catch (error) {
      toast.error(t('toast.save_failed', 'Save failed'));
      console.error(error);
    }
  };
  

  const applySearch = () => {
    const next: Record<string, any> = {};
    
    
    
    
    
    if (searchValues['display_name']) next['display_name'] = searchValues['display_name'];
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    fetchData(1, useUserProfileStore.getState().size, next);
    
  };

  const resetSearch = () => {
    setSearchValues({});
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    fetchData(1, useUserProfileStore.getState().size, {});
    
  };

  return (
    <div className="space-y-6">
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('alert.delete_title', 'Confirm deletion')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('common.confirm_delete')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction disabled={isDeleting} onClick={confirmDelete}>
              {isDeleting ? t('common.loading') : t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={bulkDeleteOpen} onOpenChange={setBulkDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('alert.delete_title', 'Confirm deletion')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('alert.bulk_delete_confirm', `Are you sure you want to delete ${selectedIds.length} items?`)}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isBulkDeleting}>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction disabled={isBulkDeleting} onClick={confirmBulkDelete}>
              {isBulkDeleting ? t('common.loading') : t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">{t('models.user_profile.name')}s</h1>
        <div className="flex items-center gap-4">
          
          
          {selectedIds.length > 0 && hasPermission('d') && (
            <Button variant="destructive" onClick={() => setBulkDeleteOpen(true)}>
              <Trash className="mr-2 h-4 w-4" /> {t('common.bulk_delete', 'Delete')} ({selectedIds.length})
            </Button>
          )}
          {hasPermission('c') && (
            <Button onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" /> {t('common.create')} {t('models.user_profile.name')}
            </Button>
          )}
        </div>
      </div>

      
      
          
      
          
      
      
      
          
      
          
      
          
      
          
      
          
      
          
      
          
      
          
      
      
      <div className="rounded-md border bg-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm font-medium">{t('common.filters', 'Filters')}</div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" type="button" onClick={resetSearch}>{t('common.reset', 'Reset')}</Button>
            <Button size="sm" type="button" onClick={applySearch}>{t('common.search')}</Button>
          </div>
        </div>
        <div className="mt-4 max-h-[40vh] overflow-auto pr-2">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          
              
          
              
          <div className="space-y-2">
            <Label>{t('models.user_profile.fields.display_name')}</Label>
            
            <Input
              className="h-9"
              value={searchValues['display_name'] || ''}
              onChange={(e) => setSearchValues((s) => ({ ...s, ['display_name']: e.target.value }))}
              placeholder={t('common.search')}
            />
            
          </div>
          
          
              
          
              
          
              
          
              
          
              
          
              
          
              
          
              
          
          </div>
        </div>
      </div>
      


      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]">
                <input
                  type="checkbox"
                  checked={selectedIds.length === data.length && data.length > 0}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 rounded border-gray-300"
                />
              </TableHead>
              
              {hasFieldPerm('id', 'r') && (
              <TableHead>{t('models.user_profile.fields.id')}</TableHead>
              )}
              
              {hasFieldPerm('display_name', 'r') && (
              <TableHead>{t('models.user_profile.fields.display_name')}</TableHead>
              )}
              
              {hasFieldPerm('avatar', 'r') && (
              <TableHead>{t('models.user_profile.fields.avatar')}</TableHead>
              )}
              
              {hasFieldPerm('bio', 'r') && (
              <TableHead>{t('models.user_profile.fields.bio')}</TableHead>
              )}
              
              {hasFieldPerm('phone', 'r') && (
              <TableHead>{t('models.user_profile.fields.phone')}</TableHead>
              )}
              
              {hasFieldPerm('ssn', 'r') && (
              <TableHead>{t('models.user_profile.fields.ssn')}</TableHead>
              )}
              
              {hasFieldPerm('internal_note', 'r') && (
              <TableHead>{t('models.user_profile.fields.internal_note')}</TableHead>
              )}
              
              {hasFieldPerm('loyalty_points', 'r') && (
              <TableHead>{t('models.user_profile.fields.loyalty_points')}</TableHead>
              )}
              
              {hasFieldPerm('id_document', 'r') && (
              <TableHead>{t('models.user_profile.fields.id_document')}</TableHead>
              )}
              
              {hasFieldPerm('created_at', 'r') && (
              <TableHead>{t('models.user_profile.fields.created_at')}</TableHead>
              )}
              
              <TableHead className="w-[100px]">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
                <TableRow>
                    <TableCell colSpan={ 12 } className="h-24 text-center">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                    </TableCell>
                </TableRow>
            ) : data.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={ 12 } className="h-24 text-center">
                        {t('common.no result')}
                    </TableCell>
                </TableRow>
            ) : (
                data.map((item) => (
                <TableRow key={item.id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={() => toggleSelect(item.id)}
                        className="h-4 w-4 rounded border-gray-300"
                      />
                    </TableCell>
                    
                    {hasFieldPerm('id', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.id)}>
                        {String(item.id)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('display_name', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.display_name)}>
                        {String(item.display_name)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('avatar', 'r') && (
                    <TableCell>
                        
                        <div className="h-10 w-10 overflow-hidden rounded-md border bg-muted">
                            <img
                                src={item.avatar || 'https://placehold.co/100?text=No+Image'}
                                alt="avatar"
                                className="h-full w-full object-cover"
                                onError={(e) => {
                                    (e.target as HTMLImageElement).src = 'https://placehold.co/100?text=Error';
                                }}
                            />
                        </div>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('bio', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.bio)}>
                        {String(item.bio)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('phone', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.phone)}>
                        {String(item.phone)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('ssn', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.ssn)}>
                        {String(item.ssn)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('internal_note', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.internal_note)}>
                        {String(item.internal_note)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('loyalty_points', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.loyalty_points)}>
                        {String(item.loyalty_points)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('id_document', 'r') && (
                    <TableCell>
                        
                        {item.id_document ? (
                            <div className="flex items-center gap-2">
                                <span
                                    className="flex items-center text-primary cursor-pointer hover:underline"
                                    title={item.id_document}
                                    onClick={() => {
                                        // TODO: Open preview
                                    }}
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                                    File
                                </span>
                                
                                <a
                                    href={item.id_document}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-muted-foreground hover:text-primary"
                                    title="Download"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                                </a>
                                
                            </div>
                        ) : (
                            <span className="text-muted-foreground">-</span>
                        )}
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('created_at', 'r') && (
                    <TableCell>
                        
                        <span className="text-muted-foreground">{formatDateTime(item.created_at, timeZone)}</span>
                        
                    </TableCell>
                    )}
                    
                    <TableCell className="flex items-center gap-2">
                        <>
                        
                        </>
                        {hasPermission('r') && (
                        <Button variant="ghost" size="icon" onClick={() => navigate(`/user_profiles/${item.id}`)}>
                            <Eye className="h-4 w-4" />
                        </Button>
                        )}
                        {hasPermission('u') && (
                        <Button variant="ghost" size="icon" onClick={() => handleEdit(item)}>
                            <Pencil className="h-4 w-4" />
                        </Button>
                        )}
                        {hasPermission('d') && (
                        <Button variant="ghost" size="icon" className="text-destructive" onClick={() => requestDelete(item.id)}>
                            <Trash2 className="h-4 w-4" />
                        </Button>
                        )}
                    </TableCell>
                </TableRow>
                ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="text-sm text-muted-foreground whitespace-nowrap">
            {t('common.page_info')} {useUserProfileStore(state => state.page)} {t('common.of_page')} {Math.ceil(useUserProfileStore(state => state.total) / useUserProfileStore(state => state.size)) || 1}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground whitespace-nowrap">{t('common.page_size', 'Page size')}:</span>
            <Select
              value={String(useUserProfileStore.getState().size)}
              onValueChange={(v) => {
                const newSize = Number(v);
                fetchData(1, newSize);
              }}
            >
              <SelectTrigger className="w-[80px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(1, useUserProfileStore.getState().size)}
            disabled={useUserProfileStore(state => state.page) <= 1 || loading}
          >
            {t('common.first')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(useUserProfileStore.getState().page - 1, useUserProfileStore.getState().size)}
            disabled={useUserProfileStore(state => state.page) <= 1 || loading}
          >
            {t('common.previous')}
          </Button>
          <div className="flex items-center gap-1">
            <Input
              type="number"
              min={1}
              max={Math.ceil(useUserProfileStore(state => state.total) / useUserProfileStore(state => state.size)) || 1}
              className="w-16 h-8 text-center"
              value={gotoPageInput}
              onChange={(e) => setGotoPageInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const page = Number(gotoPageInput);
                  const totalPages = Math.ceil(useUserProfileStore.getState().total / useUserProfileStore.getState().size) || 1;
                  if (page >= 1 && page <= totalPages) {
                    fetchData(page, useUserProfileStore.getState().size);
                  }
                }
              }}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(useUserProfileStore.getState().page + 1, useUserProfileStore.getState().size)}
            disabled={useUserProfileStore(state => state.page) >= Math.ceil(useUserProfileStore(state => state.total) / useUserProfileStore(state => state.size)) || loading}
          >
            {t('common.next')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const totalPages = Math.ceil(useUserProfileStore.getState().total / useUserProfileStore.getState().size) || 1;
              fetchData(totalPages, useUserProfileStore.getState().size);
            }}
            disabled={useUserProfileStore(state => state.page) >= Math.ceil(useUserProfileStore(state => state.total) / useUserProfileStore(state => state.size)) || loading}
          >
            {t('common.last')}
          </Button>
        </div>
      </div>



      <Modal
        title={editingId ? `${t('common.edit')} UserProfile` : `${t('common.create')} UserProfile`}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      >
            <div className="max-h-[80vh] overflow-y-auto pr-2">
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          
          {(!editingId ? hasFieldPerm('id', 'c') : hasFieldPerm('id', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="id">{t('models.user_profile.fields.id')}</Label>
            
            <Input
                id="id"
                
                type="number"
                
                {...register('id', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('display_name', 'c') : hasFieldPerm('display_name', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="display_name">{t('models.user_profile.fields.display_name')}</Label>
            
            <Input
                id="display_name"
                
                type="text"
                
                {...register('display_name', { required: !editingId ? true : true })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('avatar', 'c') : hasFieldPerm('avatar', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="avatar">{t('models.user_profile.fields.avatar')}</Label>
            
            <Controller
                control={control}
                name="avatar"
                render={({ field: { onChange, value } }) => (
                    <ImageUpload
                        value={value}
                        onChange={onChange}
                    />
                )}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('bio', 'c') : hasFieldPerm('bio', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="bio">{t('models.user_profile.fields.bio')}</Label>
            
            <Input
                id="bio"
                
                type="text"
                
                {...register('bio', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('phone', 'c') : hasFieldPerm('phone', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="phone">{t('models.user_profile.fields.phone')}</Label>
            
            <Input
                id="phone"
                
                type="text"
                
                {...register('phone', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('ssn', 'c') : hasFieldPerm('ssn', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="ssn">{t('models.user_profile.fields.ssn')}</Label>
            
            <Input
                id="ssn"
                
                type="text"
                
                {...register('ssn', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('internal_note', 'c') : hasFieldPerm('internal_note', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="internal_note">{t('models.user_profile.fields.internal_note')}</Label>
            
            <Input
                id="internal_note"
                
                type="text"
                
                {...register('internal_note', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('loyalty_points', 'c') : hasFieldPerm('loyalty_points', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="loyalty_points">{t('models.user_profile.fields.loyalty_points')}</Label>
            
            <Input
                id="loyalty_points"
                
                type="number"
                
                {...register('loyalty_points', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('id_document', 'c') : hasFieldPerm('id_document', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="id_document">{t('models.user_profile.fields.id_document')}</Label>
            
                        <Controller
                            control={control}
                            name="id_document"
                            render={({ field: { onChange, value } }) => (
                                <FileUpload
                                    value={value}
                                    onChange={onChange}
                                    allowDownload={ true }
                                />
                            )}
                        />
                        
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('created_at', 'c') : hasFieldPerm('created_at', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="created_at">{t('models.user_profile.fields.created_at')}</Label>
            
            <Input
                id="created_at"
                
                type="datetime-local"
                
                {...register('created_at', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          

          
          <div className="flex justify-end space-x-2 pt-4">
            <Button variant="outline" type="button" onClick={() => setIsModalOpen(false)}>{t('common.cancel')}</Button>
            <Button type="submit">{t('common.save')}</Button>
          </div>
        </form>
            </div>
      </Modal>
      

      
    </div>
  );
};

export default UserProfilePage;