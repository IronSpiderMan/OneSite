import React, { useState, useEffect, useRef } from 'react';
import { Plus, Pencil, Trash2, Loader2, Eye, Trash } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { 
    User
    
    
    
    
} from '../../services/user';

import { useUserStore } from '../../stores/useUserStore';
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



const UserPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, loading, fetchData, refreshData, fetchItem, createItem, updateItem, deleteItem, bulkDeleteItem } = useUserStore();
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
  const rolePermissions: Record<string, string> = {"admin": "crud", "developer": "crud", "user": "r"};
  const userPerms = rolePermissions[userRole] || '';

  const hasPermission = (perm: 'r' | 'c' | 'u' | 'd') => userPerms.includes(perm);

  // Field-level role-based permissions (Layer 2)
  const fieldRolePerms: Record<string, Record<string, string>> = {
  
  
    "email": {"admin": "rc", "developer": "rc", "user": "rc"},
  
  
  
    "full_name": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
  
  
  
    "avatar": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
  
  
  
    "is_active": {"admin": "r", "developer": "r", "user": "r"},
  
  
  
    "role": {"admin": "rc", "developer": "rc", "user": "rc"},
  
  
  
    "id": {"admin": "r", "developer": "r", "user": "r"},
  
  
  
    "hashed_password": {"admin": "", "developer": "", "user": ""},
  
  
  
    "created_at": {"admin": "r", "developer": "r", "user": "r"},
  
  
  
    "updated_at": {"admin": "r", "developer": "r", "user": "r"},
  
  
  
  
  };
  const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
    const fp = fieldRolePerms[fieldName];
    if (!fp) return true; // no restrictions = allowed
    return (fp[userRole] || '').includes(perm);
  };

  

  // User model special handling: user role can only access /me
  
  useEffect(() => {
    if (userRole === 'user') {
      // Redirect to /users/me for user role
      navigate('/users/me');
    }
  }, [userRole, navigate]);
  

  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  

  const { register, handleSubmit, reset, setValue, control } = useForm();

  

  useEffect(() => {
    
    fetchData();
    
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync page input with current page from store
  const storePage = useUserStore(state => state.page);
  useEffect(() => {
    setGotoPageInput(String(storePage));
  }, [storePage]);

  const handleCreate = () => {
    
    setEditingId(null);
    reset();
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    setIsModalOpen(true);
    
  };

  

  

  

  

  const handleEdit = async (record: User) => {
    
    setEditingId(record.id);
    const full = await fetchItem(record.id);
    const item = full || record;
    // Set form values
    
    
    setValue('email', item.email);
    
    
    
    setValue('full_name', item.full_name);
    
    
    
    setValue('avatar', item.avatar);
    
    
    
    setValue('is_active', item.is_active);
    
    
    
    setValue('role', item.role);
    
    
    
    setValue('id', item.id);
    
    
    
    
    
    setValue('created_at', item.created_at);
    
    
    
    setValue('updated_at', item.updated_at);
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
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
    
    
    
    if (searchValues['email']) next['email'] = searchValues['email'];
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    fetchData(1, useUserStore.getState().size, next);
    
  };

  const resetSearch = () => {
    setSearchValues({});
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    fetchData(1, useUserStore.getState().size, {});
    
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
        <h1 className="text-3xl font-bold tracking-tight">{t('models.user.name')}s</h1>
        <div className="flex items-center gap-4">
          
          
          {selectedIds.length > 0 && hasPermission('d') && (
            <Button variant="destructive" onClick={() => setBulkDeleteOpen(true)}>
              <Trash className="mr-2 h-4 w-4" /> {t('common.bulk_delete', 'Delete')} ({selectedIds.length})
            </Button>
          )}
          {hasPermission('c') && (
            <Button onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" /> {t('common.create')} {t('models.user.name')}
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
            <Label>{t('models.user.fields.email')}</Label>
            
            <Input
              className="h-9"
              value={searchValues['email'] || ''}
              onChange={(e) => setSearchValues((s) => ({ ...s, ['email']: e.target.value }))}
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
              
              {hasFieldPerm('email', 'r') && (
              <TableHead>{t('models.user.fields.email')}</TableHead>
              )}
              
              {hasFieldPerm('full_name', 'r') && (
              <TableHead>{t('models.user.fields.full_name')}</TableHead>
              )}
              
              {hasFieldPerm('avatar', 'r') && (
              <TableHead>{t('models.user.fields.avatar')}</TableHead>
              )}
              
              {hasFieldPerm('is_active', 'r') && (
              <TableHead>{t('models.user.fields.is_active')}</TableHead>
              )}
              
              {hasFieldPerm('role', 'r') && (
              <TableHead>{t('models.user.fields.role')}</TableHead>
              )}
              
              {hasFieldPerm('id', 'r') && (
              <TableHead>{t('models.user.fields.id')}</TableHead>
              )}
              
              
              
              {hasFieldPerm('created_at', 'r') && (
              <TableHead>{t('models.user.fields.created_at')}</TableHead>
              )}
              
              {hasFieldPerm('updated_at', 'r') && (
              <TableHead>{t('models.user.fields.updated_at')}</TableHead>
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
                    
                    {hasFieldPerm('email', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.email)}>
                        {String(item.email)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('full_name', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.full_name)}>
                        {String(item.full_name)}
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
                    
                    {hasFieldPerm('is_active', 'r') && (
                    <TableCell>
                        
                        <Badge variant={item.is_active ? "default" : "secondary"}>
                            {item.is_active ? 'Yes' : 'No'}
                        </Badge>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('role', 'r') && (
                    <TableCell>
                        
                        <Badge variant="outline">{item.role}</Badge>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('id', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.id)}>
                        {String(item.id)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    
                    
                    {hasFieldPerm('created_at', 'r') && (
                    <TableCell>
                        
                        <span className="text-muted-foreground">{formatDateTime(item.created_at, timeZone)}</span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('updated_at', 'r') && (
                    <TableCell>
                        
                        <span className="text-muted-foreground">{formatDateTime(item.updated_at, timeZone)}</span>
                        
                    </TableCell>
                    )}
                    
                    
                    
                    <TableCell className="flex items-center gap-2">
                        <>
                        
                        </>
                        {hasPermission('r') && (
                        <Button variant="ghost" size="icon" onClick={() => navigate(`/users/${item.id}`)}>
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
            {t('common.page_info')} {useUserStore(state => state.page)} {t('common.of_page')} {Math.ceil(useUserStore(state => state.total) / useUserStore(state => state.size)) || 1}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground whitespace-nowrap">{t('common.page_size', 'Page size')}:</span>
            <Select
              value={String(useUserStore.getState().size)}
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
            onClick={() => fetchData(1, useUserStore.getState().size)}
            disabled={useUserStore(state => state.page) <= 1 || loading}
          >
            {t('common.first')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(useUserStore.getState().page - 1, useUserStore.getState().size)}
            disabled={useUserStore(state => state.page) <= 1 || loading}
          >
            {t('common.previous')}
          </Button>
          <div className="flex items-center gap-1">
            <Input
              type="number"
              min={1}
              max={Math.ceil(useUserStore(state => state.total) / useUserStore(state => state.size)) || 1}
              className="w-16 h-8 text-center"
              value={gotoPageInput}
              onChange={(e) => setGotoPageInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const page = Number(gotoPageInput);
                  const totalPages = Math.ceil(useUserStore.getState().total / useUserStore.getState().size) || 1;
                  if (page >= 1 && page <= totalPages) {
                    fetchData(page, useUserStore.getState().size);
                  }
                }
              }}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(useUserStore.getState().page + 1, useUserStore.getState().size)}
            disabled={useUserStore(state => state.page) >= Math.ceil(useUserStore(state => state.total) / useUserStore(state => state.size)) || loading}
          >
            {t('common.next')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const totalPages = Math.ceil(useUserStore.getState().total / useUserStore.getState().size) || 1;
              fetchData(totalPages, useUserStore.getState().size);
            }}
            disabled={useUserStore(state => state.page) >= Math.ceil(useUserStore(state => state.total) / useUserStore(state => state.size)) || loading}
          >
            {t('common.last')}
          </Button>
        </div>
      </div>



      <Modal
        title={editingId ? `${t('common.edit')} User` : `${t('common.create')} User`}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      >
            <div className="max-h-[80vh] overflow-y-auto pr-2">
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          
          {(!editingId ? hasFieldPerm('email', 'c') : hasFieldPerm('email', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="email">{t('models.user.fields.email')}</Label>
            
            <Input
                id="email"
                
                type="text"
                
                {...register('email', { required: !editingId ? true : true })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('full_name', 'c') : hasFieldPerm('full_name', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="full_name">{t('models.user.fields.full_name')}</Label>
            
            <Input
                id="full_name"
                
                type="text"
                
                {...register('full_name', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('avatar', 'c') : hasFieldPerm('avatar', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="avatar">{t('models.user.fields.avatar')}</Label>
            
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
          
          {(!editingId ? hasFieldPerm('is_active', 'c') : hasFieldPerm('is_active', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="is_active">{t('models.user.fields.is_active')}</Label>
            
            <div className="flex items-center space-x-2">
                <Controller
                    control={control}
                    name="is_active"
                    defaultValue={ true }
                    render={({ field: { onChange, value } }) => (
                        <Switch checked={value} onCheckedChange={onChange} id="is_active" />
                    )}
                />
                <Label htmlFor="is_active" className="font-normal text-muted-foreground">
                    {t('models.user.fields.is_active')}
                </Label>
            </div>
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('role', 'c') : hasFieldPerm('role', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="role">{t('models.user.fields.role')}</Label>
            
            <Controller
                control={control}
                name="role"
                render={({ field: { onChange, value } }) => {
                    // Filter enum values based on role for User.role field
                    
                    const filteredValues = userRole === 'developer'
                        ? ["user", "admin", "developer"]
                        : (["user", "admin", "developer"] as string[]).filter(v => v !== 'developer');
                    
                    return (
                    <Select onValueChange={onChange} defaultValue={value}>
                        <SelectTrigger>
                            <SelectValue placeholder={`${t('common.select')} ${t('models.user.fields.role')}`} />
                        </SelectTrigger>
                        <SelectContent>
                            {filteredValues.map((enumVal: string) => (
                                <SelectItem key={enumVal} value={enumVal}>{enumVal}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    )
                }}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('id', 'c') : hasFieldPerm('id', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="id">{t('models.user.fields.id')}</Label>
            
            <Input
                id="id"
                
                type="number"
                
                {...register('id', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('hashed_password', 'c') : hasFieldPerm('hashed_password', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="hashed_password">{t('models.user.fields.hashed_password')}</Label>
            
            <Input
                id="hashed_password"
                
                type="text"
                
                {...register('hashed_password', { required: !editingId ? true : true })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('created_at', 'c') : hasFieldPerm('created_at', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="created_at">{t('models.user.fields.created_at')}</Label>
            
            <Input
                id="created_at"
                
                type="datetime-local"
                
                {...register('created_at', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('updated_at', 'c') : hasFieldPerm('updated_at', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="updated_at">{t('models.user.fields.updated_at')}</Label>
            
            <Input
                id="updated_at"
                
                type="datetime-local"
                
                {...register('updated_at', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('password', 'c') : hasFieldPerm('password', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="password">{t('models.user.fields.password')}</Label>
            
            <Input
                id="password"
                
                type="text"
                
                {...register('password', { required: !editingId ? true : false })}
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

export default UserPage;