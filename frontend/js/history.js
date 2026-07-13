/**
 * Conversation/feedback history panel and response comparison.
 *
 * This module is responsible ONLY for fetching and rendering
 * `/feedback/history` and `/feedback/compare` data. It contains no
 * feedback-submission logic (see feedback.js/rating.js).
 */

import { apiFetch } from "./api.js";
import { showToast } from "./router.js";

let selectedForComparison = [];

/**
 * Fetch the current user's history and render it into the given panel.
 *
 * @param {HTMLElement} panel - Container element to render items into.
 */
export async function loadHistory(panel) {
  panel.innerHTML = "<p>Loading history...</p>";

  try {
    const response = await apiFetch("/../feedback/history");
    if (!response.ok) {
      throw new Error("Unable to load history.");
    }
    const items = await response.json();
    renderHistory(panel, items);
  } catch (error) {
    panel.innerHTML = `<p class="error-banner">${error.message}</p>`;
  }
}

function renderHistory(panel, items) {
  panel.innerHTML = "";

  if (items.length === 0) {
    panel.innerHTML = "<p>No conversation history yet.</p>";
    return;
  }

  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "history-item";

    const question = document.createElement("p");
    question.className = "history-question";
    question.textContent = item.query_text;

    const answer = document.createElement("p");
    answer.className = "history-answer";
    answer.textContent = item.response_text;

    const meta = document.createElement("p");
    meta.className = "history-meta";
    const ratingText = item.rating ? `${item.rating.stars}★` : "unrated";
    const feedbackText = item.feedback
      ? item.feedback.is_helpful
        ? "👍"
        : item.feedback.is_helpful === false
          ? "👎"
          : ""
      : "";
    meta.textContent = `${new Date(item.created_at).toLocaleString()} · ${ratingText} ${feedbackText}`;

    const compareCheckbox = document.createElement("input");
    compareCheckbox.type = "checkbox";
    compareCheckbox.className = "history-compare-checkbox";
    compareCheckbox.addEventListener("change", () => toggleComparisonSelection(item.query_id, compareCheckbox));

    const compareLabel = document.createElement("label");
    compareLabel.className = "history-compare-label";
    compareLabel.appendChild(compareCheckbox);
    compareLabel.appendChild(document.createTextNode(" select to compare"));

    card.appendChild(question);
    card.appendChild(answer);
    card.appendChild(meta);
    card.appendChild(compareLabel);
    panel.appendChild(card);
  });
}

function toggleComparisonSelection(queryId, checkbox) {
  if (checkbox.checked) {
    if (selectedForComparison.length >= 2) {
      checkbox.checked = false;
      showToast("You can only compare two responses at a time.", "error");
      return;
    }
    selectedForComparison.push(queryId);
  } else {
    selectedForComparison = selectedForComparison.filter((id) => id !== queryId);
  }

  if (selectedForComparison.length === 2) {
    openComparison(selectedForComparison[0], selectedForComparison[1]);
    selectedForComparison = [];
  }
}

/**
 * Fetch and display a side-by-side comparison of two responses.
 *
 * @param {string} queryIdA - The first query ID.
 * @param {string} queryIdB - The second query ID.
 */
export async function openComparison(queryIdA, queryIdB) {
  try {
    const response = await apiFetch(
      `/../feedback/compare?query_id_a=${encodeURIComponent(queryIdA)}&query_id_b=${encodeURIComponent(queryIdB)}`
    );
    if (!response.ok) {
      throw new Error("Unable to load comparison.");
    }
    const data = await response.json();
    renderComparison(data);
  } catch (error) {
    showToast(error.message || "Unable to load comparison.", "error");
  }
}

function renderComparison(data) {
  document.getElementById("comparison-answer-a").textContent = data.response_a.response_text;
  document.getElementById("comparison-answer-b").textContent = data.response_b.response_text;
  document.getElementById("comparison-timestamp-a").textContent = new Date(
    data.response_a.created_at
  ).toLocaleString();
  document.getElementById("comparison-timestamp-b").textContent = new Date(
    data.response_b.created_at
  ).toLocaleString();
  document.getElementById("comparison-meta-a").textContent = `Faithfulness: ${
    data.response_a.evaluation?.faithfulness ?? "n/a"
  }`;
  document.getElementById("comparison-meta-b").textContent = `Faithfulness: ${
    data.response_b.evaluation?.faithfulness ?? "n/a"
  }`;
  document.getElementById("comparison-modal").classList.remove("hidden");
}

document.addEventListener("DOMContentLoaded", () => {
  const closeButton = document.getElementById("comparison-modal-close");
  if (closeButton) {
    closeButton.addEventListener("click", () => {
      document.getElementById("comparison-modal").classList.add("hidden");
    });
  }
});