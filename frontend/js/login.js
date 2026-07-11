/**
 * Login page bootstrap logic.
 *
 * This module is responsible ONLY for wiring up the login page: it
 * redirects already-authenticated visitors and initializes Google
 * Identity Services. All actual auth logic lives in auth.js.
 */

import { isAuthenticated, initGoogleSignIn } from "./auth.js";

const loadingEl = document.getElementById("login-loading");
const buttonContainer = document.getElementById("google-button-container");
const errorEl = document.getElementById("login-error");

function showLoginError(message) {
  errorEl.textContent = message;
  errorEl.classList.remove("hidden");
}

async function init() {
  if (isAuthenticated()) {
    window.location.href = "index.html";
    return;
  }

  try {
    await initGoogleSignIn("google-button-container");
    loadingEl.classList.add("hidden");
    buttonContainer.classList.remove("hidden");
  } catch (error) {
    loadingEl.classList.add("hidden");
    showLoginError(
      error.message || "Unable to load sign-in. Please try again."
    );
  }
}

init();