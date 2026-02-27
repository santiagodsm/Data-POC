import { useRef, useState } from 'react'

const POLL_INTERVAL_MS = 1000
const MAX_POLLS = 30

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

// ---------------------------------------------------------------------------
// Shared result polling logic
// ---------------------------------------------------------------------------
async function pollForResult(run_id, onStatus) {
  for (let i = 0; i < MAX_POLLS; i++) {
    await sleep(POLL_INTERVAL_MS)
    const res  = await fetch(`/profiling/runs/${run_id}`)
    const data = await res.json()
    onStatus(data.status)
    if (data.status === 'done')   return data.result
    if (data.status === 'failed') throw new Error('Profiling job failed on the server')
  }
  throw new Error('Timed out waiting for result')
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
export default function App() {
  // CSV upload section
  const fileRef = useRef(null)
  const [fileName, setFileName]   = useState('')
  const [uploadPhase, setUploadPhase] = useState('idle') // idle | uploading | profiling | done | failed

  // Manual table section
  const [table, setTable]       = useState('')
  const [manualPhase, setManualPhase] = useState('idle')

  // Shared result + error
  const [result,    setResult]    = useState(null)
  const [runId,     setRunId]     = useState(null)
  const [error,     setError]     = useState(null)
  const [pollStatus, setPollStatus] = useState('')

  // ---- CSV upload + auto-profile ----
  async function handleUpload() {
    const file = fileRef.current?.files?.[0]
    if (!file) return

    setUploadPhase('uploading')
    setResult(null)
    setRunId(null)
    setError(null)
    setPollStatus('')

    try {
      // 1. Upload
      const form = new FormData()
      form.append('file', file)
      const up = await fetch('/upload', { method: 'POST', body: form })
      if (!up.ok) {
        const err = await up.json()
        throw new Error(err.detail ?? `Upload failed (${up.status})`)
      }
      const { table: tbl } = await up.json()

      // 2. Kick off profile
      setUploadPhase('profiling')
      const run = await fetch('/profiling/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table: tbl }),
      })
      if (!run.ok) throw new Error(`Profile request failed (${run.status})`)
      const { run_id } = await run.json()
      setRunId(run_id)

      // 3. Poll
      const res = await pollForResult(run_id, setPollStatus)
      setResult(res)
      setUploadPhase('done')
    } catch (err) {
      setError(err.message)
      setUploadPhase('failed')
    }
  }

  // ---- Manual table name ----
  async function handleManualRun() {
    if (!table.trim()) return
    setManualPhase('submitting')
    setResult(null)
    setRunId(null)
    setError(null)
    setPollStatus('')

    try {
      const run = await fetch('/profiling/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table: table.trim() }),
      })
      if (!run.ok) throw new Error(`API error ${run.status}`)
      const { run_id } = await run.json()

      setManualPhase('polling')
      setRunId(run_id)
      const res = await pollForResult(run_id, setPollStatus)
      setResult(res)
      setManualPhase('done')
    } catch (err) {
      setError(err.message)
      setManualPhase('failed')
    }
  }

  const uploadBusy = uploadPhase === 'uploading' || uploadPhase === 'profiling'
  const manualBusy = manualPhase === 'submitting' || manualPhase === 'polling'

  return (
    <div style={s.page}>
      <h1 style={s.title}>Data CoPilot</h1>

      {/* ── Upload CSV ─────────────────────────────────────── */}
      <section style={s.card}>
        <h2 style={s.cardTitle}>Upload a CSV</h2>
        <p style={s.hint}>Uploads the file, creates a Postgres table, and profiles it automatically.</p>

        <div style={s.row}>
          <label style={s.fileLabel}>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? '')}
            />
            <span style={s.fileBtn}>Choose file</span>
            <span style={s.filePath}>{fileName || 'No file selected'}</span>
          </label>

          <button
            style={{ ...s.btn, ...(uploadBusy ? s.btnDisabled : {}) }}
            onClick={handleUpload}
            disabled={uploadBusy || !fileName}
          >
            {uploadPhase === 'uploading' ? 'Uploading…'
             : uploadPhase === 'profiling' ? 'Profiling…'
             : 'Upload & Profile'}
          </button>
        </div>

        {uploadPhase === 'profiling' && (
          <p style={s.hint}>⏳ Worker status: <strong>{pollStatus || 'queued'}</strong></p>
        )}
      </section>

      {/* ── Profile existing table ─────────────────────────── */}
      <section style={s.card}>
        <h2 style={s.cardTitle}>Profile an existing table</h2>
        <p style={s.hint}>Type any table name already in Postgres (e.g. <code>project</code>, <code>artifact</code>).</p>

        <div style={s.row}>
          <input
            style={s.input}
            value={table}
            onChange={(e) => setTable(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !manualBusy && handleManualRun()}
            placeholder="Table name"
            disabled={manualBusy}
          />
          <button
            style={{ ...s.btn, ...(manualBusy ? s.btnDisabled : {}) }}
            onClick={handleManualRun}
            disabled={manualBusy || !table.trim()}
          >
            {manualBusy ? 'Running…' : 'Run Profile'}
          </button>
        </div>

        {manualPhase === 'polling' && (
          <p style={s.hint}>⏳ Worker status: <strong>{pollStatus || 'queued'}</strong></p>
        )}
      </section>

      {/* ── Error ──────────────────────────────────────────── */}
      {error && <p style={s.error}>✗ {error}</p>}

      {/* ── Results ────────────────────────────────────────── */}
      {result && (
        <section style={s.card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ ...s.cardTitle, margin: 0 }}>
              {result.table} — {result.row_count.toLocaleString()} rows
            </h2>
            {runId && (
              <a
                href={`/profiling/runs/${runId}/download`}
                download
                style={s.downloadBtn}
              >
                ↓ Download JSON
              </a>
            )}
          </div>
          <table style={s.table}>
            <thead>
              <tr>
                {['Column', 'Type', 'Null %', 'Distinct'].map((h) => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.columns.map((col) => (
                <tr key={col.name}>
                  <td style={s.td}><code>{col.name}</code></td>
                  <td style={s.td}>{col.type}</td>
                  <td style={s.td}>{col.null_pct}%</td>
                  <td style={s.td}>{col.distinct_count.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------
const s = {
  page:      { fontFamily: 'system-ui, sans-serif', maxWidth: 800, margin: '48px auto', padding: '0 24px', color: '#111' },
  title:     { fontSize: 28, fontWeight: 700, marginBottom: 24 },
  card:      { border: '1px solid #e5e7eb', borderRadius: 10, padding: '20px 24px', marginBottom: 20 },
  cardTitle: { fontSize: 17, fontWeight: 600, margin: '0 0 4px' },
  hint:      { color: '#6b7280', fontSize: 13, margin: '0 0 14px' },
  row:       { display: 'flex', gap: 8, alignItems: 'center' },
  input:     { flex: 1, padding: '9px 13px', fontSize: 14, border: '1px solid #d1d5db', borderRadius: 6, outline: 'none' },
  fileLabel: { flex: 1, display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' },
  fileBtn:   { padding: '9px 14px', fontSize: 14, background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: 6, whiteSpace: 'nowrap' },
  filePath:  { fontSize: 13, color: '#374151', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  btn:       { padding: '9px 20px', fontSize: 14, fontWeight: 600, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', whiteSpace: 'nowrap' },
  btnDisabled: { background: '#93c5fd', cursor: 'not-allowed' },
  error:     { color: '#dc2626', marginTop: 4 },
  table:     { width: '100%', borderCollapse: 'collapse', marginTop: 12 },
  th:        { textAlign: 'left', padding: '8px 12px', background: '#f9fafb', borderBottom: '2px solid #e5e7eb', fontWeight: 600, fontSize: 13 },
  td:          { padding: '8px 12px', borderBottom: '1px solid #f0f0f0', fontSize: 14 },
  downloadBtn: { padding: '7px 14px', fontSize: 13, fontWeight: 600, background: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db', borderRadius: 6, textDecoration: 'none' },
}
