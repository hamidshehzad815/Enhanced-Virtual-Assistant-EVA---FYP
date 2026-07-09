import React, { createContext, useContext, useState, useEffect } from 'react';
import apiRequest from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errors, setErrors] = useState({});

  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setIsAuthenticated(false);
      setUser(null);
      setIsLoading(false);
      return;
    }
    
    try {
      const response = await apiRequest('/api/auth/me');
      if (response.status === 'success' || response.data) {
        const userData = response.data?.user || response.data || response;
        setUser(userData);
        setIsAuthenticated(true);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
    
    // Listen for global logout events (from API client on refresh expiry)
    const handleLogout = () => {
      logout();
    };
    window.addEventListener('auth-logout', handleLogout);
    return () => window.removeEventListener('auth-logout', handleLogout);
  }, []);

  const login = async (email, password) => {
    setIsLoading(true);
    setErrors({});
    try {
      const response = await apiRequest('/api/auth/login', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify({ email, password }),
      });

      if (response.success || response.status === 'success') {
        const tokens = response.data?.tokens;
        if (tokens) {
          localStorage.setItem('access_token', tokens.access_token);
          localStorage.setItem('refresh_token', tokens.refresh_token);
        }
        
        const userData = response.data?.user || response.data;
        
        if (userData?.is_verified === false) {
          setIsLoading(false);
          return { success: true, isVerified: false, message: 'Email not verified' };
        }

        setUser(userData);
        setIsAuthenticated(true);
        setIsLoading(false);
        return { success: true, isVerified: true };
      }
      
      return { success: false, message: response.message || response.msg || 'Login failed' };
    } catch (err) {
      const field = err.field || (err.data?.field);
      const message = err.message || 'Server not reachable';
      setErrors(field ? { [field]: message } : { general: message });
      setIsLoading(false);
      return { success: false, message };
    }
  };

  const signup = async (userData) => {
    setErrors({});
    try {
      const response = await apiRequest('/api/auth/register', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify(userData),
      });

      if (response.status === 'success' || response.success) {
        return {
          success: true,
          emailSent: response.data?.email_sent ?? true,
          message: response.message || 'Registration successful. Please verify your email.',
        };
      }
      return { success: false, message: response.message || 'Signup failed' };
    } catch (err) {
      const field = err.field || err.data?.field;
      const message = err.message || 'Server not reachable';
      if (field) setErrors({ [field]: message });
      return { success: false, message };
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await apiRequest('/api/auth/logout', { method: 'POST' });
    } catch (err) {
      console.error('Logout API call failed:', err);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
      setIsAuthenticated(false);
      setIsLoading(false);
    }
  };

  const updateProfile = async (profileData) => {
    setErrors({});
    try {
      const response = await apiRequest('/api/profile', {
        method: 'PATCH',
        body: JSON.stringify(profileData),
      });
      if (response.status === 'success') {
        const updatedUser = response.data?.user || response.data || response;
        setUser(prev => ({ ...prev, ...updatedUser }));
        return { success: true };
      }
      return { success: false, message: response.message || 'Update failed' };
    } catch (err) {
      const field = err.field || (err.data?.field);
      const message = err.message || 'Failed to update profile';
      setErrors(field ? { [field]: message } : { general: message });
      return { success: false, message };
    }
  };

  const forgotPassword = async (email) => {
    try {
      const response = await apiRequest('/api/auth/forgot-password', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify({ email }),
      });
      return { success: response.status === 'success' || response.success, message: response.message };
    } catch (err) {
      return { success: false, message: err.message || 'Failed to send reset link' };
    }
  };

  const resetPassword = async (token, new_password, confirm_password) => {
    try {
      const response = await apiRequest('/api/auth/reset-password', {
        method: 'POST',
        tokenRequired: false,
        body: JSON.stringify({ token, new_password, confirm_password }),
      });
      return { success: response.status === 'success' || response.success, message: response.message };
    } catch (err) {
      return { success: false, message: err.message || 'Failed to reset password' };
    }
  };

  const verifyEmailApi = async (token) => {
    try {
      const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
      const url = `${baseUrl}/api/auth/verify-email?token=${encodeURIComponent(token)}`;
      const response = await fetch(url, {
        method: 'GET',
      });
      if (response.ok) {
        return { success: true, message: 'Your email has been successfully verified. You can now log in.' };
      } else {
        try {
          const text = await response.text();
          const data = JSON.parse(text);
          return { success: false, message: data.message || data.msg || 'Verification failed' };
        } catch {
          return { success: false, message: 'This verification link is invalid or has expired.' };
        }
      }
    } catch (err) {
      return { success: false, message: err.message || 'Server not reachable' };
    }
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, errors, login, signup, logout, checkAuth, updateProfile, forgotPassword, resetPassword, verifyEmailApi }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
