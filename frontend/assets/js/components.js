/**
 * SchemeSaathi AI — Shared UI Components & Helpers
 */

// Theme initialization and dark mode toggle
window.initTheme = function() {
  const saved = localStorage.getItem('schemesaathi_theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
};
window.initTheme();

window.toggleDarkMode = function() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('schemesaathi_theme', next);
};

// Toast notifications
window.showToast = function(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
};

// Format rupees in Indian notation
window.formatCurrency = function(amount) {
  if (!amount && amount !== 0) return 'Variable';
  return '₹' + Number(amount).toLocaleString('en-IN');
};

// Render Standard Navbar
window.renderNavbar = function(activePage = '') {
  const header = document.querySelector('.site-header');
  if (!header) return;

  const isAuth = window.auth.isAuthenticated();
  const isAdmin = window.auth.isAdmin();

  header.innerHTML = `
    <div class="container header-inner">
      <a href="/index.html" class="brand">
        <div class="brand-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <div class="brand-title">SchemeSaathi</div>
          <div class="brand-tagline">AI Civic Guidance</div>
        </div>
      </a>

      <ul class="nav-links">
        <li><a href="/index.html" class="nav-link ${activePage === 'home' ? 'active' : ''}" data-i18n="nav_home">Home</a></li>
        <li><a href="/explore.html" class="nav-link ${activePage === 'explore' ? 'active' : ''}" data-i18n="nav_explore">Discover Schemes</a></li>
        <li><a href="/app/compare.html" class="nav-link ${activePage === 'compare' ? 'active' : ''}">Compare</a></li>
        <li><a href="/app/assistant.html" class="nav-link ${activePage === 'assistant' ? 'active' : ''}" data-i18n="nav_saathi">Saathi AI</a></li>
        ${isAuth ? `
          <li><a href="/app/dashboard.html" class="nav-link ${activePage === 'dashboard' ? 'active' : ''}">Dashboard</a></li>
          <li><a href="/app/saved.html" class="nav-link ${activePage === 'saved' ? 'active' : ''}" data-i18n="nav_saved">Saved</a></li>
          <li><a href="/app/checklist.html" class="nav-link ${activePage === 'checklist' ? 'active' : ''}" data-i18n="nav_checklist">Checklist</a></li>
        ` : ''}
        ${isAdmin ? `<li><a href="/admin/dashboard.html" class="nav-link">Admin Portal</a></li>` : ''}
      </ul>

      <div class="header-actions">
        <button onclick="window.toggleDarkMode()" class="btn btn-subtle btn-sm" title="Toggle Dark/Light Mode" aria-label="Toggle theme">
          🌓
        </button>
        <select class="lang-select" aria-label="Language selection">
          <option value="en">English (EN)</option>
          <option value="te">తెలుగు (TE)</option>
          <option value="hi">हिन्दी (HI)</option>
        </select>

        ${isAuth ? `
          <a href="/app/profile.html" class="btn btn-secondary btn-sm" data-i18n="nav_profile">Profile</a>
          <button onclick="window.auth.logout()" class="btn btn-subtle btn-sm" data-i18n="nav_logout">Logout</button>
        ` : `
          <a href="/auth/login.html" class="btn btn-secondary btn-sm" data-i18n="nav_login">Sign In</a>
          <a href="/auth/register.html" class="btn btn-primary btn-sm" data-i18n="nav_register">Get Started</a>
        `}
      </div>
    </div>
  `;

  // Render Mobile Bottom Bar
  let bottomNav = document.querySelector('.mobile-bottom-nav');
  if (!bottomNav) {
    bottomNav = document.createElement('nav');
    bottomNav.className = 'mobile-bottom-nav';
    document.body.appendChild(bottomNav);
  }

  bottomNav.innerHTML = `
    <a href="/index.html" class="bottom-nav-item ${activePage === 'home' ? 'active' : ''}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
      <span>Home</span>
    </a>
    <a href="/explore.html" class="bottom-nav-item ${activePage === 'explore' ? 'active' : ''}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      <span>Discover</span>
    </a>
    <a href="/app/assistant.html" class="bottom-nav-item ${activePage === 'assistant' ? 'active' : ''}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <span>Saathi AI</span>
    </a>
    <a href="${isAuth ? '/app/saved.html' : '/auth/login.html'}" class="bottom-nav-item ${activePage === 'saved' ? 'active' : ''}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>
      <span>Saved</span>
    </a>
    <a href="${isAuth ? '/app/profile.html' : '/auth/login.html'}" class="bottom-nav-item ${activePage === 'profile' ? 'active' : ''}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="7" r="4"/><path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/></svg>
      <span>Profile</span>
    </a>
  `;

  window.i18n.init();
};

// Render Standard Footer
window.renderFooter = function() {
  const footer = document.querySelector('.site-footer');
  if (!footer) return;

  footer.innerHTML = `
    <div class="container">
      <div class="grid grid-cols-1" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 2.5rem; margin-bottom: 2.5rem;">
        <div>
          <div style="font-family: var(--font-display); font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 0.75rem;">SchemeSaathi AI</div>
          <p style="font-size: var(--text-sm); line-height: 1.6; color: #CABDD0; margin-bottom: 1rem;" data-i18n="tagline">The Right Scheme. The Right Guidance. For Every Citizen.</p>
          <div style="font-size: var(--text-xs); color: #B9AEA0;">Independent Civic Technology Initiative.</div>
        </div>
        <div>
          <h4 style="color: #fff; font-size: var(--text-base); margin-bottom: 1rem;">Citizen Services</h4>
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.6rem; font-size: var(--text-sm);">
            <li><a href="/explore.html">Discover Welfare Schemes</a></li>
            <li><a href="/app/assistant.html">Saathi AI Conversational Guide</a></li>
            <li><a href="/app/checklist.html">Document Readiness Checklist</a></li>
            <li><a href="/how-it-works.html">How Eligibility is Evaluated</a></li>
          </ul>
        </div>
        <div>
          <h4 style="color: #fff; font-size: var(--text-base); margin-bottom: 1rem;">Governance & Sources</h4>
          <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.6rem; font-size: var(--text-sm);">
            <li><a href="https://myscheme.gov.in" target="_blank" rel="noopener">myScheme Official Portal ↗</a></li>
            <li><a href="https://egazette.gov.in" target="_blank" rel="noopener">The Gazette of India ↗</a></li>
            <li><a href="/admin/login.html">Administrative Portal</a></li>
          </ul>
        </div>
      </div>

      <div class="disclaimer-banner" style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: var(--radius-md); color: #CABDD0;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div style="font-size: 0.75rem; line-height: 1.5;" data-i18n="disclaimer">
          SchemeSaathi AI is an independent civic-tech portal and is NOT an official government website. Information is verified against official government gazettes and portals.
        </div>
      </div>
    </div>
  `;
};
