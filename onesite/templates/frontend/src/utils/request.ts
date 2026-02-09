import axios from 'axios';

const request = axios.create({
  baseURL: '', // Handled by Vite proxy
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
