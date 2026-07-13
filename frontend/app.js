import { apiFetch } from "./js/api.js";
import { requireAuth } from "./js/guards.js";
import { openFeedbackModal, submitThumbsFeedback } from "./js/feedback.js";
import { renderRatingWidget } from "./js/rating.js";
import { loadHistory } from "./js/history.js";

const textForm = document.getElementById("text-tab");
const voiceForm = document.getElementById("voice-tab");
const tabButtons = document.querySelectorAll(".tab-button");
const tabContents = document.querySelectorAll(".tab-content");
const questionInput = document.getElementById("question-input");
const audioInput = document.getElementById("audio-input");
const loadingIndicator = document.getElementById("loading-indicator");
const errorBanner = document.getElementById("error-banner");
const transcriptPanel = document.getElementById("transcript-panel");
const transcriptText = document.getElementById("transcript-text");
const answerPanel = document.getElementById("answer-panel");
const answerText = document.getElementById("answer-text");
const citationsPanel = document.getElementById("citations-panel");
const citationsList = document.getElementById("citations-list");
const evaluationPanel = document.getElementById("evaluation-panel");
const evaluationList = document.getElementById("evaluation-list");
const ratingContainer = document.getElementById("rating-container");
const thumbsUpButton = document.getElementById("thumbs-up-button");
const thumbsDownButton = document.getElementById("thumbs-down-button");
const commentButton = document.getElementById("comment-button");
const historyPanel = document.getElementById("history-panel");
const openHistoryButton = document.getElementById("open-history-button");

let currentQueryId = null;

requireAuth();

// Load shared feedback modal / comparison modal markup by fetching the
// component partials once, so they're available without duplicating
// markup across every page.
async function loadComponent(url, containerId) {
  try {
    const response = await fetch(url);
    if (response.ok) {
      document.getElementById(containerId).innerHTML = await response.text();
    }
  } catch (error) {
    // Non-fatal: feedback modal simply won't be available.
  }
}
loadComponent("components/feedback_modal.html", "feedback-modal-container");
loadComponent("components/comparison_modal.html", "comparison-modal-container");

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    tabButtons.forEach((btn) => btn.classList.remove("active"));
    tabContents.forEach((content) => content.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
  });
});

if (openHistoryButton) {
  openHistoryButton.addEventListener("click", () => {
    historyPanel.classList.toggle("hidden");
    if (!historyPanel.classList.contains("hidden")) {
      loadHistory(document.getElementById("history-list"));
    }
  });
}

if (thumbsUpButton) {
  thumbsUpButton.addEventListener("click", () => {
    if (currentQueryId) {
      submitThumbsFeedback(currentQueryId, true);
    }
  });
}
if (thumbsDownButton) {
  thumbsDownButton.addEventListener("click", () => {
    if (currentQueryId) {
      submitThumbsFeedback(currentQueryId, false);
    }
  });
}
if (commentButton) {
  commentButton.addEventListener("click", () => {
    if (currentQueryId) {
      openFeedbackModal(currentQueryId);
    }
  });
}

function setLoading(isLoading) {
  loadingIndicator.classList.toggle("hidden", !isLoading);
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}

function clearError() {
  errorBanner.classList.add("hidden");
  errorBanner.textContent = "";
}

function hideResults() {
  transcriptPanel.classList.add("hidden");
  answerPanel.classList.add("hidden");
  citationsPanel.classList.add("hidden");
  evaluationPanel.classList.add("hidden");
}

function renderCitations(citations) {
  citationsList.innerHTML = "";
  if (!citations || citations.length === 0) {
    citationsPanel.classList.add("hidden");
    return;
  }
  citations.forEach((citation) => {
    const item = document.createElement("li");
    item.textContent = citation;
    citationsList.appendChild(item);
  });
  citationsPanel.classList.remove("hidden");
}

function renderEvaluation(evaluation) {
  evaluationList.innerHTML = "";
  if (!evaluation) {
    evaluationPanel.classList.add("hidden");
    return;
  }
  Object.entries(evaluation).forEach(([key, value]) => {
    const term = document.createElement("dt");
    term.textContent = key;
    const definition = document.createElement("dd");
    definition.textContent = String(value);
    evaluationList.appendChild(term);
    evaluationList.appendChild(definition);
  });
  evaluationPanel.classList.remove("hidden");
}

function renderResult(result, { showTranscript }) {
  if (showTranscript) {
    transcriptText.textContent = result.transcript || "";
    transcriptPanel.classList.remove("hidden");
  }
  answerText.textContent = result.answer || "";
  answerPanel.classList.remove("hidden");
  renderCitations(result.citations);
  renderEvaluation(result.evaluation);

  currentQueryId = result.query_id || null;
  if (currentQueryId) {
    renderRatingWidget(ratingContainer, currentQueryId);
  }
}

async function handleResponse(response) {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`;
    try {
      const body = await response.json();
      if (body && body.detail) {
        detail = Array.isArray(body.detail)
          ? body.detail.map((item) => item.msg).join(", ")
          : body.detail;
      }
    } catch (parseError) {
      // fall back to the generic status message
    }
    throw new Error(detail);
  }
  return response.json();
}

textForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) {
    showError("Please enter a question.");
    return;
  }

  clearError();
  hideResults();
  setLoading(true);

  try {
    const response = await apiFetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const result = await handleResponse(response);
    renderResult(result, { showTranscript: false });
  } catch (error) {
    showError(error.message || "Something went wrong. Please try again.");
  } finally {
    setLoading(false);
  }
});

voiceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = audioInput.files[0];
  if (!file) {
    showError("Please choose an audio file to upload.");
    return;
  }

  clearError();
  hideResults();
  setLoading(true);

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiFetch("/voice", {
      method: "POST",
      body: formData,
    });
    const result = await handleResponse(response);
    renderResult(result, { showTranscript: true });
  } catch (error) {
    showError(error.message || "Something went wrong. Please try again.");
  } finally {
    setLoading(false);
  }
});