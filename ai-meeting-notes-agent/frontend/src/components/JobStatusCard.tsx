import { useCallback } from 'react';
import { formatDistanceToNow } from 'date-fns';
import useJobStatus from '../hooks/useJobStatus';
import type { MeetingJob } from '../lib/api';

interface Props {
  job: MeetingJob;
  onRefresh: (job: MeetingJob) => void;
}

const statusCopy: Record<MeetingJob['status'], string> = {
  PENDING: 'Pending — preparing to process your meeting.',
  PROCESSING: 'Processing — transcribing, summarizing, or sending emails.',
  COMPLETED: 'Completed — summary generated and emails delivered.',
  FAILED: 'Failed — something went wrong. Check CloudWatch logs.',
};

const statusColor: Record<MeetingJob['status'], string> = {
  PENDING: '#fde68a',
  PROCESSING: '#bfdbfe',
  COMPLETED: '#bbf7d0',
  FAILED: '#fecaca',
};

const JobStatusCard = ({ job, onRefresh }: Props) => {
  const { job: latestJob, loading, error } = useJobStatus({ jobId: job.id });

  const resolvedJob = latestJob ?? job;

  const handleCopy = useCallback(async () => {
    if (!resolvedJob.summary) return;
    await navigator.clipboard.writeText(resolvedJob.summary);
  }, [resolvedJob.summary]);

  return (
    <div className="grid" style={{ gap: '1.2rem' }}>
      <div className="status-panel">
        <div className="status-title">Status</div>
        <div className="badge" style={{ background: statusColor[resolvedJob.status], color: '#0f172a' }}>
          {resolvedJob.status}
        </div>
        <p style={{ marginTop: '0.6rem', color: '#475569' }}>{statusCopy[resolvedJob.status]}</p>
        {loading && <p style={{ color: '#64748b' }}>Refreshing status…</p>}
        {error && <p style={{ color: '#dc2626' }}>{error}</p>}
      </div>

      <div className="status-grid">
        <div>
          <strong>Job ID:</strong> {resolvedJob.id}
        </div>
        <div>
          <strong>Created:</strong>{' '}
          {formatDistanceToNow(new Date(resolvedJob.createdAt), { addSuffix: true })}
        </div>
        <div>
          <strong>Participants:</strong>{' '}
          {resolvedJob.participants.join(', ')}
        </div>
        {resolvedJob.targetLanguage && (
          <div>
            <strong>Target language:</strong> {resolvedJob.targetLanguage}
          </div>
        )}
        {resolvedJob.emailLocale && (
          <div>
            <strong>Email locale:</strong> {resolvedJob.emailLocale}
          </div>
        )}
        {resolvedJob.detectedLanguage && (
          <div>
            <strong>Detected language:</strong> {resolvedJob.detectedLanguage}
          </div>
        )}
        {resolvedJob.finalLanguage && (
          <div>
            <strong>Final language:</strong> {resolvedJob.finalLanguage}
          </div>
        )}
      </div>

      {resolvedJob.summary && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem' }}>
            <strong>Summary</strong>
            <button className="btn-secondary" type="button" onClick={handleCopy}>
              Copy summary
            </button>
          </div>
          <div className="summary-output">{resolvedJob.summary}</div>
          {resolvedJob.message && (
            <p style={{ color: '#475569', marginTop: '0.75rem' }}>{resolvedJob.message}</p>
          )}
        </div>
      )}
    </div>
  );
};

export default JobStatusCard;
