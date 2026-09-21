import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';

const POLL_MS = 1500;

/**
 * Tracks one background job: start it, poll until done, expose its state.
 *
 * The backend returns immediately from POST /api/actions/{name} with a job
 * id; this hook polls GET /api/jobs/{id} until `done` is true.  Polling
 * stops automatically when the component unmounts or the job finishes.
 */
export function useJob() {
  const [job, setJob] = useState(null);
  const [starting, setStarting] = useState(false);
  const timer = useRef(null);

  const stop = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  const poll = useCallback(
    async (id) => {
      try {
        const { job: latest } = await api.job(id);
        setJob(latest);
        if (!latest.done) timer.current = setTimeout(() => poll(id), POLL_MS);
      } catch (err) {
        // Transient network blip: keep trying rather than losing the job.
        timer.current = setTimeout(() => poll(id), POLL_MS * 2);
        console.warn('job poll failed', err);
      }
    },
    [],
  );

  const start = useCallback(
    async (action) => {
      stop();
      setStarting(true);
      try {
        const { job: created } = await api.startAction(action);
        setJob(created);
        timer.current = setTimeout(() => poll(created.id), POLL_MS);
        return created;
      } finally {
        setStarting(false);
      }
    },
    [poll, stop],
  );

  useEffect(() => stop, [stop]);

  const running = starting || (job && !job.done);
  return { job, running, start, clear: () => { stop(); setJob(null); } };
}
