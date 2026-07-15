import { requireAuth } from "./js/guards.js";
import { openFeedbackModal, submitThumbsFeedback } from "./js/feedback.js";
import { renderRatingWidget } from "./js/rating.js";
import { loadHistory } from "./js/history.js";
import { streamQuery, streamVoiceQuery } from "./js/streaming.js";
import { createEventDispatcher } from "./js/events.js";
import { nodeLabel, setActiveNode, setCompleteNode, setProgress } from "./js/progress.js";

const textForm = document.getElementById("text-tab");
const voiceForm = document.getElementById("voice-tab");
const tabButtons = document.querySelectorAll(".tab-button");
const tabContents = document.querySelectorAll(".tab-content");
const questionInput = document.getElementById("question-input");
const audioInput = document.getElementById("audio-input");
const errorBanner = document.getElementById("error-banner");

const streamingPanel = document.getElementById("streaming-panel");
const streamingAnswerText = document.getElementById("streaming-answer-text");
const typingCursor = document.getElementById("typing-cursor");
const transcriptLine = document.getElementById("transcript-line");

const answerPanel = document.getElementById("answer-panel");
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
let currentConversationId = null;

requireAuth();

async function loadComponent(url, containerId) {
  try {
    const response = await fetch(url);
    if (response.ok) {
      document.getElementById(containerId).innerHTML = await response.text();
    }
  } catch (error) {
    // Non-fatal: modal simply won't be available.
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
    if (currentQueryId) submitThumbsFeedback(currentQueryId, true);
  });
}
if (thumbsDownButton) {
  thumbsDownButton.addEventListener("click", () => {
    if (currentQueryId) submitThumbsFeedback(currentQueryId, false);
  });
}
if (commentButton) {
  commentButton.addEventListener("click", () => {
    if (currentQueryId) openFeedbackModal(currentQueryId);
  });
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
}

function clearError() {
  errorBanner.classList.add("hidden");
  errorBanner.textContent = "";
}

function resetStreamingUI({ showTranscript }) {
  streamingPanel.classList.remove("hidden");
  answerPanel.classList.add("hidden");
  citationsPanel.classList.add("hidden");
  evaluationPanel.classList.add("hidden");
  citationsList.innerHTML = "";
  evaluationList.innerHTML = "";
  setProgress(0);
  streamingAnswerText.textContent = "";
  streamingAnswerText.appendChild(typingCursor);
  typingCursor.classList.remove("hidden");
  transcriptLine.classList.toggle("hidden", !showTranscript);
  transcriptLine.textContent = "";
  document.querySelectorAll(".node-badge").forEach((badge) => {
    badge.classList.remove("active", "complete");
  });
}

function appendCitation(data) {
  const item = document.createElement("li");
  item.textContent = `${data.citation} (similarity: ${data.similarity.toFixed(2)})`;
  citationsList.appendChild(item);
  citationsPanel.classList.remove("hidden");
}

function renderEvaluationScores(scores) {
  evaluationList.innerHTML = "";
  Object.entries(scores || {}).forEach(([key, value]) => {
    const term = document.createElement("dt");
    term.textContent = key;
    const definition = document.createElement("dd");
    definition.textContent = String(value);
    evaluationList.appendChild(term);
    evaluationList.appendChild(definition);
  });
  evaluationPanel.classList.remove("hidden");
}

function buildDispatcher() {
  const dispatcher = createEventDispatcher();

  dispatcher.on("node_start", (data) => setActiveNode(data.node));
  dispatcher.on("node_complete", (data) => setCompleteNode(data.node));

  dispatcher.on("progress", (data) => setProgress(data.percent));

  dispatcher.on("tool_start", (data) => {
    setActiveNode("tool_router");
  });

  dispatcher.on("citation", (data) => appendCitation(data));

  dispatcher.on("token", (data) => {
    streamingAnswerText.insertBefore(document.createTextNode(data.content), typingCursor);
  });

  dispatcher.on("evaluation", (data) => {
    if (data.scores) {
      renderEvaluationScores(data.scores);
    }
  });

  dispatcher.on("finished", (data) => {
    typingCursor.classList.add("hidden");
    setProgress(100);
    currentQueryId = data.query_id || null;
    currentConversationId = data.conversation_id || null;
    if (data.transcript) {
      transcriptLine.textContent = `You said: "${data.transcript}"`;
      transcriptLine.classList.remove("hidden");
    }
    answerPanel.classList.remove("hidden");
    if (currentQueryId) {
      renderRatingWidget(ratingContainer, currentQueryId);
    }
  });

  dispatcher.on("error", (data) => {
    typingCursor.classList.add("hidden");
    showError((data && data.detail) || "Something went wrong while streaming.");
  });

  return dispatcher;
}

textForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) {
    showError("Please enter a question.");
    return;
  }

  clearError();
  resetStreamingUI({ showTranscript: false });
  streamQuery(question, currentConversationId, buildDispatcher());
});

voiceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = audioInput.files[0];
  if (!file) {
    showError("Please choose an audio file to upload.");
    return;
  }

  clearError();
  resetStreamingUI({ showTranscript: true });
  await streamVoiceQuery(file, currentConversationId, buildDispatcher());
});