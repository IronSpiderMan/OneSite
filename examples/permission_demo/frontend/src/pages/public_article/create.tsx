import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Save } from 'lucide-react';
import { useForm, Controller } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { usePublicArticleStore } from '../../stores/usePublicArticleStore';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { JsonInput } from '../../components/ui/json-input';
import { JsonModelEditor, JsonModelArrayEditor } from '../../components/ui/json-model-editor';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { ImageUpload } from '../../components/ui/image-upload';
import { FileUpload } from '../../components/ui/file-upload';
import { SearchableSelect } from '../../components/ui/searchable-select';
import { LinkTableOrderedSelect } from '../../components/ui/link-table-ordered-select';
import { TimePicker } from '../../components/ui/time-picker';



const CreatePublicArticlePage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { createItem } = usePublicArticleStore();
  const [submitting, setSubmitting] = useState(false);

  // Role-based permissions
  const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
  const rolePermissions: Record<string, string> = {"admin": "rcud", "developer": "rcud", "user": "rcud"};
  const userPerms = rolePermissions[userRole] || '';

  // Field-level role-based permissions (Layer 2)
  const fieldRolePerms: Record<string, Record<string, string>> = {
  
  
    "id": {"admin": "r", "developer": "r", "user": "r"},
  
  
  
    "title": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
  
  
  
    "content": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
  
  
  
    "is_published": {"admin": "rcu", "developer": "rcu", "user": "rcu"},
  
  
  
    "created_at": {"admin": "r", "developer": "r", "user": "r"},
  
  
  };
  const hasFieldPerm = (fieldName: string, perm: 'c' | 'r' | 'u') => {
    const fp = fieldRolePerms[fieldName];
    if (!fp) return true;
    return (fp[userRole] || '').includes(perm);
  };

  
  
  
  
  
  
  
  
  
  
  
  

  const { register, handleSubmit, reset, setValue, control } = useForm();

  const onSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      await createItem(values);
      toast.success(t('toast.create_success', 'Created'));
      navigate('/public_articles');
    } catch (error) {
      toast.error(t('toast.save_failed', 'Save failed'));
      console.error(error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/public_articles')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-3xl font-bold tracking-tight">{t('common.create')} {t('models.public_article.name')}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('models.public_article.name')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            
            {hasFieldPerm('id', 'c') && (
            <div className="space-y-2">
              <Label htmlFor="id">{t('models.public_article.fields.id')}</Label>
              
              <Input
                id="id"
                
                type="number"
                
                {...register('id', { required: false })}
              />
              
            </div>
            )}
            
            {hasFieldPerm('title', 'c') && (
            <div className="space-y-2">
              <Label htmlFor="title">{t('models.public_article.fields.title')}</Label>
              
              <Input
                id="title"
                
                type="text"
                
                {...register('title', { required: true })}
              />
              
            </div>
            )}
            
            {hasFieldPerm('content', 'c') && (
            <div className="space-y-2">
              <Label htmlFor="content">{t('models.public_article.fields.content')}</Label>
              
              <Input
                id="content"
                
                type="text"
                
                {...register('content', { required: false })}
              />
              
            </div>
            )}
            
            {hasFieldPerm('is_published', 'c') && (
            <div className="space-y-2">
              <Label htmlFor="is_published">{t('models.public_article.fields.is_published')}</Label>
              
              <div className="flex items-center space-x-2">
                <Controller
                  control={control}
                  name="is_published"
                  defaultValue={ false }
                  render={({ field: { onChange, value } }) => (
                    <Switch checked={value} onCheckedChange={onChange} id="is_published" />
                  )}
                />
                <Label htmlFor="is_published" className="font-normal text-muted-foreground">
                  {t('models.public_article.fields.is_published')}
                </Label>
              </div>
              
            </div>
            )}
            
            {hasFieldPerm('created_at', 'c') && (
            <div className="space-y-2">
              <Label htmlFor="created_at">{t('models.public_article.fields.created_at')}</Label>
              
              <Input
                id="created_at"
                
                type="datetime-local"
                
                {...register('created_at', { required: false })}
              />
              
            </div>
            )}
            

            

            <div className="flex justify-end space-x-2 pt-4">
              <Button variant="outline" type="button" onClick={() => navigate('/public_articles')}>
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.saving', 'Saving...')}</>
                ) : (
                  <><Save className="mr-2 h-4 w-4" /> {t('common.save')}</>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default CreatePublicArticlePage;