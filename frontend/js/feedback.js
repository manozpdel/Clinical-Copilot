/**
 * Feedback actions: thumbs up/down, written comments, and
 * hallucination/quality reports.
 *
 * This module is responsible ONLY for calling the `/feedback/*`
 * endpoints. It contains no DOM-rendering logic beyond wiring the
 * feedback modal's own controls; response-card rendering lives in
 * app.js.
 */

import { apiFetch } from "./api.js";
import { showToast } from "./router.js";

let activeQueryId = null;

/**
 * Submit thumbs-up/down feedback for a response.
 *
 * @param {string} queryId - The persisted query ID from the response.
 * @param {boolean} isHelpful - True for thumbs up, false for thumbs down.
 * @returns {Promise<void>}
 */
export async function submitThumbsFeedback(queryId, isHelpful) {
  try {
    const response = await apiFetch("/../feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query_id: queryId, is_helpful: isHelpful }),
    });
    if (!response.ok) {
      throw new Error("Unable to submit feedback.");
    }
    showToast(isHelpful ? "Thanks for the feedback!" : "Thanks, we'll look into it.", "success");
  } catch (error) {
    showToast(error.message || "Unable to submit feedback.", "error");
  }
}

/**
 * Open the feedback modal for a specific response.
 *
 * @param {string} queryId - The persisted query ID from the response.
 */
export function openFeedbackModal(queryId) {
  activeQueryId = queryId;
  document.getElementById("feedback-comment-input").value = "";
  document.getElementById("feedback-report-reason").value = "";
  document.getElementById("feedback-modal").classList.remove("hidden");
}

export function closeFeedbackModal() {
  document.getElementById("feedback-modal").classList.add("hidden");
  activeQueryId = null;
}

export async function submitFeedbackModal() {
  if (!activeQueryId) {
    return;
  }

  const comment = document.getElementById("feedback-comment-input").value.trim();
  const reason = document.getElementById("feedback-report-reason").value;

  try {
    if (comment) {
      const response = await apiFetch("/../feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query_id: activeQueryId, comment }),
      });
      if (!response.ok) {
        throw new Error("Unable to submit comment.");
      }
    }

    if (reason) {
      const response = await apiFetch("/../feedback/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query_id: activeQueryId, reason }),
      });
      if (!response.ok) {
        throw new Error("Unable to submit report.");
      }
    }

    showToast("Feedback submitted. Thank you!", "success");
    closeFeedbackModal();
  } catch (error) {
    showToast(error.message || "Unable to submit feedback.", "error");
  }
}

// Event listeners setup
const cancelButton = document.getElementById("feedback-modal-cancel");
const submitButton = document.getElementById("feedback-modal-submit");

if (cancelButton) {
  cancelButton.addEventListener("click", closeFeedbackModal);
}
if (submitButton) {
  submitButton.addEventListener("click", submitFeedbackModal);
}