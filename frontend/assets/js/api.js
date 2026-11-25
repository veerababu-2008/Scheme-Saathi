/**
 * SchemeSaathi AI — Fetch API Wrapper
 * Handles JSON envelopes ({data, meta, error}) and credentials.
 */

const API_BASE = window.location.origin.includes(':3000') || window.location.origin.includes(':5500')
  ? 'http://127.0.0.1:5000/api/v1'
  : '/api/v1';

class ApiClient {
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
      credentials: options.credentials || 'include',
    };

    if (config.body && typeof config.body === 'object') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      const json = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMsg = json?.error?.message || `Request failed with status ${response.status}`;
        if (!options.silent) {
          window.showToast?.(errorMsg, 'error');
        }
        const err = new Error(errorMsg);
        err.status = response.status;
        err.code = json?.error?.code || 'HTTP_ERROR';
        err.details = json?.error?.details || null;
        throw err;
      }

      return json; // Returns envelope: { data, meta, error: null }
    } catch (err) {
      if (!options.silent && !err.status) {
        window.showToast?.('Network error. Check connection.', 'error');
      }
      throw err;
    }
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'POST', body });
  }

  put(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PUT', body });
  }

  patch(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PATCH', body });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

window.api = new ApiClient();
