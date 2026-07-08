import React, { useEffect, useState, useCallback } from 'react';
import { LayoutDashboard, Menu as MenuIcon, X, LogOut, Settings, ChevronLeft, ChevronRight } from 'lucide-react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { GeneratedMenu, filterMenuByRole } from '../Menu';
import { cn } from '../lib/utils';
import { Button } from './ui/button';
import { AvatarFallback } from './ui/avatar-fallback';
import { NotificationBell } from './notification-bell';

type ThemeStyle = 'normal' | 'industrial' | 'anime' | 'cute' | 'emqx';

function useThemeStyle(): ThemeStyle {
  const [style, setStyle] = useState<ThemeStyle>(
    (document.documentElement.getAttribute('data-theme') as ThemeStyle) || 'normal'
  );
  useEffect(() => {
    const observer = new MutationObserver(() => {
      const v = document.documentElement.getAttribute('data-theme') as ThemeStyle;
      if (v) setStyle(v);
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);
  return style;
}

const SIDEBAR_WIDTH = 'md:w-64';
const SIDEBAR_WIDTH_COLLAPSED = 'md:w-16';
const MAIN_MARGIN = 'md:ml-64';
const MAIN_MARGIN_COLLAPSED = 'md:ml-16';

// Theme-specific sidebar classes
const SIDEBAR_EXTRA: Record<ThemeStyle, string> = {
  normal: '',
  industrial: 'rounded-none',
  emqx: '',
  anime: 'rounded-r-2xl',
  cute: 'rounded-r-3xl',
};

// Theme-specific active nav item
const NAV_ACTIVE: Record<ThemeStyle, string> = {
  normal: 'bg-primary text-primary-foreground border-l-[3px] border-accent pl-[calc(1rem-3px)]',
  industrial: 'bg-primary text-primary-foreground border-l-[3px] border-accent pl-[calc(1rem-3px)]',
  emqx: 'bg-primary/10 text-primary font-semibold',
  anime: 'bg-primary text-primary-foreground rounded-xl',
  cute: 'bg-primary/15 text-primary rounded-full',
};
const NAV_INACTIVE: Record<ThemeStyle, string> = {
  normal: 'hover:bg-accent hover:text-accent-foreground border-l-[3px] border-transparent',
  industrial: 'hover:bg-accent hover:text-accent-foreground border-l-[3px] border-transparent',
  emqx: 'hover:bg-muted/70',
  anime: 'hover:bg-accent hover:text-accent-foreground rounded-xl',
  cute: 'hover:bg-accent/50 hover:text-accent-foreground rounded-full',
};
const NAV_ITEM_BASE: Record<ThemeStyle, string> = {
  normal: 'rounded-md',
  industrial: 'rounded-none',
  emqx: 'rounded-md',
  anime: 'rounded-xl',
  cute: 'rounded-full',
};

// Theme-specific header classes
const HEADER_EXTRA: Record<ThemeStyle, string> = {
  normal: 'border-b-2 border-b-accent/20',
  industrial: 'border-b-2 border-b-accent/30',
  emqx: 'border-b border-b-border',
  anime: 'border-b-2 border-b-primary/15 rounded-bl-2xl',
  cute: 'border-b-2 border-b-primary/10 rounded-bl-3xl',
};

// Theme-specific logo area
const LOGO_AREA_EXTRA: Record<ThemeStyle, string> = {
  normal: 'border-b-2 border-b-accent/30',
  industrial: 'border-b-2 border-b-accent/40',
  emqx: 'border-b border-b-border',
  anime: 'border-b-2 border-b-primary/15',
  cute: 'border-b-2 border-b-primary/10',
};

const AppLayout: React.FC = () => {
  const { t } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebar_collapsed') === 'true');
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useThemeStyle();

  const [userName, setUserName] = useState(localStorage.getItem('user_name') || 'Admin User');
  const [userAvatar, setUserAvatar] = useState(localStorage.getItem('user_avatar'));
  const [userRole, setUserRole] = useState(localStorage.getItem('user_role') || 'user');
  const [isOnline, setIsOnline] = useState(false);

  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('sidebar_collapsed', String(next));
      return next;
    });
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_role');
    navigate('/login');
  };

  useEffect(() => {
    const sync = () => {
      setUserName(localStorage.getItem('user_name') || 'Admin User');
      setUserAvatar(localStorage.getItem('user_avatar'));
      setUserRole(localStorage.getItem('user_role') || 'user');
    };
    sync();
    window.addEventListener('onesite:user_updated', sync as any);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('onesite:user_updated', sync as any);
      window.removeEventListener('storage', sync);
    };
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const isCollapsed = collapsed;

  const sidebarWidth = isCollapsed ? SIDEBAR_WIDTH_COLLAPSED : SIDEBAR_WIDTH;
  const mainMargin = isCollapsed ? MAIN_MARGIN_COLLAPSED : MAIN_MARGIN;

  const logoUrl = import.meta.env.VITE_PROJECT_LOGO;
  const projectName = import.meta.env.VITE_PROJECT_NAME || 'OneSite';
  const logoLink = window.__ENV__?.LOGO_LINK || import.meta.env.VITE_LOGO_LINK || '/dashboard';

  const menuItems = filterMenuByRole(GeneratedMenu, userRole);

  return (
    <div className="min-h-screen flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 bg-card transition-transform duration-300 ease-in-out transform md:translate-x-0",
          sidebarWidth,
          SIDEBAR_EXTRA[theme],
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo area */}
        <div className={cn("h-16 flex items-center px-4 border-b", LOGO_AREA_EXTRA[theme], isCollapsed ? "justify-center" : "justify-between")}>
          <Link to={logoLink} className="flex items-center gap-3 min-w-0 no-underline">
            {isCollapsed ? (
              <div className="flex-shrink-0">
                {logoUrl ? (
                  <img src={logoUrl} alt="Logo" className="h-8 w-8 rounded-lg object-contain" />
                ) : (
                  <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                    {projectName.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-3 min-w-0">
                {logoUrl ? (
                  <img src={logoUrl} alt="Logo" className="h-8 w-8 rounded-lg object-contain flex-shrink-0" />
                ) : (
                  <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-bold text-sm flex-shrink-0">
                    {projectName.charAt(0).toUpperCase()}
                  </div>
                )}
                <span className="text-xl font-bold truncate">{projectName}</span>
              </div>
            )}
          </Link>
          {!isCollapsed && (
            <Button variant="ghost" size="icon" className="md:hidden flex-shrink-0" onClick={() => setSidebarOpen(false)}>
              <X className="h-5 w-5" />
            </Button>
          )}
        </div>

        {/* Navigation */}
        <nav className={cn("flex-1 overflow-y-auto py-4", isCollapsed ? "px-2" : "px-4")}>
          {!isCollapsed && (
            <div className="px-4 py-2 text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              {t('common.navigation', 'Navigation')}
            </div>
          )}

          <div className="space-y-1">
            {menuItems.map((item: any) => (
              <Link
                key={item.key}
                to={item.key}
                title={isCollapsed ? t(item.label) : undefined}
                className={cn(
                  "flex items-center transition-all duration-150",
                  NAV_ITEM_BASE[theme],
                  isCollapsed
                    ? "justify-center py-2.5 px-0"
                    : "space-x-2 px-4 py-2",
                  location.pathname === item.key
                    ? NAV_ACTIVE[theme]
                    : NAV_INACTIVE[theme]
                )}
              >
                {item.icon}
                {!isCollapsed && <span className="text-sm font-medium">{t(item.label)}</span>}
              </Link>
            ))}
          </div>

          {/* System section */}
          <div className={cn("mt-4 pt-4 border-t", isCollapsed && "border-t-border/30")}>
            {!isCollapsed && (
              <div className="px-4 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                {t('common.system', 'System')}
              </div>
            )}
            <Link
              to="/settings"
              title={isCollapsed ? t('common.settings') : undefined}
              className={cn(
                "flex items-center transition-all duration-150",
                NAV_ITEM_BASE[theme],
                isCollapsed
                  ? "justify-center py-2.5 px-0"
                  : "space-x-2 px-4 py-2",
                location.pathname === "/settings"
                  ? NAV_ACTIVE[theme]
                  : NAV_INACTIVE[theme]
              )}
            >
              <Settings className="h-4 w-4" />
              {!isCollapsed && <span className="text-sm font-medium">{t('common.settings')}</span>}
            </Link>
          </div>
        </nav>

        {/* Collapse toggle (desktop only) */}
        <div className={cn("hidden md:flex border-t p-2", isCollapsed ? "justify-center" : "justify-end")}>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleCollapsed}
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            title={isCollapsed ? t('common.expand', 'Expand') : t('common.collapse', 'Collapse')}
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className={cn("flex-1 flex flex-col min-w-0", mainMargin)}>
        <header className={cn("h-16 bg-card flex items-center px-4 justify-between sticky top-0 z-40", HEADER_EXTRA[theme])}>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setSidebarOpen(true)}>
                  <MenuIcon className="h-5 w-5" />
              </Button>
              {isCollapsed && (
                <Button variant="ghost" size="icon" className="hidden md:flex" onClick={toggleCollapsed}>
                  <MenuIcon className="h-5 w-5" />
                </Button>
              )}
            </div>
            <div className="flex items-center space-x-2">
                <NotificationBell onStatusChange={setIsOnline} />
                <Button variant="ghost" type="button" onClick={() => navigate('/profile')} className="h-10 px-2">
                    <AvatarFallback name={userName} src={userAvatar} size={32} isOnline={isOnline} />
                    <span className="ml-2 text-sm text-muted-foreground hidden sm:inline">{userName}</span>
                </Button>
                <Button variant="ghost" size="icon" onClick={handleLogout} title={t('common.logout')}>
                    <LogOut className="h-5 w-5" />
                </Button>
            </div>
        </header>
        <main className="flex-1 p-6 overflow-auto">
            <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
