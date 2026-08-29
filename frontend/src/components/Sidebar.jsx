import React from 'react';
import { Activity, FileClock, Workflow, Brackets, Plus, ShieldCheck } from 'lucide-react';

const navigation = [
  { id: 'dashboard', label: 'Dashboard', icon: Activity },
  { id: 'workflow', label: 'Workflow', icon: Workflow },
  { id: 'session-log', label: 'Session Log', icon: FileClock },
  { id: 'api-management', label: 'API Management', icon: Brackets }
];

export default function Sidebar({ activePage, onNavigate, onNewSession }) {
  return (
    <aside className="app-sidebar" aria-label="Primary navigation">
      <div className="sidebar-brand">
        <div className="sidebar-mark"><ShieldCheck size={19} /></div>
        <div>
          <strong>INTEGRITY_OS</strong>
          <span>V2.4.0 ACTIVE</span>
        </div>
      </div>

      <button className="sidebar-new-session" type="button" onClick={onNewSession}>
        <Plus size={16} />
        <span>New Session</span>
      </button>

      <div className="sidebar-section-label">Secure operation</div>
      <nav className="sidebar-nav">
        {navigation.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`sidebar-link ${activePage === id ? 'is-active' : ''}`}
            onClick={() => onNavigate(id)}
            aria-current={activePage === id ? 'page' : undefined}
          >
            <Icon size={17} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="sidebar-status-dot" />
        <span>System active</span>
      </div>
    </aside>
  );
}
