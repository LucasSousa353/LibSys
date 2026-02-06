import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('token_type');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const response = await api.post('/token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },
};

export const usersApi = {
  create: async (data: { name: string; email: string; password: string }) => {
    const response = await api.post('/users/', data);
    return response.data;
  },

  list: async (skip = 0, limit = 10) => {
    const response = await api.get('/users/', { params: { skip, limit } });
    return response.data;
  },

  lookup: async (query: string, skip = 0, limit = 10) => {
    const response = await api.get('/users/lookup', { params: { q: query, skip, limit } });
    return response.data;
  },

  lookupByIds: async (ids: number[]) => {
    const params = new URLSearchParams();
    ids.forEach((id) => params.append('ids', String(id)));
    const response = await api.get('/users/lookup/ids', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/users/${id}`);
    return response.data;
  },

  me: async () => {
    const response = await api.get('/users/me');
    return response.data;
  },

  exportPdf: async () => {
    const response = await api.get('/users/export/pdf', { responseType: 'blob' });
    return response.data as Blob;
  },
};

export const booksApi = {
  create: async (data: { title: string; author: string; isbn: string; total_copies: number }) => {
    const response = await api.post('/books/', data);
    return response.data;
  },

  list: async (params?: { title?: string; author?: string; skip?: number; limit?: number }) => {
    const response = await api.get('/books/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get(`/books/${id}`);
    return response.data;
  },

  exportPdf: async (params?: { title?: string; author?: string }) => {
    const response = await api.get('/books/export/pdf', { params, responseType: 'blob' });
    return response.data as Blob;
  },
};

export const loansApi = {
  create: async (data: { user_id: number; book_id: number }) => {
    const response = await api.post('/loans/', data);
    return response.data;
  },

  return: async (loanId: number) => {
    const response = await api.post(`/loans/${loanId}/return`);
    return response.data;
  },

  extend: async (loanId: number) => {
    const response = await api.post(`/loans/${loanId}/extend`);
    return response.data;
  },

  list: async (params?: { status?: 'active' | 'returned' | 'overdue'; user_id?: number; skip?: number; limit?: number }) => {
    const response = await api.get('/loans/', { params });
    return response.data;
  },

  exportCsv: async (params?: { status?: 'active' | 'returned' | 'overdue'; user_id?: number }) => {
    const response = await api.get('/loans/export/csv', { params, responseType: 'blob' });
    return response.data as Blob;
  },

  exportPdf: async (params?: { status?: 'active' | 'returned' | 'overdue'; user_id?: number }) => {
    const response = await api.get('/loans/export/pdf', { params, responseType: 'blob' });
    return response.data as Blob;
  },
};

export const healthApi = {
  check: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
