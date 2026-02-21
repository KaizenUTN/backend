# Guía de Integración Frontend - API de Autenticación

Esta guía muestra cómo integrar la API de autenticación con diferentes frameworks y tecnologías frontend.

---

## 📱 React / Next.js

### 1. Configuración Básica

```javascript
// src/config/api.js
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export const API_ENDPOINTS = {
  LOGIN: '/auth/login/',
  REGISTER: '/auth/register/',
  LOGOUT: '/auth/logout/',
  REFRESH: '/auth/refresh/',
  PROFILE: '/auth/profile/',
  CHANGE_PASSWORD: '/auth/change-password/',
};
```

### 2. Servicio de Autenticación

```javascript
// src/services/authService.js
import axios from 'axios';
import { API_BASE_URL, API_ENDPOINTS } from '../config/api';

// Configurar axios con interceptors
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token en cada request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor para refresh automático de token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refreshToken');
        const response = await axios.post(`${API_BASE_URL}${API_ENDPOINTS.REFRESH}`, {
          refresh: refreshToken,
        });

        const { access } = response.data;
        localStorage.setItem('accessToken', access);

        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Redirigir al login si el refresh falla
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

const authService = {
  async login(email, password) {
    const response = await api.post(API_ENDPOINTS.LOGIN, { email, password });
    const { access, refresh, user } = response.data;
    
    localStorage.setItem('accessToken', access);
    localStorage.setItem('refreshToken', refresh);
    localStorage.setItem('user', JSON.stringify(user));
    
    return { access, refresh, user };
  },

  async register(userData) {
    const response = await api.post(API_ENDPOINTS.REGISTER, userData);
    const { access, refresh, user } = response.data;
    
    localStorage.setItem('accessToken', access);
    localStorage.setItem('refreshToken', refresh);
    localStorage.setItem('user', JSON.stringify(user));
    
    return { access, refresh, user };
  },

  async logout() {
    const refreshToken = localStorage.getItem('refreshToken');
    
    try {
      await api.post(API_ENDPOINTS.LOGOUT, { refresh: refreshToken });
    } finally {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
    }
  },

  async getProfile() {
    const response = await api.get(API_ENDPOINTS.PROFILE);
    const user = response.data;
    localStorage.setItem('user', JSON.stringify(user));
    return user;
  },

  async updateProfile(data) {
    const response = await api.patch(API_ENDPOINTS.PROFILE, data);
    const user = response.data;
    localStorage.setItem('user', JSON.stringify(user));
    return user;
  },

  async changePassword(oldPassword, newPassword, newPasswordConfirm) {
    const response = await api.post(API_ENDPOINTS.CHANGE_PASSWORD, {
      old_password: oldPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    });
    return response.data;
  },

  isAuthenticated() {
    return !!localStorage.getItem('accessToken');
  },

  getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },
};

export default authService;
```

### 3. Context Provider (React)

```javascript
// src/contexts/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import authService from '../services/authService';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      if (authService.isAuthenticated()) {
        try {
          const userData = await authService.getProfile();
          setUser(userData);
        } catch (error) {
          console.error('Error loading user:', error);
          authService.logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const { user } = await authService.login(email, password);
    setUser(user);
  };

  const register = async (userData) => {
    const { user } = await authService.register(userData);
    setUser(user);
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  const updateProfile = async (data) => {
    const updatedUser = await authService.updateProfile(data);
    setUser(updatedUser);
  };

  const value = {
    user,
    login,
    register,
    logout,
    updateProfile,
    isAuthenticated: !!user,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
```

### 4. Componentes de Login y Registro

```javascript
// src/pages/Login.jsx
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h1>Iniciar Sesión</h1>
      <form onSubmit={handleSubmit}>
        {error && <div className="error">{error}</div>}
        
        <div className="form-group">
          <label>Email:</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>Contraseña:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <button type="submit" disabled={loading}>
          {loading ? 'Cargando...' : 'Iniciar Sesión'}
        </button>
      </form>
    </div>
  );
};

export default Login;
```

