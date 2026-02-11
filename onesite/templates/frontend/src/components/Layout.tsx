import React, { useState } from 'react';
import { LayoutDashboard, Menu as MenuIcon, X, LogOut, Settings } from 'lucide-react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { GeneratedMenu } from '../Menu';
import { cn } from '../lib/utils';
import { Button } from './ui/button';

const AppLayout: React.FC = () => {
  const { t } = useTranslation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-card border-r transition-transform duration-300 ease-in-out transform md:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b">
          <span className="text-xl font-bold">OneSite</span>
          <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <nav className="p-4 space-y-2">
          {GeneratedMenu.map((item: any) => (
            <Link
              key={item.key}
              to={item.key}
              className={cn(
                "flex items-center space-x-2 px-4 py-2 rounded-md transition-colors",
                location.pathname === item.key
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {item.icon}
              <span>{t(item.label)}</span>
            </Link>
          ))}
          
          <div className="pt-4 border-t my-2"></div>
          
          <Link
            to="/settings"
            className={cn(
              "flex items-center space-x-2 px-4 py-2 rounded-md transition-colors",
              location.pathname === "/settings"
                ? "bg-primary text-primary-foreground"
                : "hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <Settings className="h-4 w-4" />
            <span>{t('common.settings')}</span>
          </Link>
          
        </nav>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 md:ml-64">
        <header className="h-16 border-b bg-card flex items-center px-4 justify-between sticky top-0 z-40">
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setSidebarOpen(true)}>
                <MenuIcon className="h-5 w-5" />
            </Button>
            <div className="ml-auto flex items-center space-x-4">
                <span className="text-sm text-muted-foreground">Admin User</span>
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
