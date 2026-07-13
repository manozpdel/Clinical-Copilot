/**
 * Star rating widget rendering and submission.
 *
 * This module is responsible ONLY for rendering a 1-5 star widget and
 * submitting the selected rating to `/feedback/rating`. It contains
 * no other feedback logic.
 */

import { apiFetch } from "./api.js";
import { showToast } from "./router.js";

/**
 * Render a star rating widget into a container element.
 *
 * @param {HTMLElement} container - Element to render the widget into.
 * @param {string} queryId - The persisted query ID to rate.
 */
export function renderRatingWidget(container, queryId) {
  container.innerHTML = "";
  container.dataset.queryId = queryId;
  container.classList.add("rating-widget");

  for (let value = 1; value <= 5; value += 1) {
    const star = document.createElement("button");
    star.type = "button";
    star.className = "star";
    star.textContent = "★";
    star.dataset.value = String(value);
    star.setAttribute("aria-label", `${value} star${value > 1 ? "s" : ""}`);
    star.addEventListener("click", () => handleStarClick(container, queryId, value));
    container.appendChild(star);
  }
}

function highlightStars(container, stars) {
  container.querySelectorAll(".star").forEach((star) => {
    const value = Number(star.dataset.value);
    star.classList.toggle("selected", value <= stars);
  });
}

async function handleStarClick(container, queryId, stars) {
  highlightStars(container, stars);

  try {
    const response = await apiFetch("/../feedback/rating", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query_id: queryId, stars }),
    });
    if (!response.ok) {
      throw new Error("Unable to submit rating.");
    }
    showToast(`Rated ${stars} star${stars > 1 ? "s" : ""}.`, "success");
  } catch (error) {
    showToast(error.message || "Unable to submit rating.", "error");
  }
}