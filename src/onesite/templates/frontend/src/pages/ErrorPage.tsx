import { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';

type ErrorKind = '403' | '404' | '500' | 'offline';

export default function ErrorPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams();

  const kind = useMemo<ErrorKind>(() => {
    const raw = String(params.code || '').trim().toLowerCase();
    if (raw === '403' || raw === '404' || raw === '500' || raw === 'offline') return raw;
    return '500';
  }, [params.code]);

  const titleKey = `errors.${kind}.title`;
  const descKey = `errors.${kind}.desc`;
  const titleFallback =
    kind === '403'
      ? 'Access denied'
      : kind === '404'
        ? 'Page not found'
        : kind === 'offline'
          ? 'You are offline'
          : 'Something went wrong';
  const descFallback =
    kind === '403'
      ? "You don't have permission to view this page."
      : kind === '404'
        ? "The page you’re looking for doesn’t exist."
        : kind === 'offline'
          ? 'Network connection failed. Please check your connection and try again.'
          : 'Please try again or return to the home page.';

  const codeLabel = kind === 'offline' ? t('errors.offline.code', 'OFFLINE') : kind;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <div className="text-sm text-muted-foreground">{codeLabel}</div>
          <CardTitle className="text-2xl">{t(titleKey, titleFallback)}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-muted-foreground">{t(descKey, descFallback)}</div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" type="button" onClick={() => navigate(-1)}>
              {t('common.back', 'Back')}
            </Button>
            <Button type="button" onClick={() => navigate('/', { replace: true })}>
              {t('common.back_home', 'Back Home')}
            </Button>
            {kind === 'offline' || kind === '500' ? (
              <Button variant="secondary" type="button" onClick={() => window.location.reload()}>
                {t('common.retry', 'Retry')}
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

