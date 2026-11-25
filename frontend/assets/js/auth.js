/**
 * SchemeSaathi AI — Auth State Manager
 */

class AuthManager {
  constructor() {
    this.USER_KEY = 'schemesaathi_user';
    this.ADMIN_KEY = 'schemesaathi_admin';
  }

  getUser() {
    const raw = localStorage.getItem(this.USER_KEY);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  setUser(user) {
    if (user) {
      localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(this.USER_KEY);
    }
  }

  getAdmin() {
    const raw = localStorage.getItem(this.ADMIN_KEY);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  setAdmin(admin) {
    if (admin) {
      localStorage.setItem(this.ADMIN_KEY, JSON.stringify(admin));
    } else {
      localStorage.removeItem(this.ADMIN_KEY);
    }
  }

  isAuthenticated() {
    return !!this.getUser();
  }

  isAdmin() {
    return !!this.getAdmin();
  }

  async login(email, password) {
    const res = await window.api.post('/auth/login', { email, password });
    this.setUser(res.data);
    return res.data;
  }

  async register(email, password, full_name) {
    const res = await window.api.post('/auth/register', { email, password, full_name });
    this.setUser(res.data);
    return res.data;
  }

  async logout() {
    try {
      await window.api.post('/auth/logout', {}, { silent: true });
    } catch {
      // Ignored if session already expired
    }
    this.setUser(null);
    window.location.href = '/index.html';
  }

  async adminLogin(email, password) {
    const res = await window.api.post('/admin/login', { email, password });
    this.setAdmin(res.data.admin);
    return res.data.admin;
  }

  adminLogout() {
    this.setAdmin(null);
    window.location.href = '/admin/login.html';
  }

  requireAuth(redirectUrl = '/auth/login.html') {
    if (!this.isAuthenticated()) {
      window.location.href = `${redirectUrl}?redirect=${encodeURIComponent(window.location.pathname)}`;
    }
  }

  requireAdmin(redirectUrl = '/admin/login.html') {
    if (!this.isAdmin()) {
      window.location.href = redirectUrl;
    }
  }
}

window.auth = new AuthManager();
