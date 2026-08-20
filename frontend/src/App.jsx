import React, { useEffect, useRef, useState } from 'react'
import { API_BASE } from './config'

function formatMetricValue(value) {
  if (value === null || value === undefined) {
    return 'N/A'
  }
  return value.toString()
}

function formatCurrency(value) {
  if (value === null || value === undefined) {
    return 'N/A'
  }

  const number = Number(value)

  if (!Number.isFinite(number)) {
    return 'N/A'
  }

  return `$${number.toFixed(6).replace(/0+$/, '').replace(/\.$/, '')}`
}

function formatDuration(value) {
  if (value === null || value === undefined) {
    return 'N/A'
  }

  const number = Number(value)

  if (!Number.isFinite(number)) {
    return 'N/A'
  }

  if (number < 1000) {
    return `${number} ms`
  }

  const seconds = number / 1000
  return `${seconds.toFixed(seconds >= 10 ? 0 : 1)} s`
}

function formatDisplayFilename(filename, maxLength = 40) {
  if (!filename) {
    return ''
  }

  if (filename.length <= maxLength) {
    return filename
  }

  const dotIndex = filename.lastIndexOf('.')
  let extension = ''
  let stem = filename

  if (dotIndex > 0 && dotIndex < filename.length - 1) {
    extension = filename.slice(dotIndex)
    stem = filename.slice(0, dotIndex)
  }

  const available = maxLength - extension.length - 1

  if (available <= 12) {
    return `${filename.slice(0, maxLength - 1)}…`
  }

  const startLength = Math.max(10, Math.floor(available * 0.6))
  const endLength = Math.max(8, available - startLength)

  return `${stem.slice(0, startLength)}…${stem.slice(-endLength)}${extension}`
}

function getStatusTone(status) {
  const normalized = (status || '').toLowerCase()

  if (['completed', 'approved', 'resolved', 'clean'].includes(normalized)) {
    return 'success'
  }

  if (
    [
      'waiting_for_review',
      'pending_review',
      'in_progress',
      'running',
      'review',
    ].includes(normalized)
  ) {
    return 'warning'
  }

  if (['failed', 'error', 'rejected'].includes(normalized)) {
    return 'error'
  }

  return 'neutral'
}

function formatStatusLabel(status) {
  const normalized = (status || '').toLowerCase()

  if (normalized === 'waiting_for_review') return 'Waiting for review'
  if (normalized === 'completed') return 'Completed'
  if (normalized === 'running') return 'Running'
  if (normalized === 'failed') return 'Failed'
  if (normalized === 'clean') return 'Clean'
  if (normalized === 'pending_review') return 'Pending review'
  if (normalized === 'ready') return 'Ready'

  return status || 'Unknown'
}

function StatusBadge({ status }) {
  const tone = getStatusTone(status)

  return (
    <span className={`status-pill status-${tone}`}>
      {formatStatusLabel(status)}
    </span>
  )
}

function IconDocument() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm7 1.5V8h3.5L14 4.5Z" />
    </svg>
  )
}

function IconUpload() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 4a1 1 0 0 1 1 1v8.586l2.293-2.293 1.414 1.414L12 17.414 7.293 12.707l1.414-1.414L11 13.586V5a1 1 0 0 1 1-1ZM5 19h14v2H5z" />
    </svg>
  )
}

function IconRun() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 5.5v13l10-6.5-10-6.5Z" />
    </svg>
  )
}

function IconReview() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 2 3 6v6c0 5.2 3.6 9.9 9 10 5.4-.1 9-4.8 9-10V6l-9-4Zm0 3.1 6 2.7v4.2c0 3.8-2.4 7.4-6 8.1-3.6-.7-6-4.3-6-8.1V7.8l6-2.7Z" />
    </svg>
  )
}

function IconExamine() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M10 4a6 6 0 1 1 0 12 6 6 0 0 1 0-12Zm0 2a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm8.5 9.5-3-3 1.4-1.4 3 3-1.4 1.4Z" />
    </svg>
  )
}

function IconChanges() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 4h14a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm0 10h9a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1Zm11 0h3a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-3a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1Z" />
    </svg>
  )
}

