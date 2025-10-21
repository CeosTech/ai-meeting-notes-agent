import { useEffect, useRef, useState } from 'react';
import { fetchJob, MeetingJob } from '../lib/api';

interface UseJobStatusOptions {
  jobId: string;
  pollInterval?: number;
}

export default function useJobStatus({ jobId, pollInterval = 4000 }: UseJobStatusOptions) {
  const [job, setJob] = useState<MeetingJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchStatus = async () => {
      try {
        const data = await fetchJob(jobId);
        if (!isMounted) return;
        setJob(data);
        setError(null);
        setLoading(false);
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          if (intervalRef.current) {
            window.clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch (err) {
        if (!isMounted) return;
        setError('Unable to retrieve job status.');
        setLoading(false);
      }
    };

    fetchStatus();
    intervalRef.current = window.setInterval(fetchStatus, pollInterval);

    return () => {
      isMounted = false;
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
      }
    };
  }, [jobId, pollInterval]);

  return { job, setJob, loading, error };
}
