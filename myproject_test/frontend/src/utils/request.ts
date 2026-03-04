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
      config.headers.Authorization = `Bearer ${token}`;
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
      if (error.response.status === 401 || error.response.status === 403) {
        // Redirect to login if unauthorized or forbidden (often means token expired/invalid)
        localStorage.removeItem('token');
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
      }
      console.error(error.response.data.detail || 'Request failed');
    } else {
      console.error('Network error');
    }
    return Promise.reject(error);
  }
);

export default request;
