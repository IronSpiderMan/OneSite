import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import AppLayout from './components/Layout';
import { GeneratedRoutes } from './Routes';
import LoginPage from './pages/Login';

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
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        <Route path="/" element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }>
          <Route index element={<Navigate to={GeneratedRoutes[0]?.path || "/"} replace />} />
          {GeneratedRoutes.map((route) => (
             <Route key={route.path} path={route.path} element={route.element} />
          ))}
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
