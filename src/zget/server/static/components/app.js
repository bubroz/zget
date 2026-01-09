import './base.js';
import './vault.js';
import './player.js';
import './settings.js';
import './activity.js';
import './ingest.js';

export class ZgetApp extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    connectedCallback() {
        this.render();
        this.setupListeners();
    }

    render() {
        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    min-height: 100vh;
                    background-color: var(--bg-color);
                    color: var(--text-color);
                    font-family: var(--font-family);
                }

                /* Header with Glassmorphism */
                .app-header {
                    background: var(--glass-bg);
                    backdrop-filter: blur(var(--glass-blur));
                    border-bottom: 1px solid var(--glass-border);
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    height: 64px;
                    width: 100%;
                }

                .header-inner {
                    max-width: 1400px;
                    margin: 0 auto;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 40px;
                    gap: 32px;
                }

                .brand {
                    font-family: var(--font-mono);
                    font-size: 1.6rem;
                    font-weight: 800;
                    display: flex;
                    align-items: center;
                    color: var(--primary-color);
                    letter-spacing: 0.15em;
                    text-transform: uppercase;
                    /* Radiant Solar Glow */
                    text-shadow: 0 0 10px hsla(var(--primary-hsl), 0.6),
                                 0 0 20px hsla(var(--primary-hsl), 0.4),
                                 0 0 40px hsla(var(--primary-hsl), 0.2);
                    position: relative;
                    user-select: none;
                    transition: all 0.3s ease;
                }

                .brand:hover {
                    text-shadow: 0 0 15px hsla(var(--primary-hsl), 0.8),
                                 0 0 30px hsla(var(--primary-hsl), 0.6),
                                 0 0 60px hsla(var(--primary-hsl), 0.4);
                    transform: scale(1.02);
                }

                /* Removing legacy underline/sublabel pseudo-element */
                .brand::after {
                    content: none;
                }

                .header-nav {
                    display: flex;
                    align-items: center;
                    gap: 20px;
                }

                .nav-link {
                    font-size: 0.75rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    cursor: pointer;
                    color: var(--text-muted);
                    transition: color 0.2s;
                }

                .nav-link.active {
                    color: var(--primary-color);
                }

                .nav-link.disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .command-center {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    max-width: 100%;
                }

                .header-search { display: none; }

                .system-status {
                    font-family: var(--font-mono);
                    font-size: 0.7rem;
                    color: var(--text-muted);
                    letter-spacing: 0.1em;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    padding-right: 12px;
                    border-right: 1px solid var(--glass-border);
                    white-space: nowrap;
                    user-select: none;
                }

                .system-status .count {
                    color: var(--primary-color);
                    font-weight: 700;
                }

                .settings-toggle {
                    background: transparent;
                    border: none;
                    color: var(--primary-color);
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-left: 10px;
                    transition: all 0.3s ease;
                }

                .settings-toggle:hover {
                    color: var(--primary-color);
                    filter: drop-shadow(0 0 8px hsla(var(--primary-hsl), 0.4));
                    transform: rotate(30deg) scale(1.1);
                }

                /* Active Downloads Banner Area */
                .activity-area {
                    max-width: 1400px;
                    margin: 0 auto;
                }

                /* Main Content Area (Vault) */
                .main-content {
                    max-width: 1400px;
                    margin: 0 auto;
                    /* Total padding needs to match header (40px)
                       app padding (0) + vault host padding (40px) = 40px
                       We'll remove padding here and let vault handle it for cleaner alignment control */
                    padding: 40px 0;
                }

                /* Settings Modal Container */
                .settings-overlay {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.6);
                    z-index: 1000;
                    align-items: center;
                    justify-content: center;
                    backdrop-filter: blur(4px);
                    opacity: 0;
                    transition: opacity 0.2s;
                }

                .settings-overlay.open {
                    display: flex;
                    opacity: 1;
                }

                .settings-container {
                    background: var(--bg-color);
                    border: 1px solid var(--border-color);
                    border-radius: var(--radius-lg);
                    padding: 32px;
                    width: 90%;
                    max-width: 800px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                    position: relative;
                    transform: translateY(10px);
                    transition: transform 0.2s;
                }

                .settings-overlay.open .settings-container {
                    transform: translateY(0);
                }

                .close-settings {
                    position: absolute;
                    top: var(--spacing-md);
                    right: var(--spacing-md);
                    background: none;
                    border: none;
                    color: var(--text-muted);
                    cursor: pointer;
                    font-size: 1.1rem;
                    padding: 8px;
                    border-radius: var(--radius-sm);
                    line-height: 1;
                }
                
                .close-settings:hover {
                    background: rgba(255,255,255,0.1);
                    color: var(--text-color);
                }

                /* Mobile Responsive */
                @media (max-width: 768px) {
                    .app-header {
                        height: auto;
                        position: sticky;
                        top: 0;
                    }

                    .header-inner {
                        flex-direction: column;
                        padding: 16px;
                        gap: 12px;
                        align-items: stretch;
                        height: auto;
                    }

                    .brand {
                        font-size: 1.2rem;
                        justify-content: center;
                    }

                    .command-center {
                        margin: 0;
                        max-width: 100%;
                        width: 100%;
                        order: 2;
                    }

                    .header-nav {
                        position: static;
                        justify-content: center;
                        border-top: 1px solid var(--glass-border);
                        padding-top: 12px;
                        margin-top: 4px;
                        order: 3;
                    }

                    .system-status {
                        border-right: none;
                        padding-right: 0;
                    }

                    .header-nav .nav-link {
                        display: none;
                    }

                    .settings-container {
                        width: 95%;
                        max-width: 95%;
                        padding: 20px;
                        max-height: 85vh;
                        overflow-y: auto;
                    }

                    .main-content {
                        padding: 16px;
                    }
                }

                /* Desktop Polish (large screens) */
                @media (min-width: 1024px) {
                    .app-header {
                        /* Removed conflicting padding */
                    }
                    
                    .command-center {
                        max-width: 520px;
                    }
                    
                    .brand {
                        min-width: 80px;
                    }
                    
                    .header-nav {
                        min-width: 100px;
                        justify-content: flex-end;
                    }
                }
            </style>

            <header class="app-header">
                <div class="header-inner">
                    <div class="brand">
                        zget
                    </div>
                    
                    <div class="command-center">
                        <zget-ingest style="flex: 1;"></zget-ingest>
                    </div>

                    <div class="header-nav">
                        <div class="system-status">
                            INDEX // <span class="count" id="headerCount">--</span>
                        </div>
                        <button class="settings-toggle" title="Settings">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/>
                                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </header>

            <div class="activity-area">
                <zget-activity mode="banner"></zget-activity>
            </div>

            <main class="main-content">
                <zget-vault></zget-vault>
            </main>

            <div class="settings-overlay">
                <div class="settings-container">
                    <button class="close-settings" title="Close">✕</button>
                    <zget-settings mode="modal"></zget-settings>
                </div>
            </div>

            <zget-player></zget-player>
        `;
    }

    setupListeners() {
        const vault = this.shadowRoot.querySelector('zget-vault');
        const player = this.shadowRoot.querySelector('zget-player');
        const overlay = this.shadowRoot.querySelector('.settings-overlay');
        const settingsBtn = this.shadowRoot.querySelector('.settings-toggle');
        const closeSettingsBtn = this.shadowRoot.querySelector('.close-settings');

        const headerCount = this.shadowRoot.getElementById('headerCount');

        vault.addEventListener('open-video', (e) => {
            player.open(e.detail);
        });

        this.addEventListener('library-updated', (e) => {
            if (headerCount) headerCount.textContent = e.detail.count;
        });

        this.addEventListener('archive-complete', () => {
            vault.fetchVideos();
        });

        this.shadowRoot.addEventListener('video-deleted', () => {
            vault.fetchVideos();
        });

        settingsBtn.addEventListener('click', () => {
            overlay.classList.add('open');
        });

        const closeSettings = () => {
            overlay.classList.remove('open');
            // Refresh settings in case they changed things that affect other components?
        };

        closeSettingsBtn.addEventListener('click', closeSettings);

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeSettings();
            }
        });
    }
}

customElements.define('zget-app', ZgetApp);
