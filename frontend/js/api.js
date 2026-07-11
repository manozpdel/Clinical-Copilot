/**
 * Reusable API client that automatically attaches JWTs and handles
 * expired access tokens by refreshing once before failing.
 *
 * This module is responsible ONLY for making authenticated HTTP
 * requests. It contains no page-specific UI logic; higher-level auth
 * actions (login, logout, profile fetch) live in auth.js.
 */

import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "./storage.js";

export const API_BASE = "/api";

let refreshInFlight = null;

// Add a request cache to prevent duplicate in-flight requests
const pendingRequests = new Map();

async function performRefresh() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return false;
  }

  try {
    const response = await fetch("/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return false;
    }

    const body = await response.json();
    setTokens(body.access_token, body.refresh_token);
    return true;
  } catch (networkError) {
    return false;
  }
}

function handleAuthFailure() {
  clearSession();
  if (!window.location.pathname.endsWith("login.html")) {
    window.location.href = "login.html";
  }
}

/**
 * Perform an authenticated fetch against the REST API, attaching the
 * current access token and retrying once after a token refresh if the
 * server responds with 401 Unauthorized.
 *
 * @param {string} path - API path relative to API_BASE (e.g. "/query").
 * @param {RequestInit} [options] - Standard fetch options.
 * @returns {Promise<Response>} The (possibly retried) fetch response.
 */
export async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  // Create a cache key from the path and method
  const method = options.method || 'GET';
  const cacheKey = `${method}:${path}`;
  
  // Check if this exact request is already in progress
  if (pendingRequests.has(cacheKey)) {
    console.log(`♻️ Reusing in-flight request: ${cacheKey}`);
    return pendingRequests.get(cacheKey);
  }

  // Create the request promise
  const requestPromise = (async () => {
    try {
      let response;
      try {
        response = await fetch(`${API_BASE}${path}`, { ...options, headers });
      } catch (networkError) {
        throw new Error("Network error. Please check your connection and try again.");
      }

      if (response.status === 401) {
        if (!refreshInFlight) {
          refreshInFlight = performRefresh().finally(() => {
            refreshInFlight = null;
          });
        }
        const refreshed = await refreshInFlight;

        if (!refreshed) {
          handleAuthFailure();
          throw new Error("Your session has expired. Please log in again.");
        }

        headers.Authorization = `Bearer ${getAccessToken()}`;
        response = await fetch(`${API_BASE}${path}`, { ...options, headers });

        if (response.status === 401) {
          handleAuthFailure();
          throw new Error("Your session has expired. Please log in again.");
        }
      }

      return response;
    } finally {
      // Remove from cache after the request completes (success or error)
      pendingRequests.delete(cacheKey);
    }
  })();

  // Store the promise in the cache
  pendingRequests.set(cacheKey, requestPromise);
  return requestPromise;
}