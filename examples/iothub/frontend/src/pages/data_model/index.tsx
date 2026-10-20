import React, { useState, useEffect, useRef } from 'react';
import { Plus, Pencil, Trash2, Loader2, Eye, Trash } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { 
    DataModel
    
    
    
    
} from '../../services/data_model';
import { useDataModelStore } from '../../stores/useDataModelStore';
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

import { getDataSources, getDataSource } from '../../services/data_source';



const DataModelPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, loading, fetchData, fetchItem, createItem, updateItem, deleteItem, bulkDeleteItem } = useDataModelStore();
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
    if (!fp) return true; // no restrictions = allowed
    return (fp[userRole] || '').includes(perm);
  };

  // User model special handling: user role can only access /me
  

  
  
  
  
  
  
  
  
  
  
  const [DataSourceIdValueLabels, setDataSourceIdValueLabels] = useState<Record<string, string>>({});
  
  
  

  const { register, handleSubmit, reset, setValue, control } = useForm();

  

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sync page input with current page from store
  const storePage = useDataModelStore(state => state.page);
  useEffect(() => {
    setGotoPageInput(String(storePage));
  }, [storePage]);

  const handleCreate = () => {
    setEditingId(null);
    reset();
    
    
    
    
    
    
    
    
    
    
    setDataSourceIdValueLabels({});
    
    
    
    setIsModalOpen(true);
  };

  

  

  

  const handleEdit = async (record: DataModel) => {
    setEditingId(record.id);
    const full = await fetchItem(record.id);
    const item = full || record;
    // Set form values
    
    
    setValue('id', item.id);
    
    
    
    setValue('name', item.name);
    
    
    
    setValue('identifier', item.identifier);
    
    
    
    setValue('version', item.version);
    
    
    
    setValue('data_source_id', item.data_source_id);
    
    
    
    
    
    
    
    
    
    
    
    
    try {
      if (item.data_source_id) {
        const fkItem = await getDataSource(item.data_source_id);
        if (fkItem) {
          setDataSourceIdValueLabels({ [String(fkItem.id)]: fkItem.name || String(fkItem.id) });
        } else {
          setDataSourceIdValueLabels({});
        }
      } else {
        setDataSourceIdValueLabels({});
      }
    } catch (error) {
      console.error(error);
      setDataSourceIdValueLabels({});
    }
    
    
    
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
    
    
    
    
    
    if (searchValues['name']) next['name'] = searchValues['name'];
    
    
    
    
    
    if (searchValues['identifier']) next['identifier'] = searchValues['identifier'];
    
    
    
    
    
    
    
    fetchData(1, useDataModelStore.getState().size, next);
  };

  const resetSearch = () => {
    setSearchValues({});
    fetchData(1, useDataModelStore.getState().size, {});
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
        <h1 className="text-3xl font-bold tracking-tight">{t('models.data_model.name')}s</h1>
        <div className="flex items-center gap-4">
          
          
          {selectedIds.length > 0 && hasPermission('d') && (
            <Button variant="destructive" onClick={() => setBulkDeleteOpen(true)}>
              <Trash className="mr-2 h-4 w-4" /> {t('common.bulk_delete', 'Delete')} ({selectedIds.length})
            </Button>
          )}
          {hasPermission('c') && (
            <Button onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" /> {t('common.create')} {t('models.data_model.name')}
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
            <Label>{t('models.data_model.fields.name')}</Label>
            
            <Input
              className="h-9"
              value={searchValues['name'] || ''}
              onChange={(e) => setSearchValues((s) => ({ ...s, ['name']: e.target.value }))}
              placeholder={t('common.search')}
            />
            
          </div>
          
          
              
          <div className="space-y-2">
            <Label>{t('models.data_model.fields.identifier')}</Label>
            
            <Input
              className="h-9"
              value={searchValues['identifier'] || ''}
              onChange={(e) => setSearchValues((s) => ({ ...s, ['identifier']: e.target.value }))}
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
              <TableHead>{t('models.data_model.fields.id')}</TableHead>
              )}
              
              {hasFieldPerm('name', 'r') && (
              <TableHead>{t('models.data_model.fields.name')}</TableHead>
              )}
              
              {hasFieldPerm('identifier', 'r') && (
              <TableHead>{t('models.data_model.fields.identifier')}</TableHead>
              )}
              
              {hasFieldPerm('version', 'r') && (
              <TableHead>{t('models.data_model.fields.version')}</TableHead>
              )}
              
              {hasFieldPerm('data_source_id', 'r') && (
              <TableHead>{t('models.data_model.fields.data_source_id')}</TableHead>
              )}
              
              <TableHead className="w-[100px]">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
                <TableRow>
                    <TableCell colSpan={ 7 } className="h-24 text-center">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                    </TableCell>
                </TableRow>
            ) : data.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={ 7 } className="h-24 text-center">
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
                    
                    {hasFieldPerm('name', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.name)}>
                        {String(item.name)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('identifier', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.identifier)}>
                        {String(item.identifier)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('version', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.version)}>
                        {String(item.version)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('data_source_id', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={item.data_source_id_label || (item.data_source_id ? `ID: ${item.data_source_id}` : '-')}>
                        {item.data_source_id_label || (item.data_source_id ? `ID: ${item.data_source_id}` : '-')}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    <TableCell className="flex items-center gap-2">
                        <>
                        
                        </>
                        {hasPermission('r') && (
                        <Button variant="ghost" size="icon" onClick={() => navigate(`/data_models/${item.id}`)}>
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
            {t('common.page_info')} {useDataModelStore(state => state.page)} {t('common.of_page')} {Math.ceil(useDataModelStore(state => state.total) / useDataModelStore(state => state.size)) || 1}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground whitespace-nowrap">{t('common.page_size', 'Page size')}:</span>
            <Select
              value={String(useDataModelStore.getState().size)}
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
            onClick={() => fetchData(1, useDataModelStore.getState().size)}
            disabled={useDataModelStore(state => state.page) <= 1 || loading}
          >
            {t('common.first')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(useDataModelStore.getState().page - 1, useDataModelStore.getState().size)}
            disabled={useDataModelStore(state => state.page) <= 1 || loading}
          >
            {t('common.previous')}
          </Button>
          <div className="flex items-center gap-1">
            <Input
              type="number"
              min={1}
              max={Math.ceil(useDataModelStore(state => state.total) / useDataModelStore(state => state.size)) || 1}
              className="w-16 h-8 text-center"
              value={gotoPageInput}
              onChange={(e) => setGotoPageInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const page = Number(gotoPageInput);
                  const totalPages = Math.ceil(useDataModelStore.getState().total / useDataModelStore.getState().size) || 1;
                  if (page >= 1 && page <= totalPages) {
                    fetchData(page, useDataModelStore.getState().size);
                  }
                }
              }}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(useDataModelStore.getState().page + 1, useDataModelStore.getState().size)}
            disabled={useDataModelStore(state => state.page) >= Math.ceil(useDataModelStore(state => state.total) / useDataModelStore(state => state.size)) || loading}
          >
            {t('common.next')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const totalPages = Math.ceil(useDataModelStore.getState().total / useDataModelStore.getState().size) || 1;
              fetchData(totalPages, useDataModelStore.getState().size);
            }}
            disabled={useDataModelStore(state => state.page) >= Math.ceil(useDataModelStore(state => state.total) / useDataModelStore(state => state.size)) || loading}
          >
            {t('common.last')}
          </Button>
        </div>
      </div>

      <Modal
        title={editingId ? `${t('common.edit')} DataModel` : `${t('common.create')} DataModel`}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      >
            <div className="max-h-[80vh] overflow-y-auto pr-2">
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          
          {(!editingId ? hasFieldPerm('id', 'c') : hasFieldPerm('id', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="id">{t('models.data_model.fields.id')}</Label>
            
            <Input
                id="id"
                
                type="number"
                
                {...register('id', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('name', 'c') : hasFieldPerm('name', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="name">{t('models.data_model.fields.name')}</Label>
            
            <Input
                id="name"
                
                type="text"
                
                {...register('name', { required: !editingId ? true : true })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('identifier', 'c') : hasFieldPerm('identifier', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="identifier">{t('models.data_model.fields.identifier')}</Label>
            
            <Input
                id="identifier"
                
                type="text"
                
                {...register('identifier', { required: !editingId ? true : true })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('version', 'c') : hasFieldPerm('version', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="version">{t('models.data_model.fields.version')}</Label>
            
            <Input
                id="version"
                
                type="text"
                
                {...register('version', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('data_source_id', 'c') : hasFieldPerm('data_source_id', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="data_source_id">{t('models.data_model.fields.data_source_id')}</Label>
            
            <Controller
                control={control}
                name="data_source_id"
                render={({ field: { onChange, value } }) => (
                    <SearchableSelect
                        value={value}
                        onValueChange={onChange}
                        placeholder={`${t('common.select')} ${t('models.data_model.fields.data_source_id')}`}
                        searchPlaceholder={`${t('common.search')} ${t('models.data_source.name')}...`}
                        valueLabels={ DataSourceIdValueLabels }
                        loadOptions={async (query) => {
                            const filters = query ? { name: query } : undefined;
                            const response = await getDataSources(1, 20, filters);
                            return response.items.map((item: any) => ({
                                label: item.name || item.id,
                                value: item.id
                            }));
                        }}
                    />
                )}
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

export default DataModelPage;