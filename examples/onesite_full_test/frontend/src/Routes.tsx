import React from 'react';
import SettingsPage from './pages/Settings';
import DashboardPage from './pages/Dashboard';


import AdminSettingsPage from './pages/admin_settings';



import CategoryPage from './pages/category';
import CategoryDetailPage from './pages/category/detail';




import MetricPage from './pages/metric';
import MetricDetailPage from './pages/metric/detail';




import NotificationPage from './pages/notification';
import NotificationDetailPage from './pages/notification/detail';




import ProductPage from './pages/product';
import ProductDetailPage from './pages/product/detail';






import TagPage from './pages/tag';
import TagDetailPage from './pages/tag/detail';




import UserPage from './pages/user';
import UserDetailPage from './pages/user/detail';




export const GeneratedRoutes = [
  {
    path: '/dashboard',
    element: <DashboardPage />,
  },
  {
    path: '/settings',
    element: <SettingsPage />,
  },


  {
    path: '/admin_settings',
    element: <AdminSettingsPage />,
  },



  {
    path: '/categorys',
    element: <CategoryPage />,
  },
  
  {
    path: '/categorys/:id',
    element: <CategoryDetailPage />,
  },



  {
    path: '/metrics',
    element: <MetricPage />,
  },
  
  {
    path: '/metrics/:id',
    element: <MetricDetailPage />,
  },



  {
    path: '/notifications',
    element: <NotificationPage />,
  },
  
  {
    path: '/notifications/:id',
    element: <NotificationDetailPage />,
  },



  {
    path: '/products',
    element: <ProductPage />,
  },
  
  {
    path: '/products/:id',
    element: <ProductDetailPage />,
  },





  {
    path: '/tags',
    element: <TagPage />,
  },
  
  {
    path: '/tags/:id',
    element: <TagDetailPage />,
  },



  {
    path: '/users',
    element: <UserPage />,
  },
  
  {
    path: '/users/:id',
    element: <UserDetailPage />,
  },


];