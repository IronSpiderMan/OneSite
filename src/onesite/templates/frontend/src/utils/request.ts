import axios from 'axios';
import { toast } from 'sonner';

// Runtime API URL from window.__ENV__ (set at container startup via envsubst)
// Falls back to VITE_API_URL (baked at build time) if not set
declare global {
  interface Window {
    __ENV__?: { API_URL?: string; DOMAIN?: string; NODE_ENV?: string; BUILD_VERSION?: string; LOGO_LINK?: string; PROJECT_NAME?: string; PROJECT_LOGO?: string };
  }
}

export const getBaseURL = () => {
  if (import.meta.env.VITE_DESKTOP === 'true') {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window !== 'undefined' && window.__ENV__?.API_URL) {
    return window.__ENV__.API_URL;
  }
  return import.meta.env.VITE_API_URL || '/api/v1';
};

const redirectTo = (path: string) => {
  if (import.meta.env.VITE_DESKTOP === 'true') {
    window.location.hash = `#${path}`;
  } else {
    window.location.href = path;
  }
};

const baseURL = getBaseURL();

export const request = axios.create({
  baseURL,
  timeout: 30000,
});

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      const headersAny: any = (config as any).headers || {};
      if (typeof headersAny.set === 'function') {
        headersAny.set('Authorization', `Bearer ${token}`);
      } else {
        headersAny.Authorization = `Bearer ${token}`;
      }
      (config as any).headers = headersAny;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

request.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        localStorage.removeItem('token');
        if (window.location.pathname !== '/login') {
            redirectTo('/login');
        }
      } else if (error.response.status === 403) {
        // If the 403 is actually an auth failure (stale/expired token),
        // treat it like 401: clear token and redirect to login
        const detail = error.response.data?.detail || '';
        if (detail.includes('Could not validate credentials')) {
          localStorage.removeItem('token');
          if (window.location.pathname !== '/login') {
            redirectTo('/login');
          }
        } else if (!window.location.pathname.startsWith('/error/403')) {
          redirectTo('/error/403');
        }
      } else if (error.response.status >= 500) {
        if (!window.location.pathname.startsWith('/error/500')) {
          redirectTo('/error/500');
        }
      }
      console.error(error.response.data.detail || 'Request failed');
    } else if (error.code === 'ECONNABORTED') {
      // Request timed out — show toast, don't redirect
      toast.error('Request timed out. Please try again.');
      console.error('Request timeout');
    } else {
      if (!window.location.pathname.startsWith('/error/offline')) {
        redirectTo('/error/offline');
      }
      console.error('Network error');
    }
    return Promise.reject(error);
  }
);

export default request;
