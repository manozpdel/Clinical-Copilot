import { apiFetch } from "./js/api.js";
import { requireAuth } from "./js/guards.js";

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

requireAuth();

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    tabButtons.forEach((btn) => btn.classList.remove("active"));
    tabContents.forEach((content) => content.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.tab).classList.add("active");
  });
});

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