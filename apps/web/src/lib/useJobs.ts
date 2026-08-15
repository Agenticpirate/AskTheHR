import { useEffect, useState } from "react";
import { loadAllJobs, loadJobs, type JobsPayload } from "./jobs";

export function useJobs(all = true): {
  data: JobsPayload | null;
  error: string | null;
  loading: boolean;
  loadingMore: boolean;
} {
  const [data, setData] = useState<JobsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let alive = true;
    loadJobs()
      .then((p) => {
        if (!alive) return;
        setData(p);
        if (all && p.more) {
          setLoadingMore(true);
          return loadAllJobs().then((full) => {
            if (!alive) return;
            setData(full);
            setLoadingMore(false);
          });
        }
      })
      .catch((e: unknown) => {
        if (!alive) return;
        setError(e instanceof Error ? e.message : "Could not load jobs");
      });
    return () => {
      alive = false;
    };
  }, [all]);

  return { data, error, loading: !data && !error, loadingMore };
}
