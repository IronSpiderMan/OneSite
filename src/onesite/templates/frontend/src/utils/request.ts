import axios from 'axios';
import { toast } from 'sonner';

declare module 'axios' {
  export interface AxiosRequestConfig {
    /** The caller will present a contextual error message for this request. */
    suppressErrorToast?: boolean;
  }
}

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

/**
 * Turn the API's structured errors into a message suitable for a form toast.
 * FastAPI returns validation errors as an array, whereas application errors
 * use a string `detail`; callers should not need to know that distinction.
 */
export const getErrorMessage = (error: unknown, fallback: string): string => {
  const responseData = (error as any)?.response?.data;
  const detail = responseData?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: any) => {
        const location = Array.isArray(item?.loc)
          ? item.loc.filter((part: unknown) => part !== 'body').join('.')
          : '';
        const message = typeof item?.msg === 'string' ? item.msg : '';
        return location ? `${location}: ${message}` : message;
      })
      .filter(Boolean);
    if (messages.length) return messages.join('; ');
  }
  if (typeof responseData?.message === 'string' && responseData.message.trim()) {
    return responseData.message;
  }
  // Axios's "Request failed with status code …" adds no useful context.
  // Keep the caller's action-specific fallback for malformed API responses.
  if ((error as any)?.response) return fallback;
  const message = (error as any)?.message;
  return typeof message === 'string' && message.trim() ? message : fallback;
};

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
    const suppressErrorToast = error.config?.suppressErrorToast === true;
    if (error.response) {
      if (error.response.status === 401) {
        localStorage.removeItem('token');
        if (window.location.pathname !== '/login') {
            redirectTo('/login');
        }
      } else if (error.response.status === 403) {
        const requestUrl = String(error.config?.url || '');
        if (requestUrl === '/register') {
          return Promise.reject(error);
        }
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
      } else if (error.response.status >= 500 && !suppressErrorToast) {
        // Keep the current page usable and surface the server's safe error message.
        // Structured errors (for example a missing DB migration) are not connectivity
        // failures and must never be presented as "offline".
        const detail = error.response.data?.detail;
        toast.error(typeof detail === 'string' ? detail : 'The server could not complete the request. Please try again.');
      }
      console.error(error.response.data?.detail || 'Request failed');
    } else if (error.code === 'ECONNABORTED') {
      // Request timed out — show toast, don't redirect
      if (!suppressErrorToast) toast.error('Request timed out. Please try again.');
      console.error('Request timeout');
    } else if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      if (!window.location.pathname.startsWith('/error/offline')) {
        redirectTo('/error/offline');
      }
      console.error('Network error');
    } else {
      // A reachable network with no HTTP response usually means the API server or
      // proxy is unavailable, not that the user's device is offline.
      if (!suppressErrorToast) toast.error('Unable to reach the server. Please try again.');
      console.error('Server connection error');
    }
    return Promise.reject(error);
  }
);

export default request;
