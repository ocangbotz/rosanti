import { useCallback, useEffect, useState } from "react";

import { extractErrorMessage } from "@/lib/apiClient";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Minimal data-fetching hook (loading/error/data + refetch) used across
 * the dashboard pages. Deliberately not react-query: this app's fetch
 * patterns are simple enough (one call per view, occasional manual
 * refetch) that a dependency for caching/retries/etc. isn't earning its
 * keep here.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: readonly unknown[],
  options?: { skip?: boolean },
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(!options?.skip);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (options?.skip) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(extractErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, options?.skip]);

  return { data, loading, error, refetch };
}
