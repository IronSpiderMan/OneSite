import React, { useEffect, useState, useCallback } from 'react';
import { Menu as MenuIcon, X, LogOut, Settings, ChevronLeft, ChevronRight, ChevronDown } from 'lucide-react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { GeneratedMenu, filterMenuByRole, findMenuItem, findMenuPath } from '../Menu';
import { cn } from '../lib/utils';
import { Button } from './ui/button';
import { AvatarFallback } from './ui/avatar-fallback';
import { NotificationBell } from './notification-bell';

type ThemeStyle = 'normal' | 'industrial' | 'neuron';

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
  neuron: 'rounded-none',
};

// Theme-specific active nav item
const NAV_ACTIVE: Record<ThemeStyle, string> = {
  normal: 'bg-primary/10 text-primary font-medium border-r-[3px] border-primary pr-[calc(1rem-3px)]',
  industrial: 'bg-primary text-primary-foreground border-l-[3px] border-accent pl-[calc(1rem-3px)]',
  neuron: 'bg-primary/10 text-primary font-semibold border-l-2 border-primary pl-[calc(1rem-2px)]',
};
const NAV_INACTIVE: Record<ThemeStyle, string> = {
  normal: 'text-foreground/75 hover:bg-muted hover:text-primary border-r-[3px] border-transparent',
  industrial: 'hover:bg-accent hover:text-accent-foreground border-l-[3px] border-transparent',
  neuron: 'hover:bg-muted hover:text-foreground border-l-2 border-transparent',
};
const NAV_ITEM_BASE: Record<ThemeStyle, string> = {
  normal: 'rounded-none',
  industrial: 'rounded-none',
  neuron: 'rounded-none',
};

// Theme-specific header classes
const HEADER_EXTRA: Record<ThemeStyle, string> = {
  normal: 'border-b border-b-border shadow-[0_1px_4px_rgb(0_21_41_/_0.08)]',
  industrial: 'border-b-2 border-b-accent/30',
  neuron: 'border-b border-b-border',
};

// Theme-specific logo area
const LOGO_AREA_EXTRA: Record<ThemeStyle, string> = {
  normal: 'border-b border-b-border',
  industrial: 'border-b-2 border-b-accent/40',
  neuron: 'border-b border-b-border',
};

