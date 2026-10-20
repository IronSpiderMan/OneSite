import React from 'react';
import SettingsPage from './pages/Settings';
import DashboardPage from './pages/Dashboard';


import DataModelPage from './pages/data_model';
import DataModelDetailPage from './pages/data_model/detail';



import DataSourcePage from './pages/data_source';
import DataSourceDetailPage from './pages/data_source/detail';



import DevicePage from './pages/device';
import DeviceDetailPage from './pages/device/detail';





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
    path: '/data_models',
    element: <DataModelPage />,
  },
  {
    path: '/data_models/:id',
    element: <DataModelDetailPage />,
  },



  {
    path: '/data_sources',
    element: <DataSourcePage />,
  },
  {
    path: '/data_sources/:id',
    element: <DataSourceDetailPage />,
  },



  {
    path: '/devices',
    element: <DevicePage />,
  },
  {
    path: '/devices/:id',
    element: <DeviceDetailPage />,
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