### 5. Protected Route

```javascript
// src/components/ProtectedRoute.jsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div>Cargando...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default ProtectedRoute;
```

---

## 🅰️ Angular

### 1. Servicio de Autenticación

```typescript
// src/app/services/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
}

interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private currentUserSubject: BehaviorSubject<User | null>;
  public currentUser: Observable<User | null>;

  constructor(private http: HttpClient) {
    const userStr = localStorage.getItem('user');
    this.currentUserSubject = new BehaviorSubject<User | null>(
      userStr ? JSON.parse(userStr) : null
    );
    this.currentUser = this.currentUserSubject.asObservable();
  }

  public get currentUserValue(): User | null {
    return this.currentUserSubject.value;
  }

  login(email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/login/`, {
      email,
      password
    }).pipe(
      map(response => {
        localStorage.setItem('accessToken', response.access);
        localStorage.setItem('refreshToken', response.refresh);
        localStorage.setItem('user', JSON.stringify(response.user));
        this.currentUserSubject.next(response.user);
        return response;
      })
    );
  }

  register(userData: any): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/register/`, userData)
      .pipe(
        map(response => {
          localStorage.setItem('accessToken', response.access);
          localStorage.setItem('refreshToken', response.refresh);
          localStorage.setItem('user', JSON.stringify(response.user));
          this.currentUserSubject.next(response.user);
          return response;
        })
      );
  }

  logout(): Observable<any> {
    const refreshToken = localStorage.getItem('refreshToken');
    return this.http.post(`${environment.apiUrl}/auth/logout/`, {
      refresh: refreshToken
    }).pipe(
      map(() => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        this.currentUserSubject.next(null);
      }),
      catchError(error => {
        // Cleanup even if API call fails
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        this.currentUserSubject.next(null);
        return throwError(error);
      })
    );
  }

  getProfile(): Observable<User> {
    return this.http.get<User>(`${environment.apiUrl}/auth/profile/`)
      .pipe(
        map(user => {
          localStorage.setItem('user', JSON.stringify(user));
          this.currentUserSubject.next(user);
          return user;
        })
      );
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('accessToken');
  }
}
```

### 2. HTTP Interceptor

```typescript
// src/app/interceptors/auth.interceptor.ts
import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, filter, take, switchMap } from 'rxjs/operators';
import { AuthService } from '../services/auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  constructor(private authService: AuthService) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const token = localStorage.getItem('accessToken');

    if (token) {
      request = this.addToken(request, token);
    }

    return next.handle(request).pipe(
      catchError(error => {
        if (error instanceof HttpErrorResponse && error.status === 401) {
          return this.handle401Error(request, next);
        }
        return throwError(error);
      })
    );
  }

  private addToken(request: HttpRequest<any>, token: string) {
    return request.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  private handle401Error(request: HttpRequest<any>, next: HttpHandler) {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      const refreshToken = localStorage.getItem('refreshToken');

      if (refreshToken) {
        return this.authService.refreshToken(refreshToken).pipe(
          switchMap((token: any) => {
            this.isRefreshing = false;
            this.refreshTokenSubject.next(token.access);
            return next.handle(this.addToken(request, token.access));
          }),
          catchError((err) => {
            this.isRefreshing = false;
            this.authService.logout();
            return throwError(err);
          })
        );
      }
    }

    return this.refreshTokenSubject.pipe(
      filter(token => token != null),
      take(1),
      switchMap(token => {
        return next.handle(this.addToken(request, token));
      })
    );
  }
}
```

---

## 🔷 Vue.js

### 1. Servicio de Autenticación (Composition API)

