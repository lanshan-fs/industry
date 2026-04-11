type CachedValue<T> = {
  value?: T;
  updatedAt: number;
  promise?: Promise<T>;
};

const DASHBOARD_TTL = 5 * 60 * 1000;
const META_TTL = 30 * 60 * 1000;

const cacheStore: Record<string, CachedValue<any>> = {};

function isFresh<T>(entry: CachedValue<T> | undefined, ttl: number) {
  return Boolean(entry?.value !== undefined && entry && Date.now() - entry.updatedAt < ttl);
}

function getCacheKey(key: string) {
  return `ic:${key}`;
}

function readStorage<T>(key: string): CachedValue<T> | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.sessionStorage.getItem(getCacheKey(key));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as CachedValue<T>;
    if (!parsed || typeof parsed.updatedAt !== "number") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeStorage<T>(key: string, entry: CachedValue<T>) {
  if (typeof window === "undefined" || entry.value === undefined) {
    return;
  }
  try {
    window.sessionStorage.setItem(
      getCacheKey(key),
      JSON.stringify({ value: entry.value, updatedAt: entry.updatedAt }),
    );
  } catch {
    // Ignore storage quota and serialization issues.
  }
}

function peekCached<T>(key: string, ttl: number): T | null {
  const memoryEntry = cacheStore[key] as CachedValue<T> | undefined;
  if (isFresh(memoryEntry, ttl)) {
    return memoryEntry?.value ?? null;
  }

  const storageEntry = readStorage<T>(key);
  if (isFresh(storageEntry ?? undefined, ttl)) {
    cacheStore[key] = storageEntry as CachedValue<any>;
    return storageEntry?.value ?? null;
  }

  return null;
}

async function loadJsonWithCache<T>(key: string, url: string, ttl: number, force = false): Promise<T> {
  const current = cacheStore[key] as CachedValue<T> | undefined;
  if (!force) {
    if (isFresh(current, ttl) && current?.value !== undefined) {
      return current.value;
    }
    if (current?.promise) {
      return current.promise;
    }
    const cached = peekCached<T>(key, ttl);
    if (cached !== null) {
      return cached;
    }
  }

  const promise = fetch(url)
    .then(async (response) => {
      const json = (await response.json()) as T;
      const nextEntry: CachedValue<T> = {
        value: json,
        updatedAt: Date.now(),
      };
      cacheStore[key] = nextEntry as CachedValue<any>;
      writeStorage(key, nextEntry);
      return json;
    })
    .finally(() => {
      const latest = cacheStore[key];
      if (latest) {
        delete latest.promise;
      }
    });

  cacheStore[key] = {
    value: current?.value,
    updatedAt: current?.updatedAt ?? 0,
    promise,
  };

  return promise;
}

export function peekDashboardOverview<T = any>() {
  return peekCached<T>("dashboard-overview", DASHBOARD_TTL);
}

export function fetchDashboardOverview<T = any>(force = false) {
  return loadJsonWithCache<T>("dashboard-overview", "/api/dashboard/overview", DASHBOARD_TTL, force);
}

export function peekMetaAll<T = any>() {
  return peekCached<T>("meta-all", META_TTL);
}

export function fetchMetaAll<T = any>(force = false) {
  return loadJsonWithCache<T>("meta-all", "/api/meta/all", META_TTL, force);
}
