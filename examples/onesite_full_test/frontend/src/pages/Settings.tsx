import React, { useEffect, useState } from 'react';
import { Loader2, Save, ChevronRight, ChevronDown } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { JsonInput } from '../components/ui/json-input';
import { JsonModelEditor, JsonModelArrayEditor } from '../components/ui/json-model-editor';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ImageUpload } from '../components/ui/image-upload';
import { FileUpload } from '../components/ui/file-upload';
import { TimePicker } from '../components/ui/time-picker';
import { applyTheme } from '../lib/theme';

import { useSystemConfigStore } from '../stores/useSystemConfigStore';


import { useCustomConfigStore } from '../stores/useCustomConfigStore';


const SettingsPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [isSavingSystem, setIsSavingSystem] = useState(false);
  const [isSavingCustom, setIsSavingCustom] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const { register, handleSubmit, reset, control } = useForm();

  // Role-based field permissions (Layer 2)
  const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
  
  const systemFieldRolePerms: Record<string, Record<string, string>> = {
  
  
    "id": {"admin": "r", "developer": "r", "user": "r"},
  
  
  
    "site_name": {"admin": "cru", "developer": "cru", "user": ""},
  
  
  
    "day_shift_start_at": {"admin": "cru", "developer": "cru", "user": ""},
  
  
  
    "day_shift_end_at": {"admin": "cru", "developer": "cru", "user": ""},
  
  
  
    "night_shift_start_at": {"admin": "cru", "developer": "cru", "user": ""},
  
  
  
    "night_shift_end_at": {"admin": "cru", "developer": "cru", "user": ""},
  
  
  
    "allow_registration": {"admin": "cru", "developer": "cru", "user": ""},
  
  
  };
  const canEditSystem = Object.values(systemFieldRolePerms).some(
    (fp) => (fp[userRole] || '').includes('u')
  );
  
  
  const customFieldRolePerms: Record<string, Record<string, string>> = {
  
  
    "language": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
  
  
  
    "timezone": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
  
  
  
    "theme": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
  
  
  };
  
  const hasFieldPerm = (fieldRolePerms: Record<string, Record<string, string>> | undefined, fieldName: string, perm: 'c' | 'r' | 'u') => {
    if (!fieldRolePerms) return true;
    const fp = fieldRolePerms[fieldName];
    if (!fp) return true;
    return (fp[userRole] || '').includes(perm);
  };

  
  const {
    data: systemData,
    localData: systemLocalData,
    loading: systemLoading,
    error: systemError,
    fetchData: fetchSystemData,
    updateData: updateSystemData,
  } = useSystemConfigStore();
  

  
  const {
    data: customData,
    localData: customLocalData,
    loading: customLoading,
    error: customError,
    fetchData: fetchCustomData,
    updateData: updateCustomData,
  } = useCustomConfigStore();
  

  useEffect(() => {
    fetchSystemData();
    fetchCustomData();
  }, [fetchSystemData, fetchCustomData]);

  useEffect(() => {
    if (systemLoading || customLoading) return;

    const combined: Record<string, any> = {
      ...(systemData || {}),
      ...(systemLocalData || {}),
      ...(customData || {}),
      ...(customLocalData || {}),
    };

    Object.keys(combined).forEach((k) => {
      if (combined[k] === null || combined[k] === undefined) delete combined[k];
    });

    reset(combined);
  }, [systemLoading, customLoading, systemData, systemLocalData, customData, customLocalData, reset]);

  const onSaveSystem = async (formData: any) => {
    try {
      setIsSavingSystem(true);
      await updateSystemData(formData);
      toast.success(t('toast.save_success', 'Saved'));
    } catch (e) {
      console.error(e);
      toast.error(t('toast.save_failed', 'Save failed'));
    } finally {
      setIsSavingSystem(false);
    }
  };

  const onSaveCustom = async (formData: any) => {
    try {
      setIsSavingCustom(true);

      let shouldReload = false;
      if (formData.language && formData.language !== i18n.language) {
        i18n.changeLanguage(formData.language);
        shouldReload = true;
      }
      if (formData.timezone && formData.timezone !== localStorage.getItem('timezone')) {
        localStorage.setItem('timezone', formData.timezone);
        shouldReload = true;
      }

      await updateCustomData(formData);
      if (formData.theme) {
        applyTheme(formData.theme);
      }

      if (shouldReload) {
        window.location.reload();
      }
      toast.success(t('toast.save_success', 'Saved'));
    } catch (e) {
      console.error(e);
      toast.error(t('toast.save_failed', 'Save failed'));
    } finally {
      setIsSavingCustom(false);
    }
  };

  const toggleGroup = (groupKey: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  };

  const showSystemSection = systemData !== null;

  
  
  
  

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('common.settings')}</h1>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-8">
        <form className="space-y-8" onSubmit={(e) => e.preventDefault()}>
          {showSystemSection ? (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">{t('settings.system_title')}</h2>
                <Button onClick={handleSubmit(onSaveSystem)} disabled={isSavingSystem || !canEditSystem} className="flex items-center space-x-2">
                  {isSavingSystem ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  <span>{t('settings.save_system')}</span>
                </Button>
              </div>

              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              
              <div className="border rounded-lg overflow-hidden">
                <button
                  type="button"
                  onClick={() => toggleGroup('default')}
                  className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <span className="font-medium">{t('settings.groups.default', 'default')}</span>
                  {expandedGroups.has('default') ? (
                    <ChevronDown className="w-5 h-5 text-gray-500" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-500" />
                  )}
                </button>
                {expandedGroups.has('default') && (
                  <div className="p-4 space-y-4">
                    
                    {hasFieldPerm(systemFieldRolePerms, 'site_name', 'r') && (
                    <div className="space-y-2">
                      <Label htmlFor="site_name">
                        {t('models.system_config.fields.site_name', 'Site Name')}
                      </Label>

                      
                      <Input
                        id="site_name"
                        type="text"
                        disabled={!hasFieldPerm(systemFieldRolePerms, 'site_name', 'u')}
                        {...register('site_name')}
                      />
                      
                    </div>
                    )}
                    
                    {hasFieldPerm(systemFieldRolePerms, 'day_shift_start_at', 'r') && (
                    <div className="space-y-2">
                      <Label htmlFor="day_shift_start_at">
                        {t('models.system_config.fields.day_shift_start_at', 'Day Shift Start At')}
                      </Label>

                      
                      <Controller
                        name="day_shift_start_at"
                        control={control}
                        render={({ field: { onChange, value } }) => (
                          <TimePicker
                            value={value}
                            onChange={onChange}
                            placeholder={t('common.select_time', 'Select time')}
                          />
                        )}
                      />
                      
                    </div>
                    )}
                    
                    {hasFieldPerm(systemFieldRolePerms, 'day_shift_end_at', 'r') && (
                    <div className="space-y-2">
                      <Label htmlFor="day_shift_end_at">
                        {t('models.system_config.fields.day_shift_end_at', 'Day Shift End At')}
                      </Label>

                      
                      <Controller
                        name="day_shift_end_at"
                        control={control}
                        render={({ field: { onChange, value } }) => (
                          <TimePicker
                            value={value}
                            onChange={onChange}
                            placeholder={t('common.select_time', 'Select time')}
                          />
                        )}
                      />
                      
                    </div>
                    )}
                    
                    {hasFieldPerm(systemFieldRolePerms, 'night_shift_start_at', 'r') && (
                    <div className="space-y-2">
                      <Label htmlFor="night_shift_start_at">
                        {t('models.system_config.fields.night_shift_start_at', 'Night Shift Start At')}
                      </Label>

                      
                      <Controller
                        name="night_shift_start_at"
                        control={control}
                        render={({ field: { onChange, value } }) => (
                          <TimePicker
                            value={value}
                            onChange={onChange}
                            placeholder={t('common.select_time', 'Select time')}
                          />
                        )}
                      />
                      
                    </div>
                    )}
                    
                    {hasFieldPerm(systemFieldRolePerms, 'night_shift_end_at', 'r') && (
                    <div className="space-y-2">
                      <Label htmlFor="night_shift_end_at">
                        {t('models.system_config.fields.night_shift_end_at', 'Night Shift End At')}
                      </Label>

                      
                      <Controller
                        name="night_shift_end_at"
                        control={control}
                        render={({ field: { onChange, value } }) => (
                          <TimePicker
                            value={value}
                            onChange={onChange}
                            placeholder={t('common.select_time', 'Select time')}
                          />
                        )}
                      />
                      
                    </div>
                    )}
                    
                    {hasFieldPerm(systemFieldRolePerms, 'allow_registration', 'r') && (
                    <div className="space-y-2">
                      <Label htmlFor="allow_registration">
                        {t('models.system_config.fields.allow_registration', 'Allow Registration')}
                      </Label>

                      
                      <div className="flex items-center space-x-2">
                        <Controller
                          name="allow_registration"
                          control={control}
                          render={({ field: { onChange, value } }) => (
                            <Switch checked={!!value} onCheckedChange={onChange} disabled={!hasFieldPerm(systemFieldRolePerms, 'allow_registration', 'u')} />
                          )}
                        />
                      </div>
                      
                    </div>
                    )}
                    
                  </div>
                )}
              </div>
              
              
              
            </div>
          ) : null}

          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">{t('settings.custom_title')}</h2>
              <Button onClick={handleSubmit(onSaveCustom)} disabled={isSavingCustom} className="flex items-center space-x-2">
                {isSavingCustom ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                <span>{t('settings.save_custom')}</span>
              </Button>
            </div>

            
            
            {hasFieldPerm(customFieldRolePerms, 'language', 'u') && (
            <div className="space-y-2">
              <Label htmlFor="language">
                {t('models.custom_config.fields.language', 'Language')}
                
                <span className="ml-2 text-xs text-gray-500 font-normal">({t('common.local_storage', 'Local Storage')})</span>
                
              </Label>

              
              <Controller
                name="language"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <Select value={value || ''} onValueChange={onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('common.select', 'Select...')} />
                    </SelectTrigger>
                    <SelectContent>
                      
                      <SelectItem value="en">en</SelectItem>
                      
                      <SelectItem value="zh">zh</SelectItem>
                      
                    </SelectContent>
                  </Select>
                )}
              />
              
            </div>
            )}
            
            
            {hasFieldPerm(customFieldRolePerms, 'timezone', 'u') && (
            <div className="space-y-2">
              <Label htmlFor="timezone">
                {t('models.custom_config.fields.timezone', 'Timezone')}
                
                <span className="ml-2 text-xs text-gray-500 font-normal">({t('common.local_storage', 'Local Storage')})</span>
                
              </Label>

              
              <Controller
                name="timezone"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <Select value={value || ''} onValueChange={onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('common.select', 'Select...')} />
                    </SelectTrigger>
                    <SelectContent>
                      
                      <SelectItem value="UTC">UTC</SelectItem>
                      
                      <SelectItem value="Asia/Shanghai">Asia/Shanghai</SelectItem>
                      
                    </SelectContent>
                  </Select>
                )}
              />
              
            </div>
            )}
            
            
            {hasFieldPerm(customFieldRolePerms, 'theme', 'u') && (
            <div className="space-y-2">
              <Label htmlFor="theme">
                {t('models.custom_config.fields.theme', 'Theme')}
                
                <span className="ml-2 text-xs text-gray-500 font-normal">({t('common.local_storage', 'Local Storage')})</span>
                
              </Label>

              
              <Controller
                name="theme"
                control={control}
                render={({ field: { onChange, value } }) => (
                  <Select value={value || ''} onValueChange={onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('common.select', 'Select...')} />
                    </SelectTrigger>
                    <SelectContent>
                      
                      <SelectItem value="system">system</SelectItem>
                      
                      <SelectItem value="light">light</SelectItem>
                      
                      <SelectItem value="dark">dark</SelectItem>
                      
                      <SelectItem value="iothub">iothub</SelectItem>
                      
                    </SelectContent>
                  </Select>
                )}
              />
              
            </div>
            )}
            
            
            
          </div>
        </form>
      </div>
    </div>
  );
};

export default SettingsPage;