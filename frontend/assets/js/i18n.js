/**
 * SchemeSaathi AI — i18n Translation Runner
 */

class I18nManager {
  constructor() {
    this.currentLang = localStorage.getItem('schemesaathi_lang') || 'en';
  }

  init() {
    this.setLanguage(this.currentLang, false);
    this.bindLanguageSelectors();
  }

  setLanguage(lang, reload = true) {
    if (!['en', 'te', 'hi'].includes(lang)) lang = 'en';
    this.currentLang = lang;
    localStorage.setItem('schemesaathi_lang', lang);
    document.documentElement.lang = lang;
    document.body.setAttribute('lang', lang);

    this.translateDOM();

    // Update any select dropdowns
    document.querySelectorAll('.lang-select').forEach(sel => {
      sel.value = lang;
    });

    if (reload) {
      window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang } }));
    }
  }

  translate(key) {
    const dict = window.TRANSLATIONS[this.currentLang] || window.TRANSLATIONS.en;
    return dict[key] || window.TRANSLATIONS.en[key] || key;
  }

  translateDOM() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const text = this.translate(key);
      if (text) {
        if (el.tagName === 'INPUT' && el.getAttribute('placeholder')) {
          el.placeholder = text;
        } else {
          el.textContent = text;
        }
      }
    });
  }

  bindLanguageSelectors() {
    document.querySelectorAll('.lang-select').forEach(sel => {
      sel.value = this.currentLang;
      sel.addEventListener('change', (e) => {
        this.setLanguage(e.target.value, true);
      });
    });
  }
}

window.i18n = new I18nManager();
window.t = (key) => window.i18n.translate(key);