function EmptyState({ title, description, action }) {
  return (
    <div className="empty-state-card">
      <div className="empty-state-title">{title}</div>
      <div className="empty-state-description">{description}</div>
      {action ? (
        <div className="empty-state-action">{action}</div>
      ) : null}
    </div>
  )
}

function App() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(null)
  const [projectDocs, setProjectDocs] = useState([])
  const [projectName, setProjectName] = useState('')
  const [running, setRunning] = useState(false)
  const [runId, setRunId] = useState(null)
  const [runData, setRunData] = useState(null)
  const [report, setReport] = useState(null)
  const [examineRules, setExamineRules] = useState('')
  const [findings, setFindings] = useState([])
  const [examineStatus, setExamineStatus] = useState('clean')
  const [error, setError] = useState(null)
  const [uploadFiles, setUploadFiles] = useState([])
  const [expandedEvidence, setExpandedEvidence] = useState({})
  const uploadInputRef = useRef(null)
  const runRequestInFlight = useRef(false)

  useEffect(() => {
    fetchProjects()
  }, [])

  useEffect(() => {
    let timer

    if (runId && !report) {
      timer = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/runs/${runId}`)

          if (res.status === 200) {
            const j = await res.json()

            setRunData(j)

            if (j.status === 'completed') {
              clearInterval(timer)
              setRunning(false)

              const rep = await fetch(`${API_BASE}/runs/${runId}/report`)

              if (rep.status === 200) {
                const repj = await rep.json()
                setReport(repj)
              }
            }
          }
        } catch {
          setError('Unable to refresh run status')
        }
      }, 1000)
    }

    return () => clearInterval(timer)
  }, [runId, report])

  useEffect(() => {
    if (!runId) {
      setFindings([])
      setExamineStatus('clean')
      return
    }

    if (runData?.status === 'completed') {
      fetchFindings()
    }
  }, [runId, runData?.status])

  async function fetchProjects() {
    try {
      const res = await fetch(`${API_BASE}/projects`)
      const j = await res.json()
      setProjects(j)
    } catch {
      setError('Unable to load projects')
    }
  }

  async function fetchProjectDocs(projectId) {
    try {
      const res = await fetch(`${API_BASE}/projects/${projectId}/documents`)
      const j = await res.json()
      setProjectDocs(j)
    } catch {
      setError('Unable to load project documents')
    }
  }

  async function createProject() {
    if (!projectName.trim()) {
      setError('Project name is required')
      return
    }

    try {
      const res = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: projectName.trim() }),
      })

      const j = await res.json()

      if (res.status !== 201) {
        setError(j.detail || 'Unable to create project')
        return
      }

      setProjectName('')
      await fetchProjects()
      setSelectedProject(j)
      setProjectDocs([])
      setRunId(null)
      setRunData(null)
      setReport(null)
      setError(null)
    } catch {
      setError('Unable to create project')
    }
  }

  function openProject(project) {
    setSelectedProject(project)
    setRunId(null)
    setRunData(null)
    setReport(null)
    setError(null)
    setUploadFiles([])
    fetchProjectDocs(project.id)
  }

  // UPDATED: accepts files directly so we don't depend on
  // asynchronous React state updates.
  async function uploadDocuments(files = uploadFiles) {
    if (!selectedProject) {
      setError('No project selected')
      return
    }

    if (!files || !files.length) {
      setError('Select files to upload')
      return
    }

    setError(null)

    const formData = new FormData()

    files.forEach(file => {
      formData.append('files', file)
    })

    try {
      const res = await fetch(
        `${API_BASE}/projects/${selectedProject.id}/documents/upload`,
        {
          method: 'POST',
          body: formData,
        }
      )

      const contentType = res.headers.get('content-type') || ''

      let data = null

      if (contentType.includes('application/json')) {
        data = await res.json()
      } else {
        data = await res.text()
      }

      if (!res.ok) {
        const message =
          typeof data === 'object' && data?.detail
            ? data.detail
            : 'Unable to upload documents'

        setError(message)

        console.error('Document upload failed:', {
          status: res.status,
          response: data,
        })

        return
      }

      console.log('Documents uploaded successfully:', data)

      setUploadFiles([])

      await fetchProjectDocs(selectedProject.id)
      await fetchProjects()
    } catch (error) {
      console.error('Document upload error:', error)

      setError(
        error instanceof Error
          ? error.message
          : 'Unable to upload documents'
      )
    }
  }

  async function runAnalysis() {
    if (runRequestInFlight.current) {
      return
    }

    if (!selectedProject) {
      setError('No project selected')
      return
    }

    const ids = projectDocs.map(d => d.id)

    if (!ids.length) {
      setError('No documents available for this project')
      return
    }

    try {
      runRequestInFlight.current = true
      setRunning(true)

      const res = await fetch(`${API_BASE}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: selectedProject.id,
          document_ids: ids,
        }),
      })

      const j = await res.json()

      if (res.status !== 201) {
        setError(j.detail || 'Unable to start analysis run')
        setRunning(false)
        return
      }

      setRunId(j.run_id)
      setRunData(null)
      setReport(null)
      setError(null)
    } catch {
      setRunning(false)
      setError('Unable to start analysis run')
    } finally {
      runRequestInFlight.current = false
    }
  }

  async function fetchFindings() {
    if (!runId) return

    try {
      const res = await fetch(`${API_BASE}/runs/${runId}/findings`)

      if (res.status !== 200) {
        return
      }

      const j = await res.json()

      setFindings(j.findings || [])
      setExamineStatus(j.examine_status || 'clean')
    } catch {
      // ignore silently for now
    }
  }

  async function runExamination() {
    if (!runId) return

    const rules = examineRules
      .split('\n')
      .map(line => line.trim())
      .filter(line => line)

    if (!rules.length) {
      setError('Enter at least one rule before running examination')
      return
    }

    try {
      const res = await fetch(`${API_BASE}/runs/${runId}/examine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rules }),
      })

      const j = await res.json()

      if (res.status !== 200) {
        setError(
          j.error ||
            j.detail ||
            'Unable to run examination'
        )
        return
      }

      setFindings(j.findings || [])
      setExamineStatus(j.examine_status || 'clean')
      setError(null)
    } catch {
      setError('Unable to run examination')
    }
  }

  async function reviewFinding(finding_id, decision) {
    if (!runId) return

    try {
      await fetch(
        `${API_BASE}/runs/${runId}/findings/${finding_id}/review`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            decision,
            comment: '',
          }),
        }
      )

      await fetchFindings()
    } catch {
      setError('Unable to submit finding review')
    }
  }

  async function review(conflict_id, decision) {
    if (!runId) return

    try {
      await fetch(
        `${API_BASE}/runs/${runId}/conflicts/${conflict_id}/review`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            decision,
            comment:
              decision === 'accept_b'
                ? 'Accepted via demo UI'
                : '',
          }),
        }
      )

      const r = await fetch(`${API_BASE}/runs/${runId}`)
      const j = await r.json()

      setRunData(j)

      const rep = await fetch(
        `${API_BASE}/runs/${runId}/report`
      )

      if (rep.status === 200) {
        const repj = await rep.json()
        setReport(repj)
      }
    } catch {
      setError('Unable to submit review')
    }
  }

  const pendingConflicts = (runData?.conflicts || []).filter(
    c => c.status === 'pending_review'
  )

  const resolvedConflicts = (runData?.conflicts || []).filter(
    c =>
      c.status === 'resolved' ||
      c.status === 'rejected'
  )

  const hasPendingConflicts = pendingConflicts.length > 0

  const workflowSteps = [
    {
      key: 'LOAD_DOCUMENTS',
      label: 'Load Documents',
    },
    {
      key: 'RETRIEVE_RELEVANT_CONTEXT',
      label: 'Retrieve Context',
    },
    {
      key: 'EXTRACT_FACTS',
      label: 'Extract Facts',
    },
    {
      key: 'COMPARE_FACTS',
      label: 'Compare Facts',
    },
    {
      key: 'CREATE_DRAFT',
      label: 'Create Draft',
    },
  ]

  function toggleEvidence(key) {
    setExpandedEvidence(prev => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  const showAnalysisRunning = Boolean(
    running && runData?.status !== 'completed'
  )

  const runStatusLabel = formatStatusLabel(
    runData?.status ||
      (running ? 'running' : 'ready')
  )

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">D</div>

          <div>
            <div className="brand-title">DocTask</div>
            <div className="brand-subtitle">
              Project Intelligence
            </div>
          </div>
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">
            Projects
          </div>

          <button
            className={`sidebar-nav-item ${
              !selectedProject ? 'active' : ''
            }`}
            onClick={() => setSelectedProject(null)}
          >
            <span>All projects</span>
            <small>{projects.length}</small>
          </button>

          {projects.map(project => (
            <button
              key={project.id}
              className={`sidebar-nav-item ${
                selectedProject?.id === project.id
                  ? 'active'
                  : ''
              }`}
              onClick={() => openProject(project)}
            >
              <span>{project.name}</span>
              <small>{project.document_count}</small>
            </button>
          ))}
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">
            Workspace
          </div>

          <div className="sidebar-nav-item static">
            <span>
              <IconDocument /> Documents
            </span>
          </div>

          <div className="sidebar-nav-item static">
            <span>
              <IconRun /> Analysis Runs
            </span>
          </div>

          <div className="sidebar-nav-item static">
            <span>
              <IconChanges /> Changes
            </span>
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="system-pill">
            <span className="status-dot" />
            System status
          </div>

          <div className="sidebar-footer-text">
            Backend connected
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="page-header">
          <div className="page-heading">
            <div className="page-breadcrumb">
              Projects /{' '}
              {selectedProject
                ? selectedProject.name
                : 'Overview'}
            </div>

            <h1>
              {selectedProject
                ? selectedProject.name
                : 'Projects'}
            </h1>

            <p className="hero-subtitle">
              {selectedProject
                ? 'Analyze project documents, identify conflicting facts, and preserve evidence before changes are committed.'
                : 'Create or open a project to review documents, workflow status, and final report output.'}
            </p>
          </div>

          <div className="header-actions">
            {selectedProject ? (
              <>
                <button
                  className="secondary-button"
                  onClick={() =>
                    setSelectedProject(null)
                  }
                >
                  <span className="button-icon">
                    <IconRun />
                  </span>
                  Back to Projects
                </button>

                <button
                  className="secondary-button"
                  onClick={() =>
                    uploadInputRef.current?.click()
                  }
                >
                  <span className="button-icon">
                    <IconUpload />
                  </span>
                  Upload documents
                </button>

                <button
                  className="primary-button"
                  onClick={runAnalysis}
                  disabled={
                    running || !projectDocs.length
                  }
                >
                  <span className="button-icon">
                    <IconRun />
                  </span>

                  {showAnalysisRunning
                    ? 'Analysis in progress'
                    : 'Run Analysis'}
                </button>
              </>
            ) : (
              <button
                className="primary-button"
                onClick={createProject}
                disabled={!projectName.trim()}
              >
                Create Project
              </button>
            )}
          </div>
        </header>

        {error && <div className="alert">{error}</div>}

        {!selectedProject ? (
          <section className="panel panel-hero">
            <div className="hero-top">
              <div>
                <div className="section-eyebrow">
                  Workspace
                </div>

                <h2>
                  Manage projects and source documents
                </h2>

                <p className="panel-subtitle">
                  Create a project to start an analysis
                  run and surface evidence-backed
                  changes.
                </p>
              </div>
            </div>

            <div className="hero-form">
              <input
                value={projectName}
                onChange={e =>
                  setProjectName(e.target.value)
                }
                placeholder="New project name"
                aria-label="Project name"
              />

              <button
                className="primary-button"
                onClick={createProject}
              >
                Create Project
              </button>
            </div>

            <div className="project-list">
              {projects.map(project => (
                <button
                  key={project.id}
                  className="project-card"
                  onClick={() => openProject(project)}
                >
                  <div>
                    <div className="project-card-title">
                      {project.name}
                    </div>

                    <div className="project-card-meta">
                      {project.document_count} document
                      {project.document_count === 1
                        ? ''
                        : 's'}
                    </div>
                  </div>

                  <span className="text-link">
                    Open
                  </span>
                </button>
              ))}
            </div>
          </section>
        ) : (
          <>
            <section className="panel panel-overview">
              <div className="panel-heading">
                <div>
                  <div className="section-eyebrow">
                    Latest analysis run
                  </div>

                  <h3>{selectedProject.name}</h3>
                </div>

                <StatusBadge
                  status={
                    runData?.status ||
                    (running ? 'running' : 'ready')
                  }
                />
              </div>

              <div className="overview-body">
                <div className="overview-main">
                  <div className="overview-title">
                    {runStatusLabel}
                  </div>

                  <div className="overview-meta">
                    {runId
                      ? `Run ID ${runId}`
                      : 'No run started yet'}
                  </div>

                  {showAnalysisRunning ? (
                    <div className="loading-row">
                      <span className="loading-dot" />
                      Processing project
                      documents...
                    </div>
                  ) : null}
                </div>

                <div className="overview-actions">
                  <button
                    className="secondary-button"
                    onClick={() =>
                      navigator.clipboard?.writeText(
                        runId || ''
                      )
                    }
                    disabled={!runId}
                  >
                    Copy run ID
                  </button>

                  <div className="overview-kicker">
                    Duration ·{' '}
                    {formatDuration(
                      runData?.timing
                        ?.total_duration_ms
                    )}
                  </div>
                </div>
              </div>

              <div className="metric-grid">
                <div className="metric-card">
                  <div className="metric-label">
                    Input tokens
                  </div>

                  <div className="metric-value">
                    {formatMetricValue(
                      runData?.timing
                        ?.total_input_tokens
                    )}
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-label">
                    Output tokens
                  </div>

                  <div className="metric-value">
                    {formatMetricValue(
                      runData?.timing
                        ?.total_output_tokens
                    )}
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-label">
                    Total tokens
                  </div>

                  <div className="metric-value">
                    {formatMetricValue(
                      runData?.timing?.total_tokens
                    )}
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-label">
                    Estimated cost
                  </div>

                  <div className="metric-value">
                    {formatCurrency(
                      runData?.timing
                        ?.total_estimated_cost
                    )}
                  </div>
                </div>
              </div>
            </section>

            <section className="dashboard-grid">
              <div className="stack-column">
                <div className="panel documents-panel">
                  <div className="panel-heading">
                    <div>
                      <div className="section-eyebrow">
                        Documents
                      </div>

                      <h3>Source files</h3>
                    </div>

                    <div className="panel-heading-actions">
                      <span className="section-count">
                        {projectDocs.length} files
                      </span>

                      <button
                        className="inline-action"
                        onClick={() =>
                          uploadInputRef.current?.click()
                        }
                      >
                        <IconUpload />
                        <span>Upload</span>
                      </button>

                      {/* UPDATED FILE INPUT */}
                      <input
                        ref={uploadInputRef}
                        id="document-upload"
                        type="file"
                        multiple
                        onChange={async e => {
                          const files = Array.from(
                            e.target.files || []
                          )

                          setUploadFiles(files)

                          if (!files.length) {
                            return
                          }

                          // Upload the files directly instead of
                          // waiting for React state to update.
                          await uploadDocuments(files)

                          // Allow selecting the same file again later.
                          e.target.value = ''
                        }}
                        hidden
                      />
                    </div>
                  </div>

                  {projectDocs.length === 0 ? (
                    <EmptyState
                      title="No documents yet"
                      description="Upload project documents to begin analysis."
                      action={
                        <button
                          className="primary-button"
                          onClick={() =>
                            uploadInputRef.current?.click()
                          }
                        >
                          Upload documents
                        </button>
                      }
                    />
                  ) : (
                    <div className="document-list">
                      {projectDocs
                        .slice(0, 6)
                        .map(document => (
                          <div
                            key={document.id}
                            className="document-row"
                          >
                            <div className="document-main">
                              <div className="document-icon">
                                <IconDocument />
                              </div>

                              <div className="document-copy">
                                <div
                                  className="document-name"
                                  title={
                                    document.filename
                                  }
                                  aria-label={
                                    document.filename
                                  }
                                >
                                  {formatDisplayFilename(
                                    document.filename
                                  )}
                                </div>

                                <div className="document-meta">
                                  {document.document_type ||
                                    'TXT'}{' '}
                                  ·{' '}
                                  {document.status ||
                                    'Uploaded'}
                                </div>
                              </div>
                            </div>

                            <div className="document-status">
                              <StatusBadge
                                status={
                                  document.status ||
                                  'Uploaded'
                                }
                              />
                            </div>
                          </div>
                        ))}

                      {projectDocs.length > 6 ? (
                        <div className="document-footnote">
                          View all files →
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>

                <div className="panel examine-panel">
                  <div className="panel-heading">
                    <div>
                      <div className="section-eyebrow">
                        Examine
                      </div>

                      <h3>
                        Post-analysis validation
                      </h3>
                    </div>

                    <StatusBadge
                      status={
                        examineStatus === 'clean'
                          ? 'Clean'
                          : 'Review'
                      }
                    />
                  </div>

                  <div className="exam-row">
                    <textarea
                      value={examineRules}
                      onChange={e =>
                        setExamineRules(e.target.value)
                      }
                      placeholder="Enter one rule or checklist item per line"
                      rows={6}
                      aria-label="Examine rules"
                    />

                    <div className="exam-side">
                      <button
                        className="primary-button"
                        onClick={runExamination}
                        disabled={
                          !runId ||
                          runData?.status !==
                            'completed'
                        }
                      >
                        Run Examination
                      </button>

                      <div className="exam-status-card">
                        <div className="review-label">
                          Status
                        </div>

                        <div className="exam-status-value">
                          {examineStatus === 'clean'
                            ? 'CLEAN'
                            : examineStatus ===
                              'unavailable'
                            ? 'UNAVAILABLE'
                            : examineStatus.toUpperCase()}
                        </div>
                      </div>
                    </div>
                  </div>

                  {findings.length > 0 ? (
                    <div className="finding-list">
                      {findings.map(finding => (
                        <div
                          key={finding.finding_id}
                          className="finding-card"
                        >
                          <div className="finding-header">
                            <div>
                              <div className="finding-title">
                                {
                                  finding.rule_reference
                                }
                              </div>

                              <div className="finding-meta">
                                {
                                  finding.source_document
                                }
                              </div>
                            </div>

                            <StatusBadge
                              status={finding.status}
                            />
                          </div>

                          <div className="finding-body">
                            <p>
                              {finding.description}
                            </p>

                            <div className="evidence-block">
                              <button
                                className="text-button"
                                onClick={() =>
                                  toggleEvidence(
                                    `finding-${finding.finding_id}`
                                  )
                                }
                              >
                                {expandedEvidence[
                                  `finding-${finding.finding_id}`
                                ]
                                  ? 'Hide evidence'
                                  : 'Show evidence'}
                              </button>

                              {expandedEvidence[
                                `finding-${finding.finding_id}`
                              ] && (
                                <div className="evidence-text">
                                  {finding.evidence}
                                </div>
                              )}
                            </div>
                          </div>

                          {finding.status ===
                            'pending_review' && (
                            <div className="review-actions">
                              <button
                                className="secondary-button"
                                onClick={() =>
                                  reviewFinding(
                                    finding.finding_id,
                                    'approve'
                                  )
                                }
                              >
                                Approve
                              </button>

                              <button
                                className="secondary-button"
                                onClick={() =>
                                  reviewFinding(
                                    finding.finding_id,
                                    'reject'
                                  )
                                }
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      title="✓ Clean"
                      description="No findings detected."
                    />
                  )}
                </div>
              </div>

              <div className="stack-column">
                <div className="panel workflow-panel">
                  <div className="panel-heading">
                    <div>
                      <div className="section-eyebrow">
                        Workflow
                      </div>

                      <h3>Execution pipeline</h3>
                    </div>
                  </div>

                  <div className="workflow-timeline">
                    {workflowSteps.map(
                      (step, index) => {
                        const stageValue =
                          runData?.stages?.[
                            step.key
                          ] || 'not_started'

                        const metric =
                          runData?.timing?.stages?.[
                            step.key
                          ]

                        const tone =
                          getStatusTone(stageValue)

                        return (
                          <div
                            key={step.key}
                            className="workflow-item"
                          >
                            <div
                              className={`workflow-node workflow-${tone}`}
                            >
                              <div className="workflow-node-icon">
                                {tone === 'success'
                                  ? '✓'
                                  : tone === 'warning'
                                  ? '●'
                                  : tone === 'error'
                                  ? '!'
                                  : '○'}
                              </div>

                              <div className="workflow-node-copy">
                                <div className="workflow-title">
                                  {step.label}
                                </div>

                                <div className="workflow-meta">
                                  <StatusBadge
                                    status={
                                      stageValue
                                    }
                                  />

                                  {metric?.duration_ms !=
                                  null ? (
                                    <span>
                                      {formatDuration(
                                        metric.duration_ms
                                      )}
                                    </span>
                                  ) : null}
                                </div>

                                {metric?.total_tokens !=
                                null ? (
                                  <div className="workflow-detail">
                                    {
                                      metric.total_tokens
                                    }{' '}
                                    tokens
                                  </div>
                                ) : null}
                              </div>
                            </div>

                            {index <
                            workflowSteps.length - 1 ? (
                              <div className="workflow-connector" />
                            ) : null}
                          </div>
                        )
                      }
                    )}
                  </div>
                </div>

                <div
                  className={`panel review-panel ${
                    hasPendingConflicts
                      ? 'review-panel-active'
                      : ''
                  }`}
                >
                  <div className="panel-heading">
                    <div>
                      <div className="section-eyebrow">
                        Human Review
                      </div>

                      <h3>Decision required</h3>
                    </div>

                    {hasPendingConflicts ? (
                      <span className="status-pill status-warning">
                        Review required
                      </span>
                    ) : null}
                  </div>

                  {!hasPendingConflicts ? (
                    <EmptyState
                      title="✓ No pending conflicts"
                      description="All conflicting facts have been reviewed."
                    />
                  ) : (
                    <div className="review-stack">
                      {pendingConflicts.map(
                        conflict => (
                          <div
                            key={conflict.conflict_id}
                            className="review-card"
                          >
                            <div className="review-card-header">
                              <div>
                                <div className="review-card-title">
                                  {
                                    conflict.description
                                  }
                                </div>

                                <div className="review-card-subtitle">
                                  {conflict.fact_a} ·{' '}
                                  {conflict.fact_b}
                                </div>
                              </div>

                              <StatusBadge
                                status={
                                  conflict.status
                                }
                              />
                            </div>

                            <div className="review-grid">
                              <div>
                                <div className="review-label">
                                  Current
                                </div>

                                <div className="review-value">
                                  {conflict.fact_a}
                                </div>

                                <div className="review-meta">
                                  {conflict.source_a}
                                </div>
                              </div>

                              <div>
                                <div className="review-label">
                                  New
                                </div>

                                <div className="review-value">
                                  {conflict.fact_b}
                                </div>

                                <div className="review-meta">
                                  {conflict.source_b}
                                </div>
                              </div>
                            </div>

                            <div className="evidence-block">
                              <button
                                className="text-button"
                                onClick={() =>
                                  toggleEvidence(
                                    conflict.conflict_id
                                  )
                                }
                              >
                                {expandedEvidence[
                                  conflict.conflict_id
                                ]
                                  ? 'Hide evidence'
                                  : 'Show evidence'}
                              </button>

                              {expandedEvidence[
                                conflict.conflict_id
                              ] && (
                                <div className="evidence-stack">
                                  <div>
                                    <div className="review-label">
                                      Evidence A
                                    </div>

                                    <div className="evidence-text">
                                      {
                                        conflict.evidence_a
                                      }
                                    </div>
                                  </div>

                                  <div>
                                    <div className="review-label">
                                      Evidence B
                                    </div>

                                    <div className="evidence-text">
                                      {
                                        conflict.evidence_b
                                      }
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>

                            <div className="review-actions">
                              <button
                                className="secondary-button"
                                onClick={() =>
                                  review(
                                    conflict.conflict_id,
                                    'accept_a'
                                  )
                                }
                              >
                                Accept A
                              </button>

                              <button
                                className="primary-button"
                                onClick={() =>
                                  review(
                                    conflict.conflict_id,
                                    'accept_b'
                                  )
                                }
                              >
                                Accept B
                              </button>

                              <button
                                className="secondary-button"
                                onClick={() =>
                                  review(
                                    conflict.conflict_id,
                                    'reject_conflict'
                                  )
                                }
                              >
                                Reject
                              </button>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section className="panel report-panel">
              <div className="panel-heading report-heading">
                <div>
                  <div className="section-eyebrow">
                    Final Project Report
                  </div>

                  <h3>
                    Structured project register
                  </h3>

                  <p className="panel-subtitle">
                    Evidence-grounded milestones
                    derived from the latest analysis
                    and review state.
                  </p>
                </div>

                <StatusBadge status="Completed" />
              </div>

              {!report ? (
                <EmptyState
                  title="Report unavailable"
                  description="Complete the analysis and required review before the report is finalized."
                />
              ) : (
                <>
                  <div className="report-summary">
                    <span>
                      {(report.milestones || []).length}{' '}
                      milestones
                    </span>

                    <span>·</span>

                    <span>
                      {resolvedConflicts.length}{' '}
                      resolved conflict
                      {resolvedConflicts.length === 1
                        ? ''
                        : 's'}
                    </span>
                  </div>

                  <div className="report-table">
                    <div className="report-table-header">
                      <div className="report-cell report-cell-name">
                        Milestone
                      </div>

                      <div className="report-cell report-cell-owner">
                        Owner
                      </div>

                      <div className="report-cell report-cell-date">
                        Due date
                      </div>

                      <div className="report-cell report-cell-source">
                        Source
                      </div>

                      <div className="report-cell report-cell-action">
                        Evidence
                      </div>
                    </div>

                    {(report.milestones || []).map(
                      milestone => {
                        const key = `milestone-${milestone.subject}`

                        return (
                          <div
                            key={milestone.subject}
                            className="report-row"
                          >
                            <div className="report-cell report-cell-name">
                              <div className="report-name">
                                {milestone.subject}
                              </div>
                            </div>

                            <div className="report-cell report-cell-owner">
                              {milestone.owner ||
                                'Unknown'}
                            </div>

                            <div className="report-cell report-cell-date">
                              {milestone.due_date ||
                                'N/A'}
                            </div>

                            <div className="report-cell report-cell-source">
                              {milestone.source_document ||
                                'N/A'}
                            </div>

                            <div className="report-cell report-cell-action">
                              <button
                                className="text-button"
                                onClick={() =>
                                  toggleEvidence(key)
                                }
                              >
                                {expandedEvidence[key]
                                  ? 'Hide evidence'
                                  : 'View evidence'}
                              </button>
                            </div>

                            {expandedEvidence[key] ? (
                              <div className="report-evidence">
                                <div className="review-label">
                                  Evidence
                                </div>

                                <div className="evidence-text">
                                  {milestone.evidence ||
                                    'No evidence provided.'}
                                </div>
                              </div>
                            ) : null}
                          </div>
                        )
                      }
                    )}
                  </div>

                  {resolvedConflicts.length > 0 ? (
                    <div className="history-card">
                      <div className="history-title">
                        Resolved conflicts
                      </div>

                      <div className="review-stack">
                        {resolvedConflicts.map(
                          conflict => (
                            <div
                              key={
                                conflict.conflict_id
                              }
                              className="history-item"
                            >
                              <div className="history-item-header">
                                <div>
                                  <div className="history-item-title">
                                    {
                                      conflict.description
                                    }
                                  </div>

                                  <div className="history-item-meta">
                                    {
                                      conflict.fact_a
                                    }{' '}
                                    →{' '}
                                    {
                                      conflict.fact_b
                                    }
                                  </div>
                                </div>

                                <StatusBadge
                                  status={
                                    conflict.status
                                  }
                                />
                              </div>

                              <div className="history-item-details">
                                <div>
                                  <div className="review-label">
                                    Decision
                                  </div>

                                  <div>
                                    {conflict.decision ||
                                      'Pending'}
                                  </div>
                                </div>

                                <div>
                                  <div className="review-label">
                                    Accepted value
                                  </div>

                                  <div>
                                    {conflict.accepted_fact ||
                                      'N/A'}
                                  </div>
                                </div>
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  )
}

export default App