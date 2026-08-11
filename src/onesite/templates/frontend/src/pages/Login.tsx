import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { request } from '../utils/request';
import { Loader2 } from 'lucide-react';

export default function LoginPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();

  const fallbackProjectName = (window as any).__ENV__?.PROJECT_NAME
    || import.meta.env.VITE_PROJECT_NAME
    || 'OneSite';
  const [projectName, setProjectName] = useState(
    () => localStorage.getItem('onesite_site_name') || fallbackProjectName
  );
  const fallbackLogo = (window as any).__ENV__?.PROJECT_LOGO
    || import.meta.env.VITE_PROJECT_LOGO
    || '';
  const [logoUrl, setLogoUrl] = useState(
    () => localStorage.getItem('onesite_site_logo') || fallbackLogo
  );
  const [registrationAllowed, setRegistrationAllowed] = useState(
    () => localStorage.getItem('onesite_allow_registration') === 'true'
  );

  useEffect(() => {
    const syncSiteName = (event?: Event) => {
      const updatedName = (event as CustomEvent<string> | undefined)?.detail;
      setProjectName(
        updatedName || localStorage.getItem('onesite_site_name') || fallbackProjectName
      );
    };
    window.addEventListener('onesite:site_name_updated', syncSiteName);
    window.addEventListener('storage', syncSiteName);
    return () => {
      window.removeEventListener('onesite:site_name_updated', syncSiteName);
      window.removeEventListener('storage', syncSiteName);
    };
  }, [fallbackProjectName]);

  useEffect(() => {
    const syncLogo = (event?: Event) => {
      const updatedLogo = (event as CustomEvent<string> | undefined)?.detail;
      setLogoUrl(updatedLogo || localStorage.getItem('onesite_site_logo') || fallbackLogo);
    };
    const syncRegistration = (event?: Event) => {
      const detail = (event as CustomEvent<boolean> | undefined)?.detail;
      setRegistrationAllowed(
        typeof detail === 'boolean'
          ? detail
          : localStorage.getItem('onesite_allow_registration') === 'true'
      );
    };
    window.addEventListener('onesite:site_logo_updated', syncLogo);
    window.addEventListener('onesite:registration_updated', syncRegistration);
    window.addEventListener('storage', syncLogo);
    window.addEventListener('storage', syncRegistration);
    return () => {
      window.removeEventListener('onesite:site_logo_updated', syncLogo);
      window.removeEventListener('onesite:registration_updated', syncRegistration);
      window.removeEventListener('storage', syncLogo);
      window.removeEventListener('storage', syncRegistration);
    };
  }, [fallbackLogo]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await request.post('/login/access-token', formData, {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      window.dispatchEvent(new Event('onesite:auth_updated'));

      // Fetch user info to get role
      try {
        const userResponse = await request.get('/users/me');
        const user = userResponse.data;
        localStorage.setItem('user_name', user.full_name || user.email);
        if (user.avatar) {
          localStorage.setItem('user_avatar', user.avatar);
        }
        localStorage.setItem('user_role', user.role || 'user');
      } catch (err) {
        console.error('Failed to fetch user info:', err);
        localStorage.setItem('user_role', 'user');
      }

      navigate('/');
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || t('login.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative grid h-[100dvh] w-full overflow-hidden bg-background lg:grid-cols-[minmax(360px,0.9fr)_minmax(520px,1.1fr)]">
      <section className="relative hidden h-full overflow-hidden bg-zinc-950 p-10 text-white lg:flex lg:flex-col xl:p-14">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_15%,rgba(255,255,255,0.12),transparent_28%),radial-gradient(circle_at_80%_80%,rgba(99,102,241,0.25),transparent_35%)]" />
        <div className="absolute inset-0 opacity-[0.08] [background-image:linear-gradient(rgba(255,255,255,.5)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.5)_1px,transparent_1px)] [background-size:36px_36px]" />

        <div className="relative z-10 flex items-center text-lg font-semibold tracking-tight">
          <div className="mr-3 flex h-9 w-9 items-center justify-center overflow-hidden rounded-xl bg-white font-bold text-zinc-950 shadow-lg shadow-black/20">
            {logoUrl ? (
              <img src={logoUrl} alt={projectName} className="h-9 w-9 object-contain" />
            ) : (
              projectName.charAt(0).toUpperCase()
            )}
          </div>
          {projectName}
        </div>

        <div className="relative z-10 my-auto max-w-lg space-y-5">
          <div className="h-1 w-12 rounded-full bg-white/80" />
          <h2 className="text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
            {t('login.title')}
          </h2>
          <p className="max-w-md text-base leading-7 text-zinc-300">
            {t('login.description')}
          </p>
        </div>

        <div className="relative z-10 flex items-center gap-3 text-xs font-medium uppercase tracking-[0.2em] text-zinc-500">
          <span className="h-px w-8 bg-zinc-700" />
          {t('login.system_access')}
        </div>
      </section>

      <main className="relative flex h-full min-h-0 items-center justify-center overflow-hidden bg-muted/20 px-5 py-5 sm:px-8 lg:px-12">
        {registrationAllowed && (
          <div className="absolute right-6 top-6 hidden items-center gap-2 text-sm text-muted-foreground sm:flex">
            <span>{t('login.no_account')}</span>
            <Button type="button" variant="outline" size="sm" onClick={() => navigate('/register')}>
              {t('login.register')}
            </Button>
          </div>
        )}

        <div className="max-h-[calc(100dvh-2.5rem)] w-full max-w-[410px] overflow-y-auto overscroll-contain rounded-2xl border bg-card p-6 shadow-[0_24px_80px_-36px_rgba(0,0,0,0.35)] sm:p-8">
          <div className="mb-7 flex items-center justify-center gap-3 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-xl bg-primary text-sm font-bold text-primary-foreground">
              {logoUrl ? (
                <img src={logoUrl} alt={projectName} className="h-9 w-9 object-contain" />
              ) : (
                projectName.charAt(0).toUpperCase()
              )}
            </div>
            <span className="max-w-[240px] truncate text-lg font-semibold">{projectName}</span>
          </div>

          <div className="space-y-6">
            <div className="flex flex-col space-y-2 text-center">
              <h1 className="text-3xl font-semibold tracking-tight">{t('login.title')}</h1>
              <p className="text-sm text-muted-foreground">{t('login.description')}</p>
            </div>

            <form onSubmit={handleLogin} className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="email">{t('login.email')}</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder={t('login.emailPlaceholder')}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  autoCapitalize="none"
                  autoComplete="email"
                  autoCorrect="off"
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="password">{t('login.password')}</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  autoComplete="current-password"
                  required
                />
              </div>

              {error && (
                <div className="text-sm font-medium text-destructive">{error}</div>
              )}
              {(location.state as any)?.registrationSuccess && (
                <div className="text-sm font-medium text-green-600">{t('register.success')}</div>
              )}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {loading ? t('login.signingIn') : t('login.signIn')}
              </Button>

              {registrationAllowed && (
                <div className="text-center text-sm text-muted-foreground sm:hidden">
                  {t('login.no_account')}{' '}
                  <Link to="/register" className="font-medium text-primary hover:underline">
                    {t('login.register')}
                  </Link>
                </div>
              )}
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
