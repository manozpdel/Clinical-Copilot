/**
 * Profile page rendering logic.
 *
 * This module is responsible ONLY for fetching and displaying the
 * current user's profile. Route protection is handled by guards.js;
 * navigation chrome is handled by router.js.
 */

import { showToast } from "./router.js";
import { getCachedUser } from "./storage.js";  // Use cached user data

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
    // Use cached user data (already fetched by guards.js)
    const user = getCachedUser();
    
    if (!user) {
      // Fallback: fetch if not cached (shouldn't happen normally)
      console.warn('No cached user found, fetching fresh...');
      const { fetchCurrentUser } = await import("./auth.js");
      const freshUser = await fetchCurrentUser();
      displayUser(freshUser);
      return;
    }
    
    console.log('Using cached user data for profile');
    displayUser(user);
    
  } catch (error) {
    console.error('Profile error:', error);
    loadingEl.classList.add("hidden");
    errorEl.textContent = error.message || "Unable to load your profile.";
    errorEl.classList.remove("hidden");
    showToast("Unable to load your profile.", "error");
  }
}

function displayUser(user) {
  const nameEl = document.getElementById("profile-name");
  const emailEl = document.getElementById("profile-email");
  const providerEl = document.getElementById("profile-provider");
  const createdEl = document.getElementById("profile-created");
  
  if (nameEl) nameEl.textContent = user.full_name || "—";
  if (emailEl) emailEl.textContent = user.email || "No email";
  if (providerEl) providerEl.textContent = 
    user.provider === "google" ? "Google" : "Email & password";
  if (createdEl) createdEl.textContent = formatDate(user.created_at);
  
  loadingEl.classList.add("hidden");
  cardEl.classList.remove("hidden");
}

// Execute on page load
document.addEventListener('DOMContentLoaded', renderProfile);