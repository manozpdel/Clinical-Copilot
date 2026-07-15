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
  const commentInput = document.getElementById("feedback-comment-input");
  const reasonSelect = document.getElementById("feedback-report-reason");
  const modal = document.getElementById("feedback-modal");
  
  if (!modal) {
    console.error("Feedback modal not found in DOM");
    showToast("Feedback system unavailable. Please try again.", "error");
    return;
  }
  
  if (commentInput) commentInput.value = "";
  if (reasonSelect) reasonSelect.value = "";
  modal.classList.remove("hidden");
}

/**
 * Close the feedback modal.
 */
export function closeFeedbackModal() {
  const modal = document.getElementById("feedback-modal");
  if (modal) {
    modal.classList.add("hidden");
  }
  activeQueryId = null;
}

/**
 * Submit the feedback from the modal.
 */
export async function submitFeedbackModal() {
  if (!activeQueryId) {
    showToast("No active query to submit feedback for.", "error");
    return;
  }

  const commentInput = document.getElementById("feedback-comment-input");
  const reasonSelect = document.getElementById("feedback-report-reason");
  
  if (!commentInput || !reasonSelect) {
    showToast("Feedback form not available.", "error");
    return;
  }

  const comment = commentInput.value.trim();
  const reason = reasonSelect.value;

  try {
    let hasError = false;

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

/**
 * Setup event listeners for the feedback modal.
 * This function should be called after the DOM is ready.
 */
export function setupFeedbackEventListeners() {
  const cancelButton = document.getElementById("feedback-modal-cancel");
  const submitButton = document.getElementById("feedback-modal-submit");

  if (cancelButton) {
    // Remove any existing listeners to avoid duplicates
    cancelButton.removeEventListener("click", closeFeedbackModal);
    cancelButton.addEventListener("click", closeFeedbackModal);
  } else {
    console.warn("Feedback modal cancel button not found in DOM");
  }

  if (submitButton) {
    // Remove any existing listeners to avoid duplicates
    submitButton.removeEventListener("click", submitFeedbackModal);
    submitButton.addEventListener("click", submitFeedbackModal);
  } else {
    console.warn("Feedback modal submit button not found in DOM");
  }
}

// ✅ FIX: Wait for DOM to be fully loaded before attaching event listeners
if (document.readyState === "loading") {
  // Document is still loading, wait for DOMContentLoaded
  document.addEventListener("DOMContentLoaded", setupFeedbackEventListeners);
} else {
  // Document is already loaded, setup immediately
  setupFeedbackEventListeners();
}

// ✅ FIX: Also handle dynamic modal injection (if the modal is added later)
// Use MutationObserver to detect when modal is added to DOM
if (window.MutationObserver) {
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      mutation.addedNodes.forEach(function(node) {
        // Check if the added node is the feedback modal or contains it
        if (node.nodeType === 1) { // Element node
          if (node.id === "feedback-modal" || node.querySelector("#feedback-modal")) {
            setupFeedbackEventListeners();
          }
        }
      });
    });
  });

  // Start observing once the document body exists
  if (document.body) {
    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  } else {
    document.addEventListener("DOMContentLoaded", function() {
      observer.observe(document.body, {
        childList: true,
        subtree: true
      });
    });
  }
}

// Export a cleanup function in case the module is hot-reloaded
export function cleanupFeedbackEventListeners() {
  const cancelButton = document.getElementById("feedback-modal-cancel");
  const submitButton = document.getElementById("feedback-modal-submit");
  
  if (cancelButton) {
    cancelButton.removeEventListener("click", closeFeedbackModal);
  }
  if (submitButton) {
    submitButton.removeEventListener("click", submitFeedbackModal);
  }
}

// For debugging - log when module is loaded
console.log("Feedback module loaded successfully");