import React from 'react';
import SettingsPage from './pages/Settings';
import DashboardPage from './pages/Dashboard';


import AdminConfigPage from './pages/admin_config';



import MemberOnlyPostPage from './pages/member_only_post';
import MemberOnlyPostDetailPage from './pages/member_only_post/detail';




import PremiumContentPage from './pages/premium_content';
import PremiumContentDetailPage from './pages/premium_content/detail';




import PublicArticlePage from './pages/public_article';
import PublicArticleDetailPage from './pages/public_article/detail';




import SecretConfigPage from './pages/secret_config';





import UserPage from './pages/user';
import UserDetailPage from './pages/user/detail';




import UserProfilePage from './pages/user_profile';
import UserProfileDetailPage from './pages/user_profile/detail';




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
    path: '/admin_config',
    element: <AdminConfigPage />,
  },



  {
    path: '/member_only_posts',
    element: <MemberOnlyPostPage />,
  },
  
  {
    path: '/member_only_posts/:id',
    element: <MemberOnlyPostDetailPage />,
  },



  {
    path: '/premium_contents',
    element: <PremiumContentPage />,
  },
  
  {
    path: '/premium_contents/:id',
    element: <PremiumContentDetailPage />,
  },



  {
    path: '/public_articles',
    element: <PublicArticlePage />,
  },
  
  {
    path: '/public_articles/:id',
    element: <PublicArticleDetailPage />,
  },



  {
    path: '/secret_config',
    element: <SecretConfigPage />,
  },





  {
    path: '/users',
    element: <UserPage />,
  },
  
  {
    path: '/users/:id',
    element: <UserDetailPage />,
  },



  {
    path: '/user_profiles',
    element: <UserProfilePage />,
  },
  
  {
    path: '/user_profiles/:id',
    element: <UserProfileDetailPage />,
  },


];