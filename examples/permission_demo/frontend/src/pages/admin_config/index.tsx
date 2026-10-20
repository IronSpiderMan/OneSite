import React, { useEffect, useState } from 'react';
import { Loader2, Save } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useAdminConfigStore } from '../../stores/useAdminConfigStore';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { JsonInput } from '../../components/ui/json-input';
import { JsonModelEditor, JsonModelArrayEditor } from '../../components/ui/json-model-editor';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { ImageUpload } from '../../components/ui/image-upload';
import { FileUpload } from '../../components/ui/file-upload';
import { TimePicker } from '../../components/ui/time-picker';

const AdminConfigPage: React.FC = () => {
  const { t } = useTranslation();
  const { data, localData, loading, fetchData, updateData } = useAdminConfigStore();
  const [isSaving, setIsSaving] = useState(false);
  const { register, handleSubmit, reset, control } = useForm();

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (loading) return;
    const combined: Record<string, any> = { ...(data || {}), ...(localData || {}) };
    Object.keys(combined).forEach((k) => {
      if (combined[k] === null || combined[k] === undefined) delete combined[k];
    });
    reset(combined);
  }, [data, localData, loading, reset]);

  const onSubmit = async (formData: any) => {
    try {
      setIsSaving(true);
      await updateData(formData);
    } catch (error) {
      console.error('Failed to save:', error);
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t('menu.admin_config', 'AdminConfig')}
        </h1>
        <Button onClick={handleSubmit(onSubmit)} disabled={isSaving} className="flex items-center space-x-2">
          {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          <span>{t('common.save', 'Save')}</span>
        </Button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-6">
        <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
          
          
          
          
          <div className="space-y-2">
            <Label htmlFor="site_name">
              {t('models.admin_config.fields.site_name', 'Site Name')}
              
            </Label>

            
            <Input
              id="site_name"
              type="text"
              {...register('site_name')}
            />
            
          </div>
          
          
          
          <div className="space-y-2">
            <Label htmlFor="max_upload_size">
              {t('models.admin_config.fields.max_upload_size', 'Max Upload Size')}
              
            </Label>

            
            <Input
              id="max_upload_size"
              type="number"
              {...register('max_upload_size', { valueAsNumber: true })}
            />
            
          </div>
          
          
          
          <div className="space-y-2">
            <Label htmlFor="enable_registration">
              {t('models.admin_config.fields.enable_registration', 'Enable Registration')}
              
            </Label>

            
            <div className="flex items-center space-x-2">
              <Controller
                name="enable_registration"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <Switch checked={!!value} onCheckedChange={onChange} />
                )}
              />
            </div>

            
          </div>
          
          
        </form>
      </div>
    </div>
  );
};

export default AdminConfigPage;