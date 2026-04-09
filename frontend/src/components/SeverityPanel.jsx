// frontend/src/components/SeverityPanel.jsx
import { useEffect, useRef } from 'react';

const ROWS = [
  { key: 'critical', label: 'Critical', icon: '🔴', cls: 'critical' },
  { key: 'high',     label: 'High',     icon: '🟠', cls: 'high' },
  { key: 'medium',   label: 'Medium',   icon: '🟡', cls: 'medium' },
  { key: 'low',      label: 'Low',      icon: '🟢', cls: 'low' },
];

export default function SeverityPanel({ summary }) {
  const total = summary?.total || 1;
  const barRefs = useRef({});

  useEffect(() => {
    ROWS.forEach(({ key }, i) => {
      const el = barRefs.current[key];
      if (!el) return;
      const count = summary?.[key] || 0;
      const pct   = Math.round((count / total) * 100);
      setTimeout(() => {
        el.style.width = `${pct}%`;
      }, 100 + i * 120);
    });
  }, [summary, total]);

  return (
    <div className="glass severity-card fade-in">
      <p className="section-title">Severity Breakdown</p>

      {ROWS.map(({ key, label, icon, cls }) => {
        const count = summary?.[key] || 0;
        return (
          <div key={key} className="severity-row">
            <span className="sev-icon">{icon}</span>
            <span className="sev-name">{label}</span>
            <div className="sev-bar-wrap">
              <div
                className={`sev-bar ${cls}`}
                ref={(el) => (barRefs.current[key] = el)}
              />
            </div>
            <span className="sev-count">{count}</span>
          </div>
        );
      })}

      <p className="severity-total">{total} drift event{total !== 1 ? 's' : ''} total</p>
    </div>
  );
}
