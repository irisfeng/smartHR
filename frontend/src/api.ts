import axios, { type InternalAxiosRequestConfig } from 'axios';

const api = axios.create({ baseURL: '' });

let refreshPromise: Promise<void> | null = null;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config as RetryableConfig;
    if (error.response?.status === 428) {
      if (window.location.pathname !== '/force-change-password') {
        window.location.href = '/force-change-password';
      }
      return Promise.reject(error);
    }
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      if (!refreshPromise) {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          localStorage.clear();
          window.location.href = '/login';
          return Promise.reject(error);
        }
        refreshPromise = axios.post('/api/auth/refresh', { refresh_token: refreshToken })
          .then((res) => {
            localStorage.setItem('access_token', res.data.access_token);
            localStorage.setItem('refresh_token', res.data.refresh_token);
          })
          .catch(() => {
            localStorage.clear();
            window.location.href = '/login';
          })
          .finally(() => {
            refreshPromise = null;
          });
      }
      await refreshPromise;
      const token = localStorage.getItem('access_token');
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
