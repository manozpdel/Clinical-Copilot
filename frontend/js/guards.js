/**
 * Route protection for pages that require an authenticated session.
 *
 * This module is responsible ONLY for redirecting unauthenticated
 * visitors away from protected pages. It contains no token storage or
 * fetch logic of its own beyond calling into auth.js.
 */

import { fetchCurrentUser, isAuthenticated } from "./auth.js";

/**
 * Require an authenticated session for the current page, redirecting
 * to the login page if the visitor is not authenticated or their
 * session cannot be validated against the backend.
 *
 * @returns {Promise<boolean>} True if the visitor is authenticated.
 */
export async function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = "login.html";
    return false;
  }

  try {
    await fetchCurrentUser();
    return true;
  } catch (error) {
    // fetchCurrentUser/apiFetch already redirects to login.html on
    // an unrecoverable 401; this catch only guards against unexpected
    // errors so the page doesn't silently continue rendering.
    return false;
  }
}

requireAuth();