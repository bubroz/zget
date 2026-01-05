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
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: var(--spacing-md) var(--spacing-lg);
                    background: var(--glass-bg);
                    backdrop-filter: blur(var(--glass-blur));
                    border-bottom: 1px solid var(--glass-border);
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    height: 70px;
                }

                .brand {
                    font-size: 1.1rem;
                    font-weight: 600;
                    display: flex;
                    align-items: center;
                    gap: 14px;
                    color: var(--primary-color);
                    letter-spacing: 0.03em;
                }

                .brand img {
                    width: 48px;
                    height: 48px;
                    filter: drop-shadow(0 0 10px var(--primary-color));
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
                    max-width: 600px;
                    margin: 0 40px;
                }

                .settings-toggle {
                    background: transparent;
                    border: none;
                    color: var(--text-muted);
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-left: 10px;
                }

                .settings-toggle:hover {
                    color: var(--text-color);
                }

                /* Active Downloads Banner Area */
                .activity-area {
                    max-width: 1400px;
                    margin: 0 auto;
                }

                /* Main Content Area (Vault) */
                .main-content {
                    max-width: 1300px;
                    margin: 0 auto;
                    padding: 40px 20px;
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
                        flex-direction: column;
                        align-items: center;
                        height: auto;
                        padding: 16px;
                        gap: 16px;
                        position: relative;
                    }

                    .brand {
                        font-size: 1rem;
                        justify-content: center;
                    }

                    .brand img {
                        width: 36px;
                        height: 36px;
                    }

                    .command-center {
                        margin: 0;
                        max-width: 100%;
                        width: 100%;
                        order: 2;
                    }

                    .header-nav {
                        position: absolute;
                        top: 12px;
                        right: 16px;
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
            </style>

            <header class="app-header">
                <div class="brand">
                    <img src="/icon.png" alt="zget" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚡</text></svg>'"">
                </div>
                
                <div class="command-center">
                    <zget-ingest></zget-ingest>
                </div>

                <div class="header-nav">
                    <span class="nav-link active">Vault</span>
                    <button class="settings-toggle" title="Settings">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/>
                            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
                        </svg>
                    </button>
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

        vault.addEventListener('open-video', (e) => {
            player.open(e.detail);
        });

        this.shadowRoot.addEventListener('video-deleted', () => {
            vault.loadVideos();
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
