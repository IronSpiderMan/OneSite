import React, { useState, useEffect, useRef } from 'react';
import { Plus, Pencil, Trash2, Loader2, Eye, Upload, Download, Trash } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { 
    Product, getProductTags, getProductTagsWithMeta
    
    
    , importProducts
    
    
    , exportProducts
    
    
} from '../../services/product';

import { useProductStore } from '../../stores/useProductStore';
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

import { getCategorys, getCategory } from '../../services/category';



import { getTags } from '../../services/tag';



const ProductPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data, loading, fetchData, refreshData, fetchItem, createItem, updateItem, deleteItem, bulkDeleteItem } = useProductStore();
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
  
  
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importingFile, setImportingFile] = useState<File | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  

  // Role-based permissions
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
    if (!fp) return true; // no restrictions = allowed
    return (fp[userRole] || '').includes(perm);
  };

  

  // User model special handling: user role can only access /me
  

  
  
  
  
  
  
  
  
  
  
  const [CategoryIdValueLabels, setCategoryIdValueLabels] = useState<Record<string, string>>({});
  const [searchCategoryIdLabels, setSearchCategoryIdLabels] = useState<Record<string, string>>({});
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  const [TagIdsValueLabels, setTagIdsValueLabels] = useState<Record<string, string>>({});
  
  

  const { register, handleSubmit, reset, setValue, control } = useForm();

  

  useEffect(() => {
    
    fetchData();
    
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync page input with current page from store
  const storePage = useProductStore(state => state.page);
  useEffect(() => {
    setGotoPageInput(String(storePage));
  }, [storePage]);

  const handleCreate = () => {
    
    setEditingId(null);
    reset();
    
    
    
    
    
    
    
    
    
    
    setCategoryIdValueLabels({});
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    setValue('tag_ids', []);
    setTagIdsValueLabels({});
    
    
    setIsModalOpen(true);
    
  };

  

  
  const handleExport = async () => {
    try {
      await exportProducts();
      toast.success(t('export.success', 'Export completed'));
    } catch (error) {
      toast.error(t('export.failed', 'Export failed'));
    }
  };
  

  
  const handleImportClick = () => {
    setImportingFile(null);
    setImportModalOpen(true);
  };

  const handleImportSubmit = async () => {
    if (!importingFile) {
      toast.error(t('import.no_file', 'Please select a file'));
      return;
    }

    try {
      setIsImporting(true);
      const result = await importProducts(importingFile);
      if (result.failed > 0) {
        toast.warning(t('import.partial', `Imported ${result.success} records, ${result.failed} failed`));
      } else {
        toast.success(t('import.success', `Successfully imported ${result.success} records`));
      }
      // Refresh data after import
      fetchData();
      setImportModalOpen(false);
      setImportingFile(null);
    } catch (error) {
      toast.error(t('import.failed', 'Import failed'));
    } finally {
      setIsImporting(false);
    }
  };
  

  

  const handleEdit = async (record: Product) => {
    
    setEditingId(record.id);
    const full = await fetchItem(record.id);
    const item = full || record;
    // Set form values
    
    
    setValue('id', item.id);
    
    
    
    setValue('name', item.name);
    
    
    
    setValue('status', item.status);
    
    
    
    setValue('is_featured', item.is_featured);
    
    
    
    setValue('category_id', item.category_id);
    
    
    
    setValue('variants', item.variants);
    
    
    
    setValue('meta_data', item.meta_data);
    
    
    
    setValue('created_at', item.created_at);
    
    
    
    setValue('cover_image', item.cover_image);
    
    
    
    setValue('manual_file', item.manual_file);
    
    
    
    
    
    setValue('internal_note', item.internal_note);
    
    
    
    
    
    
    
    
    
    
    
    
    try {
      if (item.category_id) {
        const fkItem = await getCategory(item.category_id);
        if (fkItem) {
          setCategoryIdValueLabels({ [String(fkItem.id)]: fkItem.name || String(fkItem.id) });
        } else {
          setCategoryIdValueLabels({});
        }
      } else {
        setCategoryIdValueLabels({});
      }
    } catch (error) {
      console.error(error);
      setCategoryIdValueLabels({});
    }
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    try {
      
      const rel = await getProductTagsWithMeta(record.id, 1, 200);
      const ordered = [...rel.items].sort((a: any, b: any) => (a.order ?? 0) - (b.order ?? 0));
      setValue('tag_ids', ordered.map((x: any) => x.id));
      setTagIdsValueLabels(Object.fromEntries(ordered.map((x: any) => [String(x.id), x.label || String(x.id)])));
      
    } catch (error) {
      console.error(error);
      setTagIdsValueLabels({});
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
    
    
    
    
    
    if (searchValues['status'] && searchValues['status'] !== '__all__') next['status'] = searchValues['status'];
    
    
    
    
    
    if (searchValues['is_featured'] === 'true') next['is_featured'] = true;
    if (searchValues['is_featured'] === 'false') next['is_featured'] = false;
    
    
    
    
    
    
    
    
    
    
    
    if (searchValues['created_at_from']) next['created_at_from'] = `${searchValues['created_at_from']}T00:00:00`;
    if (searchValues['created_at_to']) next['created_at_to'] = `${searchValues['created_at_to']}T23:59:59`;
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    fetchData(1, useProductStore.getState().size, next);
    
  };

  const resetSearch = () => {
    setSearchValues({});
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    fetchData(1, useProductStore.getState().size, {});
    
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
        <h1 className="text-3xl font-bold tracking-tight">{t('models.product.name')}s</h1>
        <div className="flex items-center gap-4">
          
          
          <div className="flex items-center gap-2">
            
            <Button variant="outline" onClick={handleImportClick}>
              <Upload className="mr-2 h-4 w-4" /> {t('common.import', 'Import')}
            </Button>
            
            
            <Button variant="outline" onClick={handleExport}>
              <Download className="mr-2 h-4 w-4" />
              {t('common.export', 'Export')}
            </Button>
            
            
          </div>
          
          {selectedIds.length > 0 && hasPermission('d') && (
            <Button variant="destructive" onClick={() => setBulkDeleteOpen(true)}>
              <Trash className="mr-2 h-4 w-4" /> {t('common.bulk_delete', 'Delete')} ({selectedIds.length})
            </Button>
          )}
          {hasPermission('c') && (
            <Button onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" /> {t('common.create')} {t('models.product.name')}
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
            <Label>{t('models.product.fields.name')}</Label>
            
            <Input
              className="h-9"
              value={searchValues['name'] || ''}
              onChange={(e) => setSearchValues((s) => ({ ...s, ['name']: e.target.value }))}
              placeholder={t('common.search')}
            />
            
          </div>
          
          
              
          <div className="space-y-2">
            <Label>{t('models.product.fields.status')}</Label>
            
            <Select
              value={searchValues['status'] || '__all__'}
              onValueChange={(v) => setSearchValues((s) => ({ ...s, ['status']: v }))}
            >
              <SelectTrigger className="h-9">
                <SelectValue placeholder={t('common.all', 'All')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">{t('common.all', 'All')}</SelectItem>
                
                <SelectItem value="draft">draft</SelectItem>
                
                <SelectItem value="active">active</SelectItem>
                
                <SelectItem value="archived">archived</SelectItem>
                
              </SelectContent>
            </Select>
            
          </div>
          
          
              
          <div className="space-y-2">
            <Label>{t('models.product.fields.is_featured')}</Label>
            
            <Select
              value={searchValues['is_featured'] || '__all__'}
              onValueChange={(v) => setSearchValues((s) => ({ ...s, ['is_featured']: v }))}
            >
              <SelectTrigger className="h-9">
                <SelectValue placeholder={t('common.all', 'All')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">{t('common.all', 'All')}</SelectItem>
                <SelectItem value="true">{t('common.yes', 'Yes')}</SelectItem>
                <SelectItem value="false">{t('common.no', 'No')}</SelectItem>
              </SelectContent>
            </Select>
            
          </div>
          
          
              
          
              
          
              
          
              
          <div className="space-y-2">
            <Label>{t('models.product.fields.created_at')}</Label>
            
            <div className="flex items-center gap-2">
              <Input
                type="date"
                className="h-9"
                value={searchValues['created_at_from'] || ''}
                onChange={(e) => setSearchValues((s) => ({ ...s, ['created_at_from']: e.target.value }))}
              />
              <span className="text-muted-foreground text-sm">-</span>
              <Input
                type="date"
                className="h-9"
                value={searchValues['created_at_to'] || ''}
                onChange={(e) => setSearchValues((s) => ({ ...s, ['created_at_to']: e.target.value }))}
              />
            </div>
            
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
              <TableHead>{t('models.product.fields.id')}</TableHead>
              )}
              
              {hasFieldPerm('name', 'r') && (
              <TableHead>{t('models.product.fields.name')}</TableHead>
              )}
              
              {hasFieldPerm('status', 'r') && (
              <TableHead>{t('models.product.fields.status')}</TableHead>
              )}
              
              {hasFieldPerm('is_featured', 'r') && (
              <TableHead>{t('models.product.fields.is_featured')}</TableHead>
              )}
              
              {hasFieldPerm('category_id', 'r') && (
              <TableHead>{t('models.product.fields.category_id')}</TableHead>
              )}
              
              {hasFieldPerm('variants', 'r') && (
              <TableHead>{t('models.product.fields.variants')}</TableHead>
              )}
              
              {hasFieldPerm('meta_data', 'r') && (
              <TableHead>{t('models.product.fields.meta_data')}</TableHead>
              )}
              
              {hasFieldPerm('created_at', 'r') && (
              <TableHead>{t('models.product.fields.created_at')}</TableHead>
              )}
              
              {hasFieldPerm('cover_image', 'r') && (
              <TableHead>{t('models.product.fields.cover_image')}</TableHead>
              )}
              
              {hasFieldPerm('manual_file', 'r') && (
              <TableHead>{t('models.product.fields.manual_file')}</TableHead>
              )}
              
              
              
              {hasFieldPerm('internal_note', 'r') && (
              <TableHead>{t('models.product.fields.internal_note')}</TableHead>
              )}
              
              <TableHead className="w-[100px]">{t('common.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
                <TableRow>
                    <TableCell colSpan={ 14 } className="h-24 text-center">
                        <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                    </TableCell>
                </TableRow>
            ) : data.length === 0 ? (
                <TableRow>
                    <TableCell colSpan={ 14 } className="h-24 text-center">
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
                    
                    {hasFieldPerm('status', 'r') && (
                    <TableCell>
                        
                        <Badge variant="outline">{item.status}</Badge>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('is_featured', 'r') && (
                    <TableCell>
                        
                        <Badge variant={item.is_featured ? "default" : "secondary"}>
                            {item.is_featured ? 'Yes' : 'No'}
                        </Badge>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('category_id', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={item.category_id_label || (item.category_id ? `ID: ${item.category_id}` : '-')}>
                        {item.category_id_label || (item.category_id ? `ID: ${item.category_id}` : '-')}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('variants', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={item.variants !== undefined && item.variants !== null ? (typeof item.variants === 'object' ? JSON.stringify(item.variants) : String(item.variants)) : '-'}>
                        {item.variants !== undefined && item.variants !== null
                          ? (typeof item.variants === 'object' ? JSON.stringify(item.variants) : String(item.variants))
                          : '-'}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('meta_data', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={item.meta_data !== undefined && item.meta_data !== null ? (typeof item.meta_data === 'object' ? JSON.stringify(item.meta_data) : String(item.meta_data)) : '-'}>
                        {item.meta_data !== undefined && item.meta_data !== null
                          ? (typeof item.meta_data === 'object' ? JSON.stringify(item.meta_data) : String(item.meta_data))
                          : '-'}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('created_at', 'r') && (
                    <TableCell>
                        
                        <span className="text-muted-foreground">{formatDateTime(item.created_at, timeZone)}</span>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('cover_image', 'r') && (
                    <TableCell>
                        
                        <div className="h-10 w-10 overflow-hidden rounded-md border bg-muted">
                            <img
                                src={item.cover_image || 'https://placehold.co/100?text=No+Image'}
                                alt="cover_image"
                                className="h-full w-full object-cover"
                                onError={(e) => {
                                    (e.target as HTMLImageElement).src = 'https://placehold.co/100?text=Error';
                                }}
                            />
                        </div>
                        
                    </TableCell>
                    )}
                    
                    {hasFieldPerm('manual_file', 'r') && (
                    <TableCell>
                        
                        {item.manual_file ? (
                            <div className="flex items-center gap-2">
                                <span
                                    className="flex items-center text-primary cursor-pointer hover:underline"
                                    title={item.manual_file}
                                    onClick={() => {
                                        // TODO: Open preview
                                    }}
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                                    File
                                </span>
                                
                            </div>
                        ) : (
                            <span className="text-muted-foreground">-</span>
                        )}
                        
                    </TableCell>
                    )}
                    
                    
                    
                    {hasFieldPerm('internal_note', 'r') && (
                    <TableCell>
                        
                        <span className="block max-w-[250px] truncate" title={String(item.internal_note)}>
                        {String(item.internal_note)}
                        </span>
                        
                    </TableCell>
                    )}
                    
                    <TableCell className="flex items-center gap-2">
                        <>
                        
                        </>
                        {hasPermission('r') && (
                        <Button variant="ghost" size="icon" onClick={() => navigate(`/products/${item.id}`)}>
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
            {t('common.page_info')} {useProductStore(state => state.page)} {t('common.of_page')} {Math.ceil(useProductStore(state => state.total) / useProductStore(state => state.size)) || 1}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground whitespace-nowrap">{t('common.page_size', 'Page size')}:</span>
            <Select
              value={String(useProductStore.getState().size)}
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
            onClick={() => fetchData(1, useProductStore.getState().size)}
            disabled={useProductStore(state => state.page) <= 1 || loading}
          >
            {t('common.first')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(useProductStore.getState().page - 1, useProductStore.getState().size)}
            disabled={useProductStore(state => state.page) <= 1 || loading}
          >
            {t('common.previous')}
          </Button>
          <div className="flex items-center gap-1">
            <Input
              type="number"
              min={1}
              max={Math.ceil(useProductStore(state => state.total) / useProductStore(state => state.size)) || 1}
              className="w-16 h-8 text-center"
              value={gotoPageInput}
              onChange={(e) => setGotoPageInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const page = Number(gotoPageInput);
                  const totalPages = Math.ceil(useProductStore.getState().total / useProductStore.getState().size) || 1;
                  if (page >= 1 && page <= totalPages) {
                    fetchData(page, useProductStore.getState().size);
                  }
                }
              }}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchData(useProductStore.getState().page + 1, useProductStore.getState().size)}
            disabled={useProductStore(state => state.page) >= Math.ceil(useProductStore(state => state.total) / useProductStore(state => state.size)) || loading}
          >
            {t('common.next')}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const totalPages = Math.ceil(useProductStore.getState().total / useProductStore.getState().size) || 1;
              fetchData(totalPages, useProductStore.getState().size);
            }}
            disabled={useProductStore(state => state.page) >= Math.ceil(useProductStore(state => state.total) / useProductStore(state => state.size)) || loading}
          >
            {t('common.last')}
          </Button>
        </div>
      </div>



      <Modal
        title={editingId ? `${t('common.edit')} Product` : `${t('common.create')} Product`}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      >
            <div className="max-h-[80vh] overflow-y-auto pr-2">
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          
          {(!editingId ? hasFieldPerm('id', 'c') : hasFieldPerm('id', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="id">{t('models.product.fields.id')}</Label>
            
            <Input
                id="id"
                
                type="number"
                
                {...register('id', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('name', 'c') : hasFieldPerm('name', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="name">{t('models.product.fields.name')}</Label>
            
            <Input
                id="name"
                
                type="text"
                
                {...register('name', { required: !editingId ? true : true })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('status', 'c') : hasFieldPerm('status', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="status">{t('models.product.fields.status')}</Label>
            
            <Controller
                control={control}
                name="status"
                render={({ field: { onChange, value } }) => {
                    // Filter enum values based on role for User.role field
                    
                    const filteredValues = ["draft", "active", "archived"];
                    
                    return (
                    <Select onValueChange={onChange} defaultValue={value}>
                        <SelectTrigger>
                            <SelectValue placeholder={`${t('common.select')} ${t('models.product.fields.status')}`} />
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
          
          {(!editingId ? hasFieldPerm('is_featured', 'c') : hasFieldPerm('is_featured', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="is_featured">{t('models.product.fields.is_featured')}</Label>
            
            <div className="flex items-center space-x-2">
                <Controller
                    control={control}
                    name="is_featured"
                    defaultValue={ false }
                    render={({ field: { onChange, value } }) => (
                        <Switch checked={value} onCheckedChange={onChange} id="is_featured" />
                    )}
                />
                <Label htmlFor="is_featured" className="font-normal text-muted-foreground">
                    {t('models.product.fields.is_featured')}
                </Label>
            </div>
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('category_id', 'c') : hasFieldPerm('category_id', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="category_id">{t('models.product.fields.category_id')}</Label>
            
            <Controller
                control={control}
                name="category_id"
                render={({ field: { onChange, value } }) => (
                    <SearchableSelect
                        value={value}
                        onValueChange={onChange}
                        placeholder={`${t('common.select')} ${t('models.product.fields.category_id')}`}
                        searchPlaceholder={`${t('common.search')} ${t('models.category.name')}...`}
                        valueLabels={ CategoryIdValueLabels }
                        loadOptions={async (query) => {
                            const filters = query ? { name: query } : undefined;
                            const response = await getCategorys(1, 20, filters);
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
          
          {(!editingId ? hasFieldPerm('variants', 'c') : hasFieldPerm('variants', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="variants">{t('models.product.fields.variants')}</Label>
            
            <Controller
                control={control}
                name="variants"
                defaultValue={ [] }
                render={({ field: { onChange, value } }) => (
                    
                    <JsonModelArrayEditor
                        itemSchema={ {"fields": [{"kind": "str", "name": "sku"}, {"kind": "float", "name": "price"}, {"kind": "int", "name": "stock"}], "name": "ProductVariant"} }
                        value={value}
                        onChange={onChange}
                    />
                    
                )}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('meta_data', 'c') : hasFieldPerm('meta_data', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="meta_data">{t('models.product.fields.meta_data')}</Label>
            
            <Controller
                control={control}
                name="meta_data"
                defaultValue={ {} }
                render={({ field: { onChange, value } }) => (
                    
                    <JsonInput
                        value={value}
                        onChange={onChange}
                        jsonKind="object"
                        placeholder={ "{\\n  \\n}" }
                    />
                    
                )}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('created_at', 'c') : hasFieldPerm('created_at', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="created_at">{t('models.product.fields.created_at')}</Label>
            
            <Input
                id="created_at"
                
                type="datetime-local"
                
                {...register('created_at', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('cover_image', 'c') : hasFieldPerm('cover_image', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="cover_image">{t('models.product.fields.cover_image')}</Label>
            
            <Controller
                control={control}
                name="cover_image"
                render={({ field: { onChange, value } }) => (
                    <ImageUpload
                        value={value}
                        onChange={onChange}
                    />
                )}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('manual_file', 'c') : hasFieldPerm('manual_file', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="manual_file">{t('models.product.fields.manual_file')}</Label>
            
                        <Controller
                            control={control}
                            name="manual_file"
                            render={({ field: { onChange, value } }) => (
                                <FileUpload
                                    value={value}
                                    onChange={onChange}
                                    allowDownload={ false }
                                />
                            )}
                        />
                        
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('import_source', 'c') : hasFieldPerm('import_source', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="import_source">{t('models.product.fields.import_source')}</Label>
            
            <Input
                id="import_source"
                
                type="text"
                
                {...register('import_source', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          
          {(!editingId ? hasFieldPerm('internal_note', 'c') : hasFieldPerm('internal_note', 'u')) && (
          <div className="space-y-2">
            <Label htmlFor="internal_note">{t('models.product.fields.internal_note')}</Label>
            
            <Input
                id="internal_note"
                
                type="text"
                
                {...register('internal_note', { required: !editingId ? false : false })}
            />
            
          </div>
          )}
          

          
          
          <div className="space-y-2">
            <Label>{t('models.tag.name')}s</Label>
            <Controller
                control={control}
                name="tag_ids"
                render={({ field: { onChange, value } }) => (
                    
                    <LinkTableOrderedSelect
                        value={value}
                        onValueChange={onChange}
                        placeholder={`${t('common.select')} ${t('models.tag.name')}s`}
                        searchPlaceholder={`${t('common.search')} ${t('models.tag.name')}...`}
                        valueLabels={ TagIdsValueLabels }
                        loadOptions={async (query) => {
                            const filters = query ? { name: query } : undefined;
                            const response = await getTags(1, 20, filters);
                            return response.items.map((item: any) => ({
                                label: item.name || item.id,
                                value: item.id
                            }));
                        }}
                    />
                    
                )}
            />
          </div>
          
          
          <div className="flex justify-end space-x-2 pt-4">
            <Button variant="outline" type="button" onClick={() => setIsModalOpen(false)}>{t('common.cancel')}</Button>
            <Button type="submit">{t('common.save')}</Button>
          </div>
        </form>
            </div>
      </Modal>
      

      
      {/* Import Modal */}
      <Modal
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        title={t('common.import', 'Import')}
      >
        <div className="space-y-4">
          <div className="flex flex-col gap-2">
            <Label>{t('import.file', 'CSV File')}</Label>
            <FileInput
              accept=".csv"
              value={importingFile}
              onChange={setImportingFile}
            />
          </div>
          <div className="flex justify-end space-x-2 pt-4">
            <Button variant="outline" onClick={() => setImportModalOpen(false)}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button onClick={handleImportSubmit} disabled={!importingFile || isImporting}>
              {isImporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common.importing', 'Importing...')}
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  {t('common.import', 'Import')}
                </>
              )}
            </Button>
          </div>
        </div>
      </Modal>
      
    </div>
  );
};

export default ProductPage;