import { ZgetBase } from './base.js';
import './vault.js';
import './player.js';

// Simple Router Shell
export class ZgetApp extends ZgetBase {
    constructor() {
        super();
        this.currentView = 'vault';
    }

    connectedCallback() {
        this.loadStyles();
        this.renderTemplate();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Listen for navigation events
        this.shadowRoot.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchView(e.target.dataset.view);
            });
        });

        // Listen for video open events from children
        this.shadowRoot.addEventListener('open-video', (e) => {
            this.openVideo(e.detail.id);
        });
    }

    switchView(viewName) {
        this.currentView = viewName;

        // Update active nav state
        this.shadowRoot.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.view === viewName);
        });

        // Show/Hide views (simple v1 router)
        const vault = this.shadowRoot.getElementById('view-vault');
        const regions = this.shadowRoot.getElementById('view-regions');

        if (viewName === 'vault') {
            vault.style.display = 'block';
            regions.style.display = 'none';
            if (vault.updateList) vault.updateList(); // Refresh data
        } else {
            vault.style.display = 'none';
            regions.style.display = 'block';
            regions.innerHTML = '<div style="padding:40px; text-align:center;">Regions Component Coming Soon...</div>';
        }
    }

    async openVideo(id) {
        try {
            const res = await fetch(`/api/library?q=&limit=1`); // In real app, api/video/id
            // For now, we fetch the library to find the right object or refetch specific
            // Optimally we'd have a get_video endpoint, or pass the full object in the event
            // Hack: we'll just fetch specific video data
            const videoRes = await fetch(`/api/library`);
            const videos = await videoRes.json();
            const video = videos.find(v => v.id === id);

            const player = this.shadowRoot.querySelector('zget-player');
            if (video) player.open(video);
        } catch (e) {
            console.error(e);
        }
    }

    renderTemplate() {
        this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        :host { display: block; min-height: 100vh; background: var(--bg); }
        
        /* App Header */
        header {
          position: sticky;
          top: 0;
          z-index: 100;
          background: rgba(10, 6, 18, 0.8);
          backdrop-filter: blur(12px);
          border-bottom: 1px solid var(--border);
          padding: 16px 24px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .brand {
          font-weight: 700;
          font-size: 1.2rem;
          color: var(--primary);
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .brand span { color: var(--text-main); font-weight: 400; }

        .nav-links {
          display: flex;
          gap: 8px;
          background: rgba(255,255,255,0.05);
          padding: 4px;
          border-radius: var(--radius-round);
        }

        .nav-link {
          padding: 6px 16px;
          border-radius: var(--radius-round);
          color: var(--text-dim);
          text-decoration: none;
          font-size: 0.9rem;
          font-weight: 500;
          transition: all 0.2s;
          cursor: pointer;
        }

        .nav-link:hover { color: var(--text-main); background: rgba(255,255,255,0.05); }
        .nav-link.active {
          background: var(--surface);
          color: var(--primary);
          box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }

        .status-bar {
          display: flex;
          gap: 16px;
          font-size: 0.8rem;
          color: var(--text-dim);
        }

        /* Main Content */
        main {
          max-width: 1400px;
          margin: 0 auto;
          padding: 24px;
        }
      </style>

      <header>
        <div class="brand">
          ⚡ zget <span>Portal</span>
        </div>

        <nav class="nav-links">
          <a class="nav-link active" data-view="vault">Vault</a>
          <a class="nav-link" data-view="regions">Regions</a>
        </nav>

        <div class="status-bar">
          <span>Ready</span>
          <span style="color: var(--success)">● Online</span>
        </div>
      </header>

      <main>
        <div id="view-vault">
          <zget-vault></zget-vault>
        </div>
        <div id="view-regions" style="display: none;">
          <!-- Regions comp loaded here -->
        </div>
      </main>

      <zget-player></zget-player>
    `;
    }
}

customElements.define('zget-app', ZgetApp);
