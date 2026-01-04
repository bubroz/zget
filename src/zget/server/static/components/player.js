import { ZgetBase } from './base.js';

export class ZgetPlayer extends ZgetBase {
  constructor() {
    super();
    this.video = null;
    this.loading = false;
  }

  connectedCallback() {
    this.loadStyles();
    this.render();
  }

  async deleteVideo() {
    if (!this.video || !confirm(`Permanently delete "${this.video.title || 'this video'}"?`)) return;

    try {
      const res = await fetch(`/api/media/${this.video.id}`, { method: 'DELETE' });
      if (res.ok) {
        this.close();
        // Emit refresh event
        this.dispatchEvent(new CustomEvent('video-deleted', { bubbles: true, composed: true }));
      }
    } catch (e) {
      alert('Delete failed.');
    }
  }

  async downloadVideo() {
    if (!this.video) return;
    const link = document.createElement('a');
    const slug = this.video.title ? this.video.title.toLowerCase().replace(/[^\w\s-]/g, '').replace(/[\s_]+/g, '_').substring(0, 100) : this.video.id;
    link.href = `/api/media/${this.video.id}?download=1`;
    link.download = `${slug}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  }

  formatViews(count) {
    if (!count) return '';
    if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M views';
    if (count >= 1000) return (count / 1000).toFixed(1) + 'K views';
    return count + ' views';
  }

  async open(initialData) {
    console.log("[Player] Opening with:", initialData);
    // Show modal loading state immediately
    this.loading = true;
    this.video = initialData; // might be partial
    this.render();

    // Animate in
    const modal = this.shadowRoot.getElementById('modal');
    if (modal) {
      modal.style.display = 'flex';
      requestAnimationFrame(() => modal.classList.add('visible'));
    }

    // Fetch full details if we only have an ID or to ensure freshness
    try {
      const videoId = initialData.id;
      if (!videoId) throw new Error("No video ID provided");

      const res = await fetch(`/api/video/${videoId}`);
      if (!res.ok) throw new Error('Video not found');
      const fullData = await res.json();
      console.log("[Player] Fetched full data:", fullData);
      this.video = fullData;
    } catch (e) {
      console.error("[Player] Failed to load details:", e);
      // Fallback: use initialData but ensure title/uploader aren't missing
      if (!this.video || !this.video.title) {
        this.video = { ...initialData, title: initialData.title || 'Unknown Video', uploader: initialData.uploader || 'Unknown' };
      }
    } finally {
      this.loading = false;
      this.render();
      // Re-apply visible class because render nuked the DOM
      const newModal = this.shadowRoot.getElementById('modal');
      if (newModal) {
        newModal.style.display = 'flex';
        newModal.classList.add('visible');
      }
    }
  }

  close() {
    const modal = this.shadowRoot.getElementById('modal');
    if (!modal) return;

    modal.classList.remove('visible');
    setTimeout(() => {
      modal.style.display = 'none';
      this.video = null;
      this.render(); // Clear video element to stop playback
    }, 200);
  }

  render() {
    const v = this.video;

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/styles/theme.css">
      <link rel="stylesheet" href="/styles/shared.css">
      <style>
        .modal-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.92);
          backdrop-filter: blur(14px);
          z-index: 1000;
          display: none;
          justify-content: center;
          align-items: center;
          opacity: 0;
          transition: opacity 0.2s ease;
        }
        
        .modal-overlay.visible { opacity: 1; }

        .modal-content {
          width: 90%;
          max-width: 1000px;
          background: #0B0E14;
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          overflow: hidden;
          box-shadow: 0 25px 50px -12px rgba(0,0,0,0.7);
          display: flex;
          flex-direction: column;
          max-height: 90vh;
          position: relative;
        }

        .video-wrapper {
          width: 100%;
          background: #000;
          position: relative;
          flex: 0 0 auto;
          aspect-ratio: 16/9;
          display: flex;
          justify-content: center;
          align-items: center;
        }

        video {
          width: 100%;
          height: 100%;
          max-height: 70vh;
          object-fit: contain;
        }

        .info-bar {
          padding: 24px;
          border-top: 1px solid var(--border-color);
          background: #0B0E14;
          display: flex;
          flex-direction: column;
          gap: 20px;
          flex: 1;
          overflow-y: auto;
        }

        .meta-header {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        h2 { 
            margin: 0; 
            font-size: 1.25rem; 
            font-weight: 600; 
            color: var(--text-color);
            line-height: 1.4;
        }
        
        .meta-row { 
            margin: 0; 
            color: var(--text-muted); 
            font-size: 0.85rem; 
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .bullet { opacity: 0.3; }

        .tag {
            background: rgba(255,255,255,0.05);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            border: 1px solid var(--border-color);
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.05em;
        }

        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: auto;
          padding-top: 20px;
          border-top: 1px solid rgba(255,255,255,0.05);
        }

        @media (max-width: 768px) {
          .modal-content {
            width: 100%;
            height: 100%;
            max-height: 100vh;
            border-radius: 0;
            border: none;
          }

          .info-bar {
            padding: 20px;
          }

          .actions {
            position: sticky;
            bottom: 0;
            background: #0B0E14;
            padding-bottom: env(safe-area-inset-bottom, 20px);
          }

          .actions .btn {
            flex: 1;
            padding: 12px;
            justify-content: center;
          }

          .actions .btn.close-btn {
            order: -1;
            width: 100%;
            flex: none;
          }
        }
        
        .loading-title {
            height: 24px;
            width: 60%;
            background: rgba(255,255,255,0.05);
            border-radius: 4px;
            margin-bottom: 8px;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.5; }
            50% { opacity: 0.8; }
            100% { opacity: 0.5; }
        }
      </style>

      <div class="modal-overlay" id="modal" onclick="if(event.target === this) this.getRootNode().host.close()">
        ${v ? `
          <div class="modal-content">
            <div class="video-wrapper">
              <video controls autoplay>
                <source src="/api/media/${v.id}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
            </div>
            
            <div class="info-bar">
              <div class="meta-header">
                ${this.loading ? `
                    <div class="loading-title"></div> 
                    <p>Loading details...</p>
                ` : `
                    <h2>${v.title || 'Untitled Archive'}</h2>
                    <div class="meta-row">
                        <span class="tag" style="background: var(--primary-color); border: none; color: white;">${v.platform_display || (v.platform ? v.platform.toUpperCase() : 'WEB')}</span>
                        <span style="font-weight: 600; color: var(--text-color);">${v.uploader || 'Creator Unknown'}</span>
                        <span class="bullet">•</span>
                        <span>${this.formatDate(v.upload_date)}</span>
                    </div>
                    ${v.view_count || v.resolution ? `
                        <div class="meta-row" style="opacity: 0.5; font-size: 0.75rem; gap: 12px; margin-top: -8px;">
                            ${v.view_count ? `<span>${this.formatViews(v.view_count)}</span>` : ''}
                            ${v.view_count && v.resolution ? '<span class="bullet" style="opacity: 0.2;">|</span>' : ''}
                            ${v.resolution ? `<span>${v.resolution}</span>` : ''}
                            ${(v.view_count || v.resolution) && v.codec ? '<span class="bullet" style="opacity: 0.2;">|</span>' : ''}
                            ${v.codec ? `<span>${v.codec.toUpperCase()}</span>` : ''}
                        </div>
                    ` : ''}
                `}
              </div>
              
              <div class="actions">
                ${!this.loading ? `
                    <button class="btn" style="color: #ef4444; border-color: rgba(239,68,68, 0.2);" onclick="this.getRootNode().host.deleteVideo()">
                        Delete
                    </button>
                    <button class="btn" onclick="window.open('${v.url || '#'}', '_blank')">Source</button>
                    <button class="btn primary" onclick="this.getRootNode().host.downloadVideo()">Download</button>
                ` : ''}
                <button class="btn close-btn" onclick="this.getRootNode().host.close()">Close</button>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }
}

customElements.define('zget-player', ZgetPlayer);
