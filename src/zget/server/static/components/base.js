/**
 * Base Component for zget
 * Handles Shadow DOM attachment and StyleSheet adoption.
 */
export class ZgetBase extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  async loadStyles() {
    // In a real buildless setup, we might fetch CSS text or use import assertions.
    // For now, we'll link to the shared files to ensure hot-reload and browser caching work nicely.
    // Constructable Stylesheets are great, but <link> inside Shadow DOM is roughly equivalent
    // and easier to manage without a bundler for external CSS files.
    
    const linkTheme = document.createElement('link');
    linkTheme.rel = 'stylesheet';
    linkTheme.href = '/styles/theme.css';

    const linkShared = document.createElement('link');
    linkShared.rel = 'stylesheet';
    linkShared.href = '/styles/shared.css';

    this.shadowRoot.appendChild(linkTheme);
    this.shadowRoot.appendChild(linkShared);
  }

  /**
   * Helper to dispatch events that bubble up
   * @param {string} name - Event name
   * @param {any} detail - Event payload
   */
  emit(name, detail = {}) {
    this.dispatchEvent(new CustomEvent(name, {
      detail,
      bubbles: true,
      composed: true
    }));
  }

  /**
   * Simple render helper
   * @param {string} html - Template string
   */
  render(html) {
    // Preserve style links
    const styles = Array.from(this.shadowRoot.querySelectorAll('link'));
    this.shadowRoot.innerHTML = html;
    styles.forEach(link => this.shadowRoot.appendChild(link));
  }
}
