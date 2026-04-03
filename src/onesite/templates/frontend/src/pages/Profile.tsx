import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ImageUpload } from '../components/ui/image-upload';
import { getMe, updateMe } from '../services/user';
import { toast } from 'sonner';

type Me = {
  id: number;
  email: string;
  full_name?: string | null;
  avatar?: string | null;
};

export default function ProfilePage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [me, setMe] = useState<Me | null>(null);

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
      const updated = await updateMe({
        full_name: me.full_name,
        avatar: me.avatar,
      });
      setMe(updated as any);
      localStorage.setItem('user_name', (updated as any).full_name || (updated as any).email || '');
      localStorage.setItem('user_avatar', (updated as any).avatar || '');
      window.dispatchEvent(new Event('onesite:user_updated'));
      toast.success(t('toast.update_success'));
    } catch (e) {
      console.error(e);
      toast.error(t('toast.save_failed'));
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
              <div className="space-y-2">
                <Label>{t('models.user.fields.email')}</Label>
                <Input value={me.email || ''} disabled />
              </div>
              <div className="space-y-2">
                <Label>{t('models.user.fields.full_name')}</Label>
                <Input
                  value={me.full_name || ''}
                  onChange={(e) => setMe((prev) => (prev ? { ...prev, full_name: e.target.value } : prev))}
                  placeholder={t('profile.full_name_placeholder')}
                />
              </div>
              <div className="space-y-2">
                <Label>{t('models.user.fields.avatar')}</Label>
                <ImageUpload value={me.avatar || ''} onChange={(v) => setMe((prev) => (prev ? { ...prev, avatar: v } : prev))} />
              </div>
            </>
          ) : (
            <div className="text-muted-foreground">{t('toast.save_failed')}</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

