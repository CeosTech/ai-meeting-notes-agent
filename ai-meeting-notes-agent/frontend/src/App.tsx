import { useCallback, useMemo, useState } from 'react';
import UploadForm from './components/UploadForm';
import JobStatusCard from './components/JobStatusCard';
import type { CreateJobPayload, MeetingJob } from './lib/api';
import { createJob, getPresignedUpload, uploadFileToS3 } from './lib/api';

function App() {
  const [currentJob, setCurrentJob] = useState<MeetingJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async (payload: CreateJobPayload) => {
    setIsSubmitting(true);
    setError(null);
    try {
      let sourceKey = payload.sourceKey;
      if (payload.file) {
        const { uploadUrl, objectKey, fields } = await getPresignedUpload({
          filename: payload.file.name,
          contentType: payload.file.type || 'application/octet-stream'
        });
        await uploadFileToS3({ file: payload.file, uploadUrl, fields });
        sourceKey = objectKey;
      }

      const { file: _file, sourceKey: _placeholderKey, ...rest } = payload;
      const jobPayload = sourceKey
        ? { ...rest, sourceKey }
        : rest;

      const job = await createJob(jobPayload);
      setCurrentJob(job);
    } catch (err) {
      console.error(err);
      setError('Failed to create job. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const heroCopy = useMemo(() => ({
    title: 'AI Meeting Notes Agent',
    subtitle: 'Summarize meetings, surface action items, and deliver localized emails in minutes.'
  }), []);

  return (
    <div className="container">
      <header className="hero">
        <img src="/logo.svg" alt="AI Meeting Notes Agent" className="hero-logo" />
        <h1 className="hero-title">{heroCopy.title}</h1>
        <p className="hero-subtitle">{heroCopy.subtitle}</p>
      </header>

      <section className="card" style={{ marginBottom: '1.75rem' }}>
        <UploadForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
        {error && <p style={{ color: '#dc2626', marginTop: '1rem' }}>{error}</p>}
      </section>

      {currentJob && (
        <section className="card">
          <JobStatusCard job={currentJob} onRefresh={setCurrentJob} />
        </section>
      )}

      <footer style={{ marginTop: '3rem', textAlign: 'center', color: '#64748b' }}>
        <p>
          Built for the AWS AI Agent Hackathon — Powered by Amazon Bedrock, Transcribe, Translate, and SES.
        </p>
      </footer>
    </div>
  );
}

export default App;
