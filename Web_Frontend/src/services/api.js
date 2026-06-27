const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token) {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
}

function onRefreshFailed() {
  refreshSubscribers.forEach(cb => cb(null));
  refreshSubscribers = [];
}

const getHeaders = (tokenRequired = true) => {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (tokenRequired) {
    const token = localStorage.getItem('access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  return headers;
};

export const apiRequest = async (path, options = {}) => {
  const { tokenRequired = true, ...fetchOptions } = options;
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${API_BASE_URL}${normalizedPath}`;

  const headers = {
    ...getHeaders(tokenRequired),
    ...fetchOptions.headers
  };

  const config = {
    ...fetchOptions,
    headers
  };

  try {
    let response = await fetch(url, config);

    // Auto-refresh token if 401 Unauthorized
    if (response.status === 401 && tokenRequired) {
      const refreshToken = localStorage.getItem('refresh_token');

      if (!refreshToken) {
        localStorage.removeItem('access_token');
        window.dispatchEvent(new CustomEvent('auth-logout'));
        throw new Error('Session expired. Please log in again.');
      }

      // All 401 callers (including the first) wait in the subscriber queue
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          const refreshRes = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
          });

          if (refreshRes.ok) {
            const data = await refreshRes.json();
            const newAccessToken = data.data?.access_token || data.data?.tokens?.access_token;
            const newRefreshToken = data.data?.refresh_token || data.data?.tokens?.refresh_token;

            if (newAccessToken) {
              localStorage.setItem('access_token', newAccessToken);
            }
            if (newRefreshToken) {
              localStorage.setItem('refresh_token', newRefreshToken);
            }

            isRefreshing = false;
            onRefreshed(newAccessToken || localStorage.getItem('access_token'));
          } else {
            isRefreshing = false;
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            onRefreshFailed();
            window.dispatchEvent(new CustomEvent('auth-logout'));
            throw new Error('Session expired. Please log in again.');
          }
        } catch (refreshErr) {
          isRefreshing = false;
          onRefreshFailed();
          throw refreshErr;
        }
      }

      // Both the original request and any queued requests wait here
      return new Promise((resolve, reject) => {
        subscribeTokenRefresh(async (newToken) => {
          if (!newToken) {
            reject(new Error('Session expired. Please log in again.'));
            return;
          }
          config.headers['Authorization'] = `Bearer ${newToken}`;
          try {
            const retryRes = await fetch(url, config);
            resolve(await handleResponse(retryRes));
          } catch (err) {
            reject(err);
          }
        });
      });
    }

    return await handleResponse(response);
  } catch (error) {
    console.error(`API Error on ${path}:`, error);
    throw error;
  }
};

const handleResponse = async (response) => {
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const errorMsg = data.message || data.msg || `Request failed with status ${response.status}`;
    const error = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    error.field = data.field;
    throw error;
  }

  return data;
};

export default apiRequest;
