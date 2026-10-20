import React from 'react';
import SettingsPage from './pages/Settings';
import DashboardPage from './pages/Dashboard';


import AuthorPage from './pages/author';
import AuthorDetailPage from './pages/author/detail';




import BookPage from './pages/book';
import BookDetailPage from './pages/book/detail';




import SubjectPage from './pages/subject';
import SubjectDetailPage from './pages/subject/detail';






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
    path: '/authors',
    element: <AuthorPage />,
  },
  
  {
    path: '/authors/:id',
    element: <AuthorDetailPage />,
  },



  {
    path: '/books',
    element: <BookPage />,
  },
  
  {
    path: '/books/:id',
    element: <BookDetailPage />,
  },



  {
    path: '/subjects',
    element: <SubjectPage />,
  },
  
  {
    path: '/subjects/:id',
    element: <SubjectDetailPage />,
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