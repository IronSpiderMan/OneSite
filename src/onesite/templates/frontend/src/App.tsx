import { BrowserRouter, HashRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import AppLayout from './components/Layout';
import { GeneratedPublicFeatureRoutes, GeneratedRoutes } from './Routes';
import LoginPage from './pages/Login';
import RegisterPage from './pages/Register';
import ErrorPage from './pages/ErrorPage';
import ProfilePage from './pages/Profile';
import { AppToaster } from './components/ui/sonner';
import SiteMetadata from './SiteMetadata';

// Simple Auth Guard
function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem('token');
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

function App() {
  // Release builds are served through Tauri's custom protocol. Hash routing
  // keeps every route anchored to index.html while preserving BrowserRouter
  // URLs for the regular web build and Tauri development server.
  const Router = import.meta.env.VITE_DESKTOP === 'true' ? HashRouter : BrowserRouter;

  return (
    <Router>
      <SiteMetadata />
      <AppToaster />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/error/:code"
          element={<ErrorPage />}
        />
        {GeneratedPublicFeatureRoutes.map((route) => (
          <Route key={route.id} path={route.path} element={route.element} />
        ))}
        
        <Route path="/" element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }>
          <Route path="profile" element={<ProfilePage />} />
          <Route index element={<Navigate to={GeneratedRoutes[0]?.path || "/"} replace />} />
          {GeneratedRoutes.map((route) => (
             <Route key={route.id} path={route.path} element={route.element} />
          ))}
          <Route path="*" element={<Navigate to="/error/404" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
