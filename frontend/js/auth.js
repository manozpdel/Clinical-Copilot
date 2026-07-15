/**
 * Authentication actions: Google Sign-In, session checks, logout, and
 * fetching the current user's profile.
 *
 * This module is responsible ONLY for orchestrating authentication
 * flows against the existing backend endpoints. It contains no
 * low-level fetch retry/refresh logic (see api.js) and no page-specific
 * DOM rendering beyond rendering the Google button itself.
 */

import { apiFetch } from "./api.js";
import {
  clearSession,
  getAccessToken,
  setCachedUser,
  setTokens,
} from "./storage.js";

// Cache for fetch promise to prevent duplicate requests
let currentUserPromise = null;

export function isAuthenticated() {
  return Boolean(getAccessToken());
}

export function logout() {
  clearSession();
  window.location.href = "login.html";
}

/**
 * Fetch the authenticated user's profile from the backend and cache it.
 * Uses a promise cache to prevent duplicate concurrent requests.
 *
 * @returns {Promise<object>} The user's profile.
 * @throws {Error} If the request fails (including after a failed
 *   token refresh, in which case apiFetch will have already redirected
 *   to the login page).
 */
export async function fetchCurrentUser() {
  // If there's already a fetch in progress, return that promise
  if (currentUserPromise) {
    console.log('Using existing fetch promise for user');
    return currentUserPromise;
  }
  
  console.log('Starting new user fetch');
  currentUserPromise = (async () => {
    try {
      const response = await apiFetch("/../auth/me", { method: "GET" });
      if (!response.ok) {
        throw new Error("Unable to load your profile.");
      }
      const user = await response.json();
      setCachedUser(user);
      return user;
    } finally {
      // Clear the promise after it completes
      currentUserPromise = null;
    }
  })();
  
  return currentUserPromise;
}

/**
 * Complete a Google login using an ID token obtained via Google
 * Identity Services, storing the resulting JWTs and caching the user.
 *
 * @param {string} idToken - The Google-issued ID token.
 * @returns {Promise<object>} The authenticated user's profile.
 * @throws {Error} If the backend rejects the ID token.
 */
export async function completeGoogleLogin(idToken) {
  const response = await fetch("/login/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });

  if (!response.ok) {
    let detail = "Google sign-in failed. Please try again.";
    try {
      const body = await response.json();
      if (body && body.detail) {
        detail = body.detail;
      }
    } catch (parseError) {
      // fall back to the generic message
    }
    throw new Error(detail);
  }

  const tokens = await response.json();
  setTokens(tokens.access_token, tokens.refresh_token);

  return fetchCurrentUser();
}

/**
 * Load the public Google OAuth client ID from the backend.
 *
 * @returns {Promise<string>} The Google OAuth client ID.
 * @throws {Error} If the configuration cannot be loaded.
 */
async function fetchGoogleClientId() {
  const response = await fetch("/auth/config");
  if (!response.ok) {
    throw new Error("Unable to load sign-in configuration.");
  }
  const config = await response.json();
  if (!config.google_client_id) {
    throw new Error("Google sign-in is not configured.");
  }
  return config.google_client_id;
}

/**
 * Initialize Google Identity Services and render the Sign in with
 * Google button into the given container element.
 *
 * @param {string} containerId - ID of the element to render the button into.
 * @returns {Promise<void>}
 * @throws {Error} If configuration or the Google script fails to load.
 */
export async function initGoogleSignIn(containerId) {
  const clientId = await fetchGoogleClientId();

  await new Promise((resolve, reject) => {
    const start = Date.now();
    const timeoutMs = 5000;

    (function waitForGoogle() {
      if (window.google && window.google.accounts && window.google.accounts.id) {
        resolve();
        return;
      }
      if (Date.now() - start > timeoutMs) {
        reject(new Error("Google sign-in script failed to load."));
        return;
      }
      setTimeout(waitForGoogle, 100);
    })();
  });

  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: async (response) => {
      try {
        await completeGoogleLogin(response.credential);
        window.location.href = "index.html";
      } catch (error) {
        const errorEl = document.getElementById("login-error");
        if (errorEl) {
          errorEl.textContent =
            error.message || "Google sign-in failed. Please try again.";
          errorEl.classList.remove("hidden");
        }
      }
    },
  });

  window.google.accounts.id.renderButton(
    document.getElementById(containerId),
    { theme: "filled_blue", size: "large", width: 280 }
  );
}