import React from 'react';
import { FileClock, ShieldCheck } from 'lucide-react';

export default function SessionLog({ summaryData, historyData, onStartNew }) {
  const hasSession = Boolean(summaryData);
  const totalChunks = summaryData?.total_chunks || historyData.length || 0;
  const peakRisk = Math.round(summaryData?.peak_risk || 0);

  return (
    <div className="page-frame">
      <div className="page-heading">
        <div>
          <span className="command-center-label">Audit trail / recent activity</span>
          <h2 className="command-title">Session Log</h2>
          <p className="page-description">Review the latest protected voice analysis session.</p>
        </div>
        <FileClock className="page-heading-icon" size={28} />
      </div>

      {hasSession ? (
        <section className="session-log-card">
          <div className="session-log-title"><ShieldCheck size={18} /><span>Latest forensic audit</span><b>COMPLETE</b></div>
          <div className="session-log-metrics">
            <div><span>Peak risk</span><strong>{peakRisk}%</strong></div>
            <div><span>Analyzed chunks</span><strong>{totalChunks}</strong></div>
            <div><span>Window</span><strong>{(totalChunks * 2.5).toFixed(1)}s</strong></div>
          </div>
          <button className="primary-action" type="button" onClick={onStartNew}>Start New Session</button>
        </section>
      ) : (
        <section className="session-log-card empty-log">
          <FileClock size={34} />
          <strong>No completed sessions yet</strong>
          <p>Start a monitored call to create the first forensic audit.</p>
          <button className="primary-action" type="button" onClick={onStartNew}>Open Dashboard</button>
        </section>
      )}
    </div>
  );
}
