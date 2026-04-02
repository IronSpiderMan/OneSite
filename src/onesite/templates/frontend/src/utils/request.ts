import axios from 'axios';

// Get API URL from environment variable
const baseURL = import.meta.env.VITE_API_URL || '/api/v1';

export const request = axios.create({
  baseURL,
  timeout: 10000,
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
            window.location.href = '/login';
        }
      } else if (error.response.status === 403) {
        if (!window.location.pathname.startsWith('/error/403')) {
          window.location.href = '/error/403';
        }
      } else if (error.response.status >= 500) {
        if (!window.location.pathname.startsWith('/error/500')) {
          window.location.href = '/error/500';
        }
      }
      console.error(error.response.data.detail || 'Request failed');
    } else {
      if (!window.location.pathname.startsWith('/error/offline')) {
        window.location.href = '/error/offline';
      }
      console.error('Network error');
    }
    return Promise.reject(error);
  }
);

export default request;
