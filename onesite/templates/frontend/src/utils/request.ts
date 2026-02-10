import axios from 'axios';

// Get API URL from environment variable
const baseURL = import.meta.env.VITE_API_URL || '/api/v1';

export const request = axios.create({
  baseURL,
  timeout: 10000,
});

request.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      console.error(error.response.data.detail || 'Request failed');
    } else {
      console.error('Network error');
    }
    return Promise.reject(error);
  }
);

export default request;
