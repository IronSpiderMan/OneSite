import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ImageUpload } from '../components/ui/image-upload';
import { FileUpload } from '../components/ui/file-upload';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { getMe, updateMe } from '../services/user';
import { toast } from 'sonner';

type Me = {
  id: number;

  
  email: string | null;
  

  
  full_name?: string | null;
  

  
  avatar?: string | null;
  

  
  is_active?: boolean | null;
  

  
  role?: string | null;
  

  

  

  
  created_at?: string | null;
  

  
  updated_at?: string | null;
  

  

};

export default function ProfilePage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [me, setMe] = useState<Me | null>(null);

  // Password change state
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Field-level role-based permissions (Layer 2)
  const userRole = (localStorage.getItem('user_role') || 'user') as 'user' | 'admin' | 'developer';
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
    if (!fp) return true;
    return (fp[userRole] || '').includes(perm);
  };

  const displayName = useMemo(() => {
    if (!me) return '';
    return (me.full_name || me.email || '').trim();
  }, [me]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const data = await getMe();
        if (!mounted) return;
        setMe(data as any);
      } catch (e) {
        console.error(e);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const handleSave = async () => {
    if (!me) return;
    try {
      setSaving(true);

      // Collect all updatable fields
      const updateData: Record<string, any> = {};

  

  
      updateData.full_name = me.full_name;
  

  
      updateData.avatar = me.avatar;
  

  

  

  

  

  

  

  


      // Handle password change
      if (newPassword) {
        if (newPassword !== confirmPassword) {
          toast.error(t('profile.password_mismatch'));
          setSaving(false);
          return;
        }
        updateData.old_password = oldPassword;
        updateData.password = newPassword;
      }

      const updated = await updateMe(updateData);
      setMe(updated as any);
      localStorage.setItem('user_name', (updated as any).full_name || (updated as any).email || '');
      localStorage.setItem('user_avatar', (updated as any).avatar || '');
      window.dispatchEvent(new Event('onesite:user_updated'));

      // Reset password fields on success
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');

      toast.success(t('toast.update_success'));
    } catch (e: any) {
      console.error(e);
      const detail = e?.response?.data?.detail;
      toast.error(detail || t('toast.save_failed'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-muted-foreground">{t('common.profile')}</div>
          <div className="text-2xl font-semibold">{displayName}</div>
        </div>
        <Button type="button" onClick={handleSave} disabled={loading || saving || !me}>
          {saving ? t('common.loading') : t('common.save')}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('profile.basic')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {loading ? (
            <div className="text-muted-foreground">{t('common.loading')}</div>
          ) : me ? (
            <>

  {hasFieldPerm('email', 'r') && (
              <div className="space-y-2">
                <Label>{t('models.user.fields.email')}</Label>
    
      
      
                <Input value={me.email || ''} disabled />
      
    
              </div>
  )}

  {hasFieldPerm('full_name', 'r') && (
              <div className="space-y-2">
                <Label>{t('models.user.fields.full_name')}</Label>
    {hasFieldPerm('full_name', 'u') ? (
      
                <Input
                  value={me.full_name || ''}
                  onChange={(e) => setMe((prev) => (prev ? { ...prev, full_name: e.target.value } : prev))}
        
                  placeholder={t('profile.full_name_placeholder')}
        
                />
      
    ) : (<>
      
      
                <Input value={me.full_name || ''} disabled />
      
    </>)}
              </div>
  )}

  {hasFieldPerm('avatar', 'r') && (
              <div className="space-y-2">
                <Label>{t('models.user.fields.avatar')}</Label>
    {hasFieldPerm('avatar', 'u') ? (
      
                <ImageUpload
                  value={me.avatar || ''}
                  onChange={(v) => setMe((prev) => (prev ? { ...prev, avatar: v } : prev))}
                />
      
    ) : (<>
      
      
                {me.avatar ? (
                  <div className="relative aspect-video w-full max-w-sm overflow-hidden rounded-lg border bg-muted">
                    <img src={me.avatar} alt="avatar" className="h-full w-full object-cover" />
                  </div>
                ) : (
                  <span className="text-muted-foreground italic">No image</span>
                )}
      
    </>)}
              </div>
  )}

  {hasFieldPerm('is_active', 'r') && (
              <div className="space-y-2">
                <Label>{t('models.user.fields.is_active')}</Label>
    
      
      
                <div className="font-medium">
                  {me.is_active ? 'Yes' : 'No'}
                </div>
      
    
              </div>
  )}

  {hasFieldPerm('role', 'r') && (
              <div className="space-y-2">
                <Label>{t('models.user.fields.role')}</Label>
    
      
      
                <div className="font-medium">{me.role || '-'}</div>
      
    
              </div>
  )}

  

  

  {hasFieldPerm('created_at', 'r') && (
              <div className="space-y-2">
                <Label>{t('models.user.fields.created_at')}</Label>
    
      
      
                <div className="text-muted-foreground">{me.created_at || '-'}</div>
      
    
              </div>
  )}

  {hasFieldPerm('updated_at', 'r') && (
              <div className="space-y-2">
                <Label>{t('models.user.fields.updated_at')}</Label>
    
      
      
                <div className="text-muted-foreground">{me.updated_at || '-'}</div>
      
    
              </div>
  )}

  

            </>
          ) : (
            <div className="text-muted-foreground">{t('toast.save_failed')}</div>
          )}
        </CardContent>
      </Card>



      <Card>
        <CardHeader>
          <CardTitle>{t('profile.change_password')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>{t('profile.old_password')}</Label>
            <Input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder={t('profile.old_password')}
            />
          </div>
          <div className="space-y-2">
            <Label>{t('profile.new_password')}</Label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={t('profile.new_password')}
            />
          </div>
          <div className="space-y-2">
            <Label>{t('profile.confirm_password')}</Label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t('profile.confirm_password')}
            />
          </div>
        </CardContent>
      </Card>

    </div>
  );
}