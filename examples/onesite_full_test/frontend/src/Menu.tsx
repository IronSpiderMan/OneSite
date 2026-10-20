import React from 'react';
import { LayoutDashboard, Home } from 'lucide-react';

export const GeneratedMenu = [
  {
    key: '/dashboard',
    icon: <Home className="h-4 w-4" />,
    label: 'menu.dashboard',
    minRole: 'user',
  },


  {
    key: '/admin_settings',
    icon: <LayoutDashboard className="h-4 w-4" />,
    label: 'models.admin_settings.name',
    
    visible: {"admin": true, "developer": true, "user": false},
    minRole: 'admin',
  },



  {
    key: '/categorys',
    icon: <LayoutDashboard className="h-4 w-4" />,
    label: 'models.category.name',
    
    visible: {"admin": true, "developer": true, "user": true},
    minRole: 'user',
  },



  {
    key: '/metrics',
    icon: <LayoutDashboard className="h-4 w-4" />,
    label: 'models.metric.name',
    
    visible: {"admin": true, "developer": true, "user": true},
    minRole: 'user',
  },



  {
    key: '/notifications',
    icon: <LayoutDashboard className="h-4 w-4" />,
    label: 'models.notification.name',
    
    visible: {"admin": true, "developer": true, "user": true},
    minRole: 'user',
  },



  {
    key: '/products',
    icon: <LayoutDashboard className="h-4 w-4" />,
    label: 'models.product.name',
    
    visible: {"admin": true, "developer": true, "user": true},
    minRole: 'user',
  },





  {
    key: '/tags',
    icon: <LayoutDashboard className="h-4 w-4" />,
    label: 'models.tag.name',
    
    visible: {"admin": true, "developer": true, "user": true},
    minRole: 'user',
  },



  {
    key: '/users',
    icon: <LayoutDashboard className="h-4 w-4" />,
    label: 'models.user.name',
    
    visible: {"admin": true, "developer": true, "user": true},
    minRole: 'user',
  },


];

// Role hierarchy for filtering
const ROLE_HIERARCHY: Record<string, number> = {
  'user': 0,
  'admin': 1,
  'developer': 2,
};

export function filterMenuByRole(menu: typeof GeneratedMenu, userRole: string): typeof GeneratedMenu {
  const userLevel = ROLE_HIERARCHY[userRole] ?? 0;
  return menu.filter(item => {
    // Check if item has explicit visible config
    if ('visible' in item && item.visible) {
      const itemVisible = item.visible as Record<string, boolean>;
      return itemVisible[userRole] ?? false;
    }
    // Fall back to minRole check
    return (ROLE_HIERARCHY[item.minRole] ?? 0) <= userLevel;
  }).map(item => {
    // Use myLabel for user role when available (owner-scoped models)
    if (userRole === 'user' && 'myLabel' in item) {
      return { ...item, label: item.myLabel as string };
    }
    return item;
  });
}