import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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

  const fallbackProjectName = (window as any).__ENV__?.PROJECT_NAME
    || import.meta.env.VITE_PROJECT_NAME
    || 'OneSite';
  const [projectName, setProjectName] = useState(
    () => localStorage.getItem('onesite_site_name') || fallbackProjectName
  );
  const logoUrl = (window as any).__ENV__?.PROJECT_LOGO
    || import.meta.env.VITE_PROJECT_LOGO;

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
    <div className="login-shell container relative min-h-screen flex-col items-center justify-center grid lg:max-w-none lg:grid-cols-2 lg:px-0">
      {/* Left panel — branding */}
      <div className="login-brand-panel relative hidden h-full flex-col bg-muted p-10 text-white lg:flex dark:border-r">
        <div className="absolute inset-0 bg-zinc-900" />
        <div className="relative z-20 flex items-center text-lg font-medium">
          <div className="mr-2 h-6 w-6 rounded bg-white flex items-center justify-center font-bold text-xs overflow-hidden">
            {logoUrl ? (
              <img src={logoUrl} alt={projectName} className="h-6 w-6 object-contain" />
            ) : (
              <span className="text-zinc-900">{projectName.charAt(0).toUpperCase()}</span>
            )}
          </div>
          {projectName}
        </div>
        <div className="relative z-20 mt-auto">
          <blockquote className="space-y-2">
            <p className="text-lg">
              &ldquo;{t('login.description')}&rdquo;
            </p>
            <footer className="text-sm">{t('login.system_access')}</footer>
          </blockquote>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="login-form-panel lg:p-8">
        <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
          <div className="flex flex-col space-y-2 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">
              {t('login.title')}
            </h1>
            <p className="text-sm text-muted-foreground">
              {t('login.description')}
            </p>
          </div>

          <div className="grid gap-6">
            <form onSubmit={handleLogin}>
              <div className="grid gap-4">
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
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {loading ? t('login.signingIn') : t('login.signIn')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
