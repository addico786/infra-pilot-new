// frontend/src/components/DriftScore.jsx
import { useEffect, useRef } from 'react';

const RADIUS = 56;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS; // ≈ 351.86

function getScoreColor(score) {
  if (score >= 7.5) return '#ff4757';
  if (score >= 5)   return '#ffa502';
  return '#2ed573';
}

function getVerdict(score) {
  if (score >= 7.5) return { label: 'Critical Risk', cls: 'verdict-critical' };
  if (score >= 5)   return { label: 'High Risk',     cls: 'verdict-high' };
  if (score >= 2.5) return { label: 'Medium Risk',   cls: 'verdict-medium' };
  return                   { label: 'Low Risk',      cls: 'verdict-low' };
}

export default function DriftScore({ score = 0 }) {
  const fillRef = useRef(null);

  useEffect(() => {
    if (!fillRef.current) return;
    const pct    = Math.min(score / 10, 1);
    const offset = CIRCUMFERENCE * (1 - pct);
    fillRef.current.style.strokeDashoffset = offset;
    fillRef.current.style.stroke = getScoreColor(score);
  }, [score]);

  const verdict = getVerdict(score);

  return (
    <div className="glass score-card fade-in">
      <p className="score-label">Drift Score</p>

      <div className="score-gauge-wrap">
        <svg className="score-svg" viewBox="0 0 140 140">
          <circle className="score-track" cx="70" cy="70" r={RADIUS} />
          <circle
            ref={fillRef}
            className="score-fill"
            cx="70"
            cy="70"
            r={RADIUS}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE}
          />
        </svg>

        <div className="score-number" style={{ color: getScoreColor(score) }}>
          {score.toFixed(1)}
          <span>/ 10</span>
        </div>
      </div>

      <span className={`score-verdict ${verdict.cls}`}>{verdict.label}</span>
    </div>
  );
}
