// frontend/src/components/DriftTable.jsx

const DRIFT_TYPE_CLS = {
  added:      'pill-added',
  removed:    'pill-removed',
  modified:   'pill-modified',
  deprecated: 'pill-deprecated',
};

const SEV_DOT = {
  critical: '🔴',
  high:     '🟠',
  medium:   '🟡',
  low:      '🟢',
};

function riskColor(score) {
  if (score < 0)  return 'var(--text-muted)';
  if (score >= 7) return 'var(--sev-critical)';
  if (score >= 5) return 'var(--sev-high)';
  if (score >= 3) return 'var(--sev-medium)';
  return 'var(--sev-low)';
}

export default function DriftTable({ events = [] }) {
  if (!events.length) {
    return (
      <div className="glass table-card">
        <div className="empty-state">
          <span className="state-icon">✨</span>
          <p>No drift events detected. Your infrastructure looks clean!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass table-card fade-in">
      <div className="table-header">
        <h2>📊 Drift Events</h2>
        <span className="event-count-badge">{events.length} event{events.length !== 1 ? 's' : ''}</span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="drift-table">
          <thead>
            <tr>
              <th>Resource</th>
              <th>Type</th>
              <th>Severity</th>
              <th>Field Changed</th>
              <th>AI Summary</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {events.map((ev, i) => (
              <tr key={ev.event_id} style={{ animationDelay: `${i * 60}ms` }}>
                <td className="resource-cell">
                  <span className="resource-type">{ev.resource_type}</span>
                  <span className="resource-name">{ev.resource_name}</span>
                </td>
                <td>
                  <span className={`drift-type-pill ${DRIFT_TYPE_CLS[ev.drift_type] || 'pill-modified'}`}>
                    {ev.drift_type}
                  </span>
                </td>
                <td>
                  <span className={`sev-badge ${ev.severity}`}>
                    {SEV_DOT[ev.severity]} {ev.severity}
                  </span>
                </td>
                <td>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {ev.changed_field || '—'}
                  </span>
                </td>
                <td className="ai-summary-cell">
                  <p className="ai-summary-text">{ev.ai_summary}</p>
                  {ev.recommendation && (
                    <p style={{ fontSize: '0.71rem', color: 'var(--text-muted)', marginTop: '0.2rem', fontStyle: 'italic' }}>
                      → {ev.recommendation}
                    </p>
                  )}
                </td>
                <td className="risk-score-cell">
                  <span
                    className="risk-score-num"
                    style={{ color: riskColor(ev.risk_score) }}
                  >
                    {ev.risk_score >= 0 ? ev.risk_score.toFixed(1) : '—'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
