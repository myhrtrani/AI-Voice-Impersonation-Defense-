import React from 'react';
import { Activity, KeyRound, Server, ShieldCheck } from 'lucide-react';

export default function ApiManagement() {
  return (
    <div className="page-frame">
      <div className="page-heading">
        <div>
          <span className="command-center-label">Connectivity / access control</span>
          <h2 className="command-title">API Management</h2>
          <p className="page-description">Monitor the services that connect VoiceIntegrity to your protected workflows.</p>
        </div>
        <span className="cyber-status"><span className="status-dot" /> ALL SYSTEMS NOMINAL</span>
      </div>

      <div className="api-grid">
        <section className="api-card">
          <div className="api-card-top"><Activity size={18} /><span>Global latency</span></div>
          <strong>12.4 <small>ms</small></strong>
          <p>Within the real-time analysis target.</p>
        </section>
        <section className="api-card">
          <div className="api-card-top"><ShieldCheck size={18} /><span>Service health</span></div>
          <strong>99.98 <small>%</small></strong>
          <div className="api-progress"><span /></div>
          <p>Detection and scoring services available.</p>
        </section>
        <section className="api-card">
          <div className="api-card-top"><Server size={18} /><span>Active endpoints</span></div>
          <strong>03 <small>routes</small></strong>
          <p>Calls, stream, and signaling connected.</p>
        </section>
      </div>

      <section className="api-endpoints">
        <div className="api-card-top"><KeyRound size={18} /><span>Connected services</span></div>
        <div className="endpoint-row"><code>/calls/upload</code><span>Audio replay intake</span><b>ONLINE</b></div>
        <div className="endpoint-row"><code>/calls/{'{session_id}'}/stream</code><span>Live analysis WebSocket</span><b>ONLINE</b></div>
        <div className="endpoint-row"><code>/health</code><span>System readiness probe</span><b>ONLINE</b></div>
      </section>
    </div>
  );
}