```javascript
// src/composables/useAuth.js
import { ref, computed } from 'vue';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Estado global
const user = ref(null);
const loading = ref(false);

// Configurar axios
const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export function useAuth() {
  const isAuthenticated = computed(() => !!user.value);

  const login = async (email, password) => {
    loading.value = true;
    try {
      const response = await api.post('/auth/login/', { email, password });
      const { access, refresh, user: userData } = response.data;
      
      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      localStorage.setItem('user', JSON.stringify(userData));
      
      user.value = userData;
      return userData;
    } finally {
      loading.value = false;
    }
  };

  const register = async (userData) => {
    loading.value = true;
    try {
      const response = await api.post('/auth/register/', userData);
      const { access, refresh, user: newUser } = response.data;
      
      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      localStorage.setItem('user', JSON.stringify(newUser));
      
      user.value = newUser;
      return newUser;
    } finally {
      loading.value = false;
    }
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('refreshToken');
    try {
      await api.post('/auth/logout/', { refresh: refreshToken });
    } finally {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      user.value = null;
    }
  };

  const loadUser = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token) return;

    try {
      const response = await api.get('/auth/profile/');
      user.value = response.data;
    } catch (error) {
      console.error('Error loading user:', error);
      logout();
    }
  };

  return {
    user,
    loading,
    isAuthenticated,
    login,
    register,
    logout,
    loadUser,
  };
}
```

---

## 📱 React Native

```javascript
// src/services/authService.js
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';

const API_BASE_URL = 'http://YOUR_SERVER_IP:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export const authService = {
  async login(email, password) {
    const response = await api.post('/auth/login/', { email, password });
    const { access, refresh, user } = response.data;
    
    await AsyncStorage.setItem('accessToken', access);
    await AsyncStorage.setItem('refreshToken', refresh);
    await AsyncStorage.setItem('user', JSON.stringify(user));
    
    return { access, refresh, user };
  },

  async logout() {
    const refreshToken = await AsyncStorage.getItem('refreshToken');
    
    try {
      await api.post('/auth/logout/', { refresh: refreshToken });
    } finally {
      await AsyncStorage.multiRemove(['accessToken', 'refreshToken', 'user']);
    }
  },

  async isAuthenticated() {
    const token = await AsyncStorage.getItem('accessToken');
    return !!token;
  },
};
```

---

## 🔧 Testing con Jest

```javascript
// __tests__/authService.test.js
import authService from '../services/authService';
import axios from 'axios';

jest.mock('axios');

describe('AuthService', () => {
  afterEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  test('should login successfully', async () => {
    const mockResponse = {
      data: {
        access: 'mock-access-token',
        refresh: 'mock-refresh-token',
        user: { id: 1, email: 'test@example.com' },
      },
    };

    axios.post.mockResolvedValue(mockResponse);

    const result = await authService.login('test@example.com', 'password123');

    expect(result.user.email).toBe('test@example.com');
    expect(localStorage.getItem('accessToken')).toBe('mock-access-token');
  });

  test('should handle login error', async () => {
    axios.post.mockRejectedValue(new Error('Invalid credentials'));

    await expect(
      authService.login('test@example.com', 'wrong-password')
    ).rejects.toThrow('Invalid credentials');
  });
});
```

---

## 📌 Notas Importantes

### CORS en Desarrollo
Asegúrate de que el backend tenga CORS configurado para aceptar requests del frontend:

```python
# config/settings/dev.py
CORS_ALLOW_ALL_ORIGINS = True  # Solo en desarrollo
```

### URLs del API
- **Desarrollo local**: `http://localhost:8000/api`
- **React Native**: `http://TU_IP_LOCAL:8000/api` (no usar localhost)
- **Producción**: `https://tu-dominio.com/api`

### Storage Seguro
- **Web**: LocalStorage (considera HttpOnly cookies para mayor seguridad)
- **React Native**: AsyncStorage o SecureStore
- **Nunca** guardar contraseñas en storage local

### Manejo de Errores
Siempre implementa manejo de errores apropiado para cada framework y muestra mensajes amigables al usuario.

---

Para más detalles, consulta la documentación completa en `docs/authentication-api.md`.
