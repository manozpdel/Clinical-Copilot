/**
 * Shared navigation chrome: renders auth-aware nav state, the user
 * menu dropdown, and toast notifications.
 *
 * This module is responsible ONLY for UI rendering tied to
 * authentication state. It contains no fetch or token logic beyond
 * reading the cached user and calling logout().
 */

import { logout } from "./auth.js";
import { getCachedUser, getAccessToken } from "./storage.js";

/**
 * Show a transient toast notification.
 *
 * @param {string} message - The message to display.
 * @param {"error"|"success"} [type] - The toast style.
 */
export function showToast(message, type = "error") {
  const container = document.getElementById("toast-container");
  if (!container) {
    return;
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function initialsFor(name, email) {
  const source = (name || email || "?").trim();
  return source.charAt(0).toUpperCase();
}

function renderNav() {
  const navAuthenticated = document.getElementById("nav-authenticated");
  const navUnauthenticated = document.getElementById("nav-unauthenticated");
  if (!navAuthenticated || !navUnauthenticated) {
    return;
  }

  const isLoggedIn = Boolean(getAccessToken());
  navAuthenticated.classList.toggle("hidden", !isLoggedIn);
  navUnauthenticated.classList.toggle("hidden", isLoggedIn);

  if (!isLoggedIn) {
    return;
  }

  const user = getCachedUser();
  const nameEl = document.getElementById("user-name");
  const emailEl = document.getElementById("user-email");
  const avatarEl = document.getElementById("user-avatar");

  if (user && nameEl) {
    nameEl.textContent = user.full_name || user.email;
  }
  if (user && emailEl) {
    emailEl.textContent = user.email;
  }
  if (user && avatarEl) {
    avatarEl.textContent = initialsFor(user.full_name, user.email);
  }

  const menuButton = document.getElementById("user-menu-button");
  const dropdown = document.getElementById("user-dropdown");
  if (menuButton && dropdown) {
    menuButton.addEventListener("click", () => {
      dropdown.classList.toggle("hidden");
    });
    document.addEventListener("click", (event) => {
      if (!menuButton.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.classList.add("hidden");
      }
    });
  }

  const logoutButton = document.getElementById("logout-button");
  if (logoutButton) {
    logoutButton.addEventListener("click", () => {
      logout();
    });
  }
}

renderNav();