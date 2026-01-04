import { ZgetBase } from './base.js';

export class ZgetRegions extends ZgetBase {
    constructor() {
        super();
        this.regions = {};
        this.sites = [];
        this.activeCategory = 'all';
        this.loading = true;
    }

    connectedCallback() {
        this.loadStyles();
        this.renderTemplate();
        this.fetchData();
    }

    async fetchData() {
        this.loading = true;
        this.renderContent();

        try {
            const [regionsRes, sitesRes] = await Promise.all([
                fetch('/api/regions'),
                fetch('/api/uploaders') // Assuming sites came from here or similar endpoint
            ]);

            this.regions = await regionsRes.json();

            // Transform uploader data into site format expected by UI
            // In the old app, this was client-side logic combining regions + uploader statuses
            // We'll reimplement that transformation here
            const rawSites = await sitesRes.json();
            this.sites = rawSites;

        } catch (err) {
            console.error('Failed to fetch regions:', err);
        } finally {
            this.loading = false;
            this.renderContent();
        }
    }

    getRegionSites(regionId) {
        if (!this.sites.length) return [];
        // Filter sites that belong to this region
        // The previous logic had hardcoded mappings or backend data. 
        // For now, we'll assume the API returns a 'region_id' or similar on the uploader object
        // Or we filter based on known region logic.
        // Replicating original filter logic:
        return this.sites.filter(s => s.region === regionId || (!s.region && regionId === 'global'));
    }

    calculateSummary(sites) {
        return {
            working: sites.filter(s => s.status === 'working').length,
            failed: sites.filter(s => s.status === 'broken').length,
            untested: sites.filter(s => s.status === 'untested').length
        };
    }

    renderTemplate() {
        this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        :host { display: block; padding: 20px; }
        
        .regions-header {
          margin-bottom: 30px;
        }

        .region-card {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          margin-bottom: 24px;
          overflow: hidden;
        }

        .region-header {
          padding: 20px;
          background: rgba(255, 255, 255, 0.03);
          border-bottom: 1px solid var(--border);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .region-title {
          font-size: 1.1rem;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .region-content {
          padding: 20px;
        }

        /* Chips */
        .chip-container {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
        }

        .chip {
          font-size: 0.75rem;
          padding: 4px 12px;
          border-radius: 12px;
          border: 1px solid var(--border);
          background: rgba(255,255,255,0.05);
          cursor: pointer;
          transition: all 0.2s;
        }
        .chip.active {
          background: var(--primary);
          color: var(--bg);
          border-color: var(--primary);
        }

        /* Summary Stats */
        .summary-stats {
          font-size: 0.8rem;
          color: var(--text-dim);
          margin-bottom: 16px;
        }

        /* Site Grid */
        .site-grid {
          display: grid;
          gap: 12px;
        }

        .site-row {
          display: flex;
          align-items: center;
          padding: 12px 16px;
          background: rgba(0,0,0,0.2);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          gap: 12px;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }
        .status-dot.working { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .status-dot.broken { background: var(--danger); box-shadow: 0 0 8px var(--danger); }
        .status-dot.untested { background: var(--text-dim); }

        .site-name { font-weight: 600; font-size: 0.9rem; flex: 1; }
        .site-cat { font-size: 0.75rem; color: var(--text-dim); border: 1px solid var(--border); padding: 2px 8px; border-radius: 8px; }

      </style>

      <div class="regions-header">
        <div class="header-title">
          <h2>Regional Sites</h2>
          <p>Global scraper status & availability</p>
        </div>
      </div>

      <div id="regions-container">
        <!-- Injected Content -->
      </div>
    `;
    }

    renderContent() {
        const container = this.shadowRoot.getElementById('regions-container');
        if (!container) return;

        if (this.loading) {
            container.innerHTML = '<div style="text-align:center; padding: 40px; color: var(--text-dim)">Loading Regions...</div>';
            return;
        }

        // Example Mock Data if API fails or is empty for dev
        // In real app, uses this.regions
        const displayRegions = Object.keys(this.regions).length ? this.regions : [
            { id: 'global', name: 'Global / International', icon: '🌍' },
            { id: 'us', name: 'North America', icon: '🇺🇸' },
            { id: 'eu', name: 'European Union', icon: '🇪🇺' },
            { id: 'asia', name: 'Asia Pacific', icon: '🇯🇵' }
        ];

        container.innerHTML = displayRegions.map(region => {
            const sites = this.getRegionSites(region.id);
            const summary = this.calculateSummary(sites);

            return `
        <div class="region-card">
          <div class="region-header">
            <div class="region-title">
              <span style="font-size: 1.4rem">${region.icon || '📍'}</span>
              <span>${region.name}</span>
            </div>
          </div>
          <div class="region-content">
            <div class="summary-stats">
              ${summary.working} working • ${summary.failed} issues • ${summary.untested} untested
            </div>
            
            <div class="site-grid">
               ${sites.length ? sites.map(s => `
                 <div class="site-row">
                   <div class="status-dot ${s.status}"></div>
                   <div class="site-name">${s.name}</div>
                   <div class="site-cat">${s.category || 'General'}</div>
                 </div>
               `).join('') : '<div style="color:var(--text-mute); font-size:0.9rem;">No scrappers configured for this region.</div>'}
            </div>
          </div>
        </div>
      `;
        }).join('');
    }
}

customElements.define('zget-regions', ZgetRegions);
