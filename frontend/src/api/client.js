import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('academicos_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// On 401 wipe local session so the login page shows
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('academicos_token');
      localStorage.removeItem('academicos_user');
      window.dispatchEvent(new Event('auth:logout'));
    }
    return Promise.reject(err);
  }
);

export default api;
