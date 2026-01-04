import { ZgetBase } from './base.js';

export class ZgetPlayer extends ZgetBase {
    constructor() {
        super();
        this.video = null;
    }

    connectedCallback() {
        this.loadStyles();
        this.render();
    }

    open(videoData) {
        this.video = videoData;
        this.render();
        const modal = this.shadowRoot.getElementById('modal');
        modal.style.display = 'flex';
        // Small delay to allow display:flex to apply before opacity transition
        requestAnimationFrame(() => modal.classList.add('visible'));
    }

    close() {
        const modal = this.shadowRoot.getElementById('modal');
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
          background: rgba(0,0,0,0.9);
          backdrop-filter: blur(10px);
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
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          overflow: hidden;
          box-shadow: 0 20px 50px rgba(0,0,0,0.5);
          display: flex;
          flex-direction: column;
        }

        .video-wrapper {
          width: 100%;
          background: #000;
          aspect-ratio: 16/9;
          display: flex;
          justify-content: center;
          align-items: center;
        }

        video {
          width: 100%;
          height: 100%;
          max-height: 70vh;
        }

        .info-bar {
          padding: 20px;
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 20px;
        }

        h2 { margin: 0 0 8px; font-size: 1.2rem; }
        p { margin: 0; color: var(--text-dim); font-size: 0.9rem; }

        .actions {
          display: flex;
          gap: 10px;
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
              <div>
                <h2>${v.title}</h2>
                <p>${v.uploader} • ${v.platform_display}</p>
              </div>
              <div class="actions">
                <button class="btn" onclick="window.open('${v.url}', '_blank')">Original</button>
                <button class="btn primary" onclick="this.getRootNode().host.close()">Close</button>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;
    }
}

customElements.define('zget-player', ZgetPlayer);
