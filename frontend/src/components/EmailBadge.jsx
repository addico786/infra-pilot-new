// frontend/src/components/EmailBadge.jsx

export default function EmailBadge({ emailSent, recipients = [], sheetUrl }) {
  if (!emailSent && !sheetUrl) return null;

  return (
    <div className="glass email-badge fade-in">
      {emailSent && (
        <>
          <div className="email-icon">✉️</div>
          <div className="email-msg">
            <strong>Report emailed successfully ✅</strong>
            <span>Sent to: {recipients.join(', ')}</span>
          </div>
        </>
      )}

      {sheetUrl && (
        <a
          id="sheet-link"
          href={sheetUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="sheet-link"
        >
          📊 Open Google Sheet ↗
        </a>
      )}
    </div>
  );
}
