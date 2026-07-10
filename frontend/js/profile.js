/**
 * Profile page rendering logic.
 *
 * This module is responsible ONLY for fetching and displaying the
 * current user's profile. Route protection is handled by guards.js;
 * navigation chrome is handled by router.js.
 */

import { fetchCurrentUser } from "./auth.js";
import { showToast } from "./router.js";

const loadingEl = document.getElementById("profile-loading");
const cardEl = document.getElementById("profile-card");
const errorEl = document.getElementById("profile-error");

function formatDate(isoString) {
  try {
    return new Date(isoString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch (error) {
    return isoString;
  }
}

async function renderProfile() {
  try {
    const user = await fetchCurrentUser();

    document.getElementById("profile-name").textContent =
      user.full_name || "—";
    document.getElementById("profile-email").textContent = user.email;
    document.getElementById("profile-provider").textContent =
      user.provider === "google" ? "Google" : "Email & password";
    document.getElementById("profile-created").textContent = formatDate(
      user.created_at
    );

    loadingEl.classList.add("hidden");
    cardEl.classList.remove("hidden");
  } catch (error) {
    loadingEl.classList.add("hidden");
    errorEl.textContent = error.message || "Unable to load your profile.";
    errorEl.classList.remove("hidden");
    showToast("Unable to load your profile.", "error");
  }
}

renderProfile();