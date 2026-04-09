// frontend/src/App.jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { analyzeFile, getHealth } from './api/analyze';
import DriftScore from './components/DriftScore';
import SeverityPanel from './components/SeverityPanel';
import DriftTable from './components/DriftTable';
import EmailBadge from './components/EmailBadge';

// ── Available models ───────────────────────────────────────────────
const MODEL_OPTIONS = [
  { value: '',                 label: '⚡ Auto (Ollama → Gemini)',  group: 'Auto' },
  { value: 'ollama:llama3',   label: '🟣 Llama 3 (Local)',          group: 'Ollama' },
  { value: 'ollama:wizardlm2:7b', label: '🔵 WizardLM 2 7B (Local)', group: 'Ollama' },
  { value: 'gemini',          label: '✨ Gemini 2.0 Flash (Cloud)', group: 'Gemini' },
];

// ── Model Selector component ─────────────────────────────────────
function ModelSelector({ value, onChange }) {
  return (
    <div className="model-selector-wrap">
      <label htmlFor="model-select">🤖 AI Model:</label>
      <select
        id="model-select"
        className="model-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {MODEL_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

const EXAMPLE_TF = `resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
  
  tags = {
    Name = "WebServer"
    Env  = "production"
  }
}

resource "aws_security_group" "web_sg" {
  name = "web-sg"
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}`;

const LOADING_STEPS = [
  '🔍 Parsing infrastructure file...',
  '🔄 Detecting drift patterns...',
  '🤖 Running AI analysis (Ollama)...',
  '📊 Writing to Google Sheets...',
  '✉️  Sending email report...',
];

// ── Navbar ─────────────────────────────────────────────────────
function Navbar({ health }) {
  const overall = health?.overall;
  const ledCls  = overall === 'ok' ? '' : overall === 'partial' ? 'partial' : 'error';
  const ledText  = overall === 'ok' ? 'All systems online' : overall === 'partial' ? 'Partial connectivity' : 'Connecting...';

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="navbar-logo">🛸</div>
        <span>Infra-Pilot</span>
      </div>
      <div className="status-led">
        <div className={`led-dot ${ledCls}`} />
        {ledText}
      </div>
    </nav>
  );
}

// ── Loading overlay ────────────────────────────────────────────
function LoadingCard({ step }) {
  return (
    <div className="glass loading-wrap fade-in">
      <div className="spinner" />
      <div className="loading-text">
        Analyzing your infrastructure
        <span className="loading-step" style={{ display: 'block', marginTop: '0.4rem' }}>
          {step}
        </span>
      </div>
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────
export default function App() {
  const [content, setContent]     = useState('');
  const [fileName, setFileName]   = useState('infra.tf');
  const [email, setEmail]         = useState('');
  const [fileType, setFileType]   = useState('terraform');
  const [model, setModel]         = useState('');

  const [loading, setLoading]     = useState(false);
  const [loadStep, setLoadStep]   = useState(0);
  const [result, setResult]       = useState(null);
  const [error, setError]         = useState(null);

  const [health, setHealth]       = useState(null);

  // Poll health on mount
  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ overall: 'error' }));
    const id = setInterval(() => {
      getHealth().then(setHealth).catch(() => {});
    }, 30000);
    return () => clearInterval(id);
  }, []);

  // Cycle loading steps
  useEffect(() => {
    if (!loading) return;
    const id = setInterval(() => {
      setLoadStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 1800);
    return () => clearInterval(id);
  }, [loading]);

  const handleFileType = (type) => {
    setFileType(type);
    setFileName(type === 'terraform' ? 'infra.tf' : 'manifest.yaml');
  };

  const handleAnalyze = async () => {
    if (!content.trim()) return;
    setError(null);
    setResult(null);
    setLoading(true);
    setLoadStep(0);

    try {
      const data = await analyzeFile({
        content: content.trim(),
        fileName,
        emailRecipients: email ? [email] : [],
        model: model || null,
      });
      setResult(data);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Unknown error';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const loadExample = () => {
    setContent(EXAMPLE_TF);
    setFileType('terraform');
    setFileName('infra.tf');
  };

  // ── File Upload ───────────────────────────────────────────────
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver]   = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);

  const processFile = useCallback((file) => {
    if (!file) return;
    const ext  = file.name.split('.').pop().toLowerCase();
    const type = (ext === 'tf') ? 'terraform' : 'kubernetes';
    setFileType(type);
    setFileName(file.name);
    setUploadedFile(file.name);
    setResult(null);
    setError(null);

    const reader = new FileReader();
    reader.onload = (e) => setContent(e.target.result);
    reader.readAsText(file);
  }, []);

  const handleFileInputChange = (e) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    // Reset so the same file can be re-uploaded if needed
    e.target.value = '';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = ()    => setDragOver(false);

  return (
    <div className="app-bg">
      <Navbar health={health} />

      <main className="main-content">

        {/* Hero */}
        <section className="hero">
          <div className="hero-badge">⚡ B.L.A.S.T. Protocol · A.N.T. Architecture</div>
          <h1>Infrastructure Drift<br />Analyzer</h1>
          <p>Paste your Terraform or Kubernetes file and get instant AI-powered drift analysis, risk scoring, and automated reporting.</p>
        </section>

        {/* File Input */}
        <div className="glass file-input-card">
          <div className="card-label">
            <span>📄</span> File Input
          </div>

          {/* Upload strip + Type toggles */}
          <div className="file-type-toggle">
            <button
              id="btn-terraform"
              className={`toggle-btn ${fileType === 'terraform' ? 'active' : ''}`}
              onClick={() => handleFileType('terraform')}
            >
              🟦 Terraform (.tf)
            </button>
            <button
              id="btn-kubernetes"
              className={`toggle-btn ${fileType === 'kubernetes' ? 'active' : ''}`}
              onClick={() => handleFileType('kubernetes')}
            >
              ☸️ Kubernetes (.yaml)
            </button>
            <button
              id="btn-example"
              className="toggle-btn"
              onClick={loadExample}
              style={{ opacity: 0.7 }}
            >
              Load Example
            </button>

            {/* Hidden real file input */}
            <input
              id="file-upload-input"
              ref={fileInputRef}
              type="file"
              accept=".tf,.yaml,.yml"
              style={{ display: 'none' }}
              onChange={handleFileInputChange}
            />
            <button
              id="btn-upload"
              className="toggle-btn upload-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Upload .tf, .yaml or .yml file"
            >
              📂 Upload File
            </button>
          </div>

          {/* Drop Zone — shown when no content yet */}
          {!content && (
            <div
              id="drop-zone"
              className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
            >
              <span className="drop-icon">📁</span>
              <span className="drop-text">Drop your <code>.tf</code> or <code>.yaml</code> file here</span>
              <span className="drop-sub">or click to browse · max 2 MB</span>
            </div>
          )}

          {/* Uploaded file badge */}
          {uploadedFile && content && (
            <div className="upload-badge">
              <span>📄 {uploadedFile}</span>
              <button
                className="clear-btn"
                onClick={() => { setContent(''); setUploadedFile(null); }}
                title="Clear file"
              >✕</button>
            </div>
          )}

          <textarea
            id="file-content-input"
            className="code-editor"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={
              fileType === 'terraform'
                ? '# Paste your Terraform .tf file here...\nresource "aws_instance" "web" {\n  instance_type = "t2.micro"\n  ...\n}'
                : '# Paste your Kubernetes manifest here...\napiVersion: apps/v1\nkind: Deployment\n...'
            }
            spellCheck={false}
          />

          <div className="editor-footer">
            <div className="editor-footer-top">
              <div className="email-input-wrap">
                <label htmlFor="email-recipient">✉️ Email report to:</label>
                <input
                  id="email-recipient"
                  type="email"
                  className="email-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@gmail.com"
                />
              </div>
              <ModelSelector value={model} onChange={setModel} />
            </div>

            <button
              id="analyze-btn"
              className="analyze-btn"
              onClick={handleAnalyze}
              disabled={loading || !content.trim()}
            >
              {loading ? '⏳ Analyzing...' : '▶ Analyze Drift'}
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="error-banner fade-in">
            <span className="err-icon">⚠️</span>
            <div className="err-msg">
              Analysis failed
              <span className="err-detail">{error}</span>
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && <LoadingCard step={LOADING_STEPS[loadStep]} />}

        {/* Results */}
        {result && !loading && (
          <>
            {/* Score + Severity side by side */}
            <div className="results-grid">
              <DriftScore score={result.drift_score} />
              <SeverityPanel summary={result.summary} />
            </div>

            {/* Drift Events Table */}
            <DriftTable events={result.drift_events} />

            {/* Email Confirmation + Sheet Link */}
            <EmailBadge
              emailSent={result.email_sent}
              recipients={result.email_recipients}
              sheetUrl={result.sheet_url}
            />
          </>
        )}

        {/* Empty / initial state */}
        {!result && !loading && !error && (
          <div className="glass empty-state">
            <span className="state-icon">🛸</span>
            <p>Paste your infrastructure file above and click <strong>Analyze Drift</strong> to get started.</p>
          </div>
        )}

      </main>
    </div>
  );
}