const AppLayout: React.FC = () => {
  const { t } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebar_collapsed') === 'true');
  const [openMenuGroups, setOpenMenuGroups] = useState<Record<string, boolean>>({});
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useThemeStyle();

  const [userName, setUserName] = useState(localStorage.getItem('user_name') || 'Admin User');
  const [userAvatar, setUserAvatar] = useState(localStorage.getItem('user_avatar'));
  const [userRole, setUserRole] = useState(localStorage.getItem('user_role') || 'user');
  const [isOnline, setIsOnline] = useState(false);
  const fallbackProjectName = window.__ENV__?.PROJECT_NAME || import.meta.env.VITE_PROJECT_NAME || 'OneSite';
  const [projectName, setProjectName] = useState(
    () => localStorage.getItem('onesite_site_name') || fallbackProjectName
  );
  const fallbackLogo = window.__ENV__?.PROJECT_LOGO || import.meta.env.VITE_PROJECT_LOGO || '';
  const [logoUrl, setLogoUrl] = useState(
    () => localStorage.getItem('onesite_site_logo') || fallbackLogo
  );

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
    const syncSiteLogo = (event?: Event) => {
      const updatedLogo = (event as CustomEvent<string> | undefined)?.detail;
      setLogoUrl(
        updatedLogo || localStorage.getItem('onesite_site_logo') || fallbackLogo
      );
    };
    window.addEventListener('onesite:site_logo_updated', syncSiteLogo);
    window.addEventListener('storage', syncSiteLogo);
    return () => {
      window.removeEventListener('onesite:site_logo_updated', syncSiteLogo);
      window.removeEventListener('storage', syncSiteLogo);
    };
  }, [fallbackLogo]);

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const isCollapsed = collapsed;
  const isNormal = theme === 'normal';
  const isNeuron = theme === 'neuron';

  const sidebarWidth = isCollapsed ? SIDEBAR_WIDTH_COLLAPSED : isNormal ? 'md:w-56' : SIDEBAR_WIDTH;
  const mainMargin = isCollapsed ? MAIN_MARGIN_COLLAPSED : isNormal ? 'md:ml-56' : MAIN_MARGIN;

  const logoLink = window.__ENV__?.LOGO_LINK || import.meta.env.VITE_LOGO_LINK || '/dashboard';

  const menuItems = filterMenuByRole(GeneratedMenu, userRole);
  const activeMenuItem = findMenuItem(menuItems, location.pathname);
  const activeMenuPath = findMenuPath(menuItems, location.pathname);
  const groupContainsActiveItem = (item: any): boolean =>
    item.type === 'group' && item.children.some((child: any) =>
      child.type === 'item'
        ? child.key === location.pathname
        : groupContainsActiveItem(child)
    );
  const activePageName = activeMenuItem
    ? t(activeMenuItem.label)
    : location.pathname === '/settings'
      ? t('common.settings')
      : t('common.dashboard', 'Dashboard');

  return (
    <div className={cn("h-screen overflow-hidden flex", isNormal && "ant-admin-shell")}>
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
          isNormal && "ant-admin-sider",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo area */}
        <div className={cn("h-16 flex items-center px-4 border-b", LOGO_AREA_EXTRA[theme], isNormal && "ant-admin-brand", isNeuron && "neuron-brand-area h-[72px] px-5", isCollapsed ? "justify-center" : "justify-between")}>
          {isNeuron ? (
            <Link to={logoLink} className="neuron-brand min-w-0 no-underline">
              {logoUrl ? (
                <img src={logoUrl} alt={projectName} className={cn("neuron-project-logo", isCollapsed && "neuron-project-logo--collapsed")} />
              ) : (
                <span className="neuron-mark" aria-hidden="true">
                  <><i /><i /><i /></>
                </span>
              )}
              {!isCollapsed && (
                <span className="neuron-brand-copy">
                  <strong className="truncate">{projectName}</strong>
                  <small>NEURAL OPERATIONS</small>
                </span>
              )}
            </Link>
          ) : (
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
          )}
          {!isCollapsed && (
            <Button variant="ghost" size="icon" className="md:hidden flex-shrink-0" onClick={() => setSidebarOpen(false)}>
              <X className="h-5 w-5" />
            </Button>
          )}
        </div>

        {/* Navigation */}
        <nav className={cn("flex-1 overflow-y-auto py-4", isNormal && "ant-admin-menu", isNeuron && "neuron-nav", isCollapsed ? "px-2" : isNormal ? "px-0" : "px-4")}>
          {!isCollapsed && (
            <div className={cn("px-4 py-2 text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground", isNeuron && "neuron-nav-heading")}>
              {isNeuron ? <><span>01</span> OPERATIONS</> : t('common.navigation', 'Navigation')}
            </div>
          )}

          <div className={cn("space-y-1", isNormal && "space-y-0")}>
            {menuItems.map((item: any) => {
              if (item.type === 'group') {
                const containsActiveItem = groupContainsActiveItem(item);
                const isOpen = openMenuGroups[item.key] ?? (item.defaultOpen || containsActiveItem);
                return (
                  <div
                    key={item.key}
                    className={cn(
                      "menu-nav-group mb-1",
                      !isCollapsed && isOpen && "menu-nav-group--open"
                    )}
                  >
                    <button
                      type="button"
                      title={isCollapsed ? t(item.label) : undefined}
                      aria-expanded={!isCollapsed && isOpen}
                      onClick={() => {
                        if (isCollapsed) {
                          localStorage.setItem('sidebar_collapsed', 'false');
                          setCollapsed(false);
                          setOpenMenuGroups(groups => ({ ...groups, [item.key]: true }));
                          return;
                        }
                        setOpenMenuGroups(groups => ({ ...groups, [item.key]: !isOpen }));
                      }}
                      className={cn(
                        "w-full flex items-center transition-all duration-150",
                        isNeuron && "neuron-nav-item",
                        NAV_ITEM_BASE[theme],
                        isCollapsed
                          ? "justify-center py-2.5 px-0"
                          : "space-x-2 px-4 py-2",
                        !isCollapsed && "menu-nav-group-trigger",
                        containsActiveItem ? NAV_ACTIVE[theme] : NAV_INACTIVE[theme]
                      )}
                    >
                      {item.icon}
                      {!isCollapsed && <>
                        <span className="flex-1 text-left text-sm font-medium">{t(item.label)}</span>
                        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", isOpen && "rotate-180")} />
                      </>}
                    </button>
                    {!isCollapsed && isOpen && (
                      <div className={cn(
                        "menu-nav-group-children ml-4 border-l py-0.5",
                        isNormal ? "border-border/60" : theme === 'industrial' ? "border-accent/40" : "border-primary/25"
                      )}>
                        {item.children.map((child: any) => {
                          const isChildActive = location.pathname === child.key;
                          return (
                            <Link
                              key={child.key}
                              to={child.key}
                              aria-current={isChildActive ? 'page' : undefined}
                              className={cn(
                                "menu-nav-group-child flex items-center gap-2 py-2 pl-5 pr-4 text-sm transition-all duration-150",
                                isNeuron && "neuron-nav-item",
                                isChildActive ? NAV_ACTIVE[theme] : NAV_INACTIVE[theme]
                              )}
                            >
                              {child.icon}
                              <span className="font-medium">{t(child.label)}</span>
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              }
              return (
                <Link
                  key={item.key}
                  to={item.key}
                  title={isCollapsed ? t(item.label) : undefined}
                  className={cn(
                    "flex items-center transition-all duration-150",
                    isNeuron && "neuron-nav-item",
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
              );
            })}
          </div>

          {/* System section */}
          <div className={cn("mt-4 pt-4 border-t", isCollapsed && "border-t-border/30")}>
            {!isCollapsed && (
              <div className={cn("px-4 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground", isNeuron && "neuron-nav-heading")}>
                {isNeuron ? <><span>02</span> SYSTEM</> : t('common.system', 'System')}
              </div>
            )}
            <Link
              to="/settings"
              title={isCollapsed ? t('common.settings') : undefined}
              className={cn(
                "flex items-center transition-all duration-150",
                isNeuron && "neuron-nav-item",
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
      <div className={cn("flex-1 flex flex-col min-w-0 min-h-0", mainMargin)}>
        <header className={cn("h-16 bg-card flex items-center px-4 justify-between sticky top-0 z-40", HEADER_EXTRA[theme], isNormal && "ant-admin-header", isNeuron && "neuron-header h-[72px] px-5 md:px-7")}>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setSidebarOpen(true)}>
                  <MenuIcon className="h-5 w-5" />
              </Button>
              {isCollapsed && (
                <Button variant="ghost" size="icon" className="hidden md:flex" onClick={toggleCollapsed}>
                  <MenuIcon className="h-5 w-5" />
                </Button>
              )}
              {isNeuron && (
                <div className="neuron-breadcrumbs hidden sm:flex">
                  <span>{projectName.toUpperCase()}</span>
                  {activeMenuPath.length > 0 ? activeMenuPath.map((item, index) => (
                    <React.Fragment key={item.key}>
                      <i>/</i>
                      {index === activeMenuPath.length - 1
                        ? <b>{t(item.label)}</b>
                        : <span>{t(item.label)}</span>}
                    </React.Fragment>
                  )) : <>
                    <i>/</i>
                    <b>{activePageName}</b>
                  </>}
                </div>
              )}
            </div>
            <div className="flex items-center space-x-2">
                <NotificationBell onStatusChange={setIsOnline} />
                <Button variant="ghost" type="button" onClick={() => navigate('/profile')} className={cn("h-10 px-2", isNeuron && "neuron-user-control")}>
                    <AvatarFallback name={userName} src={userAvatar} size={32} isOnline={isOnline} />
                    <span className="ml-2 text-sm text-muted-foreground hidden sm:inline">{userName}</span>
                </Button>
                <Button variant="ghost" size="icon" onClick={handleLogout} title={t('common.logout')}>
                    <LogOut className="h-5 w-5" />
                </Button>
            </div>
        </header>
        <main className={cn("flex-1 min-h-0 p-6 overflow-auto", isNormal && "ant-admin-content", isNeuron && "neuron-workspace px-5 py-6 md:px-8 md:py-7")}>
            <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
