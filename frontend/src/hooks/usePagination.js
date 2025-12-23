/**
 * React hook for managing paginated list data
 * Works with the standardized ListResponse format from backend
 */
import { useState, useCallback, useMemo } from "react";

/**
 * @typedef {Object} UsePaginationOptions
 * @property {number} [initialOffset=0] - Initial offset
 * @property {number} [defaultLimit=50] - Default items per page
 */

/**
 * @typedef {Object} UsePaginationReturn
 * @property {number} offset - Current offset
 * @property {number} limit - Current limit
 * @property {number|null} total - Total count (null if not loaded)
 * @property {number} currentPage - Current page number (1-indexed)
 * @property {number} totalPages - Total number of pages
 * @property {boolean} hasNext - Whether there's a next page
 * @property {boolean} hasPrev - Whether there's a previous page
 * @property {() => void} nextPage - Go to next page
 * @property {() => void} prevPage - Go to previous page
 * @property {(page: number) => void} goToPage - Go to specific page (1-indexed)
 * @property {(newLimit: number) => void} setLimit - Change items per page
 * @property {() => void} reset - Reset to first page
 * @property {(meta: PaginationMeta) => void} updateFromMeta - Update from server response
 * @property {string} getQueryParams - Get URL query params string
 */

/**
 * Hook for managing pagination state and calculations
 * @param {UsePaginationOptions} [options]
 * @returns {UsePaginationReturn}
 */
export function usePagination(options = {}) {
  const { initialOffset = 0, defaultLimit = 50 } = options;

  const [offset, setOffset] = useState(initialOffset);
  const [limit, setLimit] = useState(defaultLimit);
  const [total, setTotal] = useState(null);

  // Calculate current page (1-indexed)
  const currentPage = useMemo(() => {
    return Math.floor(offset / limit) + 1;
  }, [offset, limit]);

  // Calculate total pages
  const totalPages = useMemo(() => {
    if (total === null) return 0;
    return Math.ceil(total / limit);
  }, [total, limit]);

  // Check if there's a next page
  const hasNext = useMemo(() => {
    if (total === null) return false;
    return offset + limit < total;
  }, [offset, limit, total]);

  // Check if there's a previous page
  const hasPrev = useMemo(() => {
    return offset > 0;
  }, [offset]);

  // Go to next page
  const nextPage = useCallback(() => {
    if (hasNext) {
      setOffset((prev) => prev + limit);
    }
  }, [hasNext, limit]);

  // Go to previous page
  const prevPage = useCallback(() => {
    if (hasPrev) {
      setOffset((prev) => Math.max(0, prev - limit));
    }
  }, [hasPrev, limit]);

  // Go to specific page (1-indexed)
  const goToPage = useCallback(
    (page) => {
      const pageNum = Math.max(1, Math.min(page, totalPages || 1));
      setOffset((pageNum - 1) * limit);
    },
    [limit, totalPages]
  );

  // Change limit and reset to first page
  const changeLimitAndReset = useCallback((newLimit) => {
    setLimit(newLimit);
    setOffset(0);
  }, []);

  // Reset to first page
  const reset = useCallback(() => {
    setOffset(0);
  }, []);

  // Update state from server PaginationMeta response
  const updateFromMeta = useCallback((meta) => {
    if (meta && typeof meta === "object") {
      if (typeof meta.total === "number") {
        setTotal(meta.total);
      }
      // Optionally sync offset/limit if server adjusted them
      if (typeof meta.offset === "number" && meta.offset !== offset) {
        setOffset(meta.offset);
      }
      if (typeof meta.limit === "number" && meta.limit !== limit) {
        setLimit(meta.limit);
      }
    }
  }, [offset, limit]);

  // Get query params string for API requests
  const getQueryParams = useCallback(() => {
    return `offset=${offset}&limit=${limit}`;
  }, [offset, limit]);

  return {
    offset,
    limit,
    total,
    currentPage,
    totalPages,
    hasNext,
    hasPrev,
    nextPage,
    prevPage,
    goToPage,
    setLimit: changeLimitAndReset,
    reset,
    updateFromMeta,
    getQueryParams,
  };
}

/**
 * Hook for managing a complete paginated list with API fetching
 * @template T
 * @param {Function} fetchFn - Async function that fetches data. Receives (offset, limit, filters)
 * @param {Object} [options]
 * @param {number} [options.initialOffset=0]
 * @param {number} [options.defaultLimit=50]
 * @param {Object} [options.initialFilters={}]
 * @param {boolean} [options.autoFetch=true]
 * @returns {{
 *   data: T[],
 *   loading: boolean,
 *   error: Error|null,
 *   pagination: UsePaginationReturn,
 *   filters: Object,
 *   setFilters: (filters: Object) => void,
 *   updateFilter: (key: string, value: any) => void,
 *   refresh: () => Promise<void>
 * }}
 */
export function usePaginatedList(fetchFn, options = {}) {
  const {
    initialOffset = 0,
    defaultLimit = 50,
    initialFilters = {},
    autoFetch = true,
  } = options;

  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFiltersState] = useState(initialFilters);

  const pagination = usePagination({ initialOffset, defaultLimit });

  // Fetch data from API
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchFn(pagination.offset, pagination.limit, filters);

      // Handle ListResponse format
      if (response && typeof response === "object") {
        if ("items" in response && "pagination" in response) {
          // New standardized format
          setData(response.items);
          pagination.updateFromMeta(response.pagination);
        } else if (Array.isArray(response)) {
          // Legacy format (direct array)
          setData(response);
        } else {
          // Unknown format
          console.warn("Unexpected API response format", response);
          setData([]);
        }
      } else {
        setData([]);
      }
    } catch (err) {
      setError(err);
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [fetchFn, pagination.offset, pagination.limit, filters, pagination.updateFromMeta]);

  // Update filters and reset to first page
  const setFilters = useCallback(
    (newFilters) => {
      setFiltersState(newFilters);
      pagination.reset();
    },
    [pagination.reset]
  );

  // Update a single filter
  const updateFilter = useCallback(
    (key, value) => {
      setFiltersState((prev) => ({ ...prev, [key]: value }));
      pagination.reset();
    },
    [pagination.reset]
  );

  // Auto-fetch when dependencies change
  useState(() => {
    if (autoFetch) {
      fetchData();
    }
  });

  return {
    data,
    loading,
    error,
    pagination,
    filters,
    setFilters,
    updateFilter,
    refresh: fetchData,
  };
}
