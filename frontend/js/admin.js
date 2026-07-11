/**
 * Admin dashboard rendering logic.
 *
 * This module is responsible ONLY for fetching and displaying
 * `/feedback/analytics`, and triggering `/feedback/export` downloads.
 * Route protection is handled by guards.js; navigation chrome by
 * router.js. Non-admin users receive a clear 403 message rather than
 * a silent failure, since `/feedback/analytics` and `/feedback/export`
 * are gated server-side by `feedback.dependencies.require_admin`.
 */

import { apiFetch } from "./api.js";
import { showToast } from "./router.js";

const loadingEl = document.getElementById("admin-loading");
const errorEl = document.getElementById("admin-error");
const contentEl = document.getElementById("admin-content");

function showAdminError(message) {
  loadingEl.classList.add("hidden");
  errorEl.textContent = message;
  errorEl.classList.remove("hidden");
}

function renderStats(data) {
  document.getElementById("stat-average-rating").textContent =
    data.average_rating !== null ? data.average_rating.toFixed(2) : "—";
  document.getElementById("stat-positive").textContent = `${data.positive_percent.toFixed(1)}%`;
  document.getElementById("stat-negative").textContent = `${data.negative_percent.toFixed(1)}%`;
  document.getElementById("stat-total-feedback").textContent = data.total_feedback;
  document.getElementById("stat-total-ratings").textContent = data.total_ratings;
}

function renderReportsByReason(data) {
  const container = document.getElementById("reports-by-reason");
  const emptyMessage = document.getElementById("reports-empty");
  container.innerHTML = "";

  const entries = Object.entries(data.hallucination_reports_by_reason || {});
  if (entries.length === 0) {
    emptyMessage.classList.remove("hidden");
    return;
  }
  emptyMessage.classList.add("hidden");

  entries.forEach(([reason, count]) => {
    const term = document.createElement("dt");
    term.textContent = reason.replace(/_/g, " ");
    const definition = document.createElement("dd");
    definition.textContent = String(count);
    container.appendChild(term);
    container.appendChild(definition);
  });
}

function renderCommonIssues(data) {
  const list = document.getElementById("common-issues-list");
  const emptyMessage = document.getElementById("issues-empty");
  list.innerHTML = "";

  if (!data.most_common_issues || data.most_common_issues.length === 0) {
    emptyMessage.classList.remove("hidden");
    return;
  }
  emptyMessage.classList.add("hidden");

  data.most_common_issues.forEach((issue) => {
    const item = document.createElement("li");
    item.textContent = issue.replace(/_/g, " ");
    list.appendChild(item);
  });
}

function renderTrend(data) {
  const chart = document.getElementById("trend-chart");
  const emptyMessage = document.getElementById("trend-empty");
  chart.innerHTML = "";

  if (!data.daily_trend || data.daily_trend.length === 0) {
    emptyMessage.classList.remove("hidden");
    return;
  }
  emptyMessage.classList.add("hidden");

  const maxCount = Math.max(...data.daily_trend.map((point) => point.count));

  data.daily_trend.forEach((point) => {
    const bar = document.createElement("div");
    bar.className = "trend-bar";
    const heightPercent = maxCount > 0 ? (point.count / maxCount) * 100 : 0;
    bar.style.height = `${Math.max(heightPercent, 4)}%`;
    bar.title = `${point.date}: ${point.count}`;
    chart.appendChild(bar);
  });
}

async function loadAnalytics() {
  try {
    const response = await apiFetch("/../feedback/analytics");

    if (response.status === 403) {
      showAdminError("You do not have administrator access to view this page.");
      return;
    }
    if (!response.ok) {
      throw new Error("Unable to load analytics.");
    }

    const data = await response.json();

    renderStats(data);
    renderReportsByReason(data);
    renderCommonIssues(data);
    renderTrend(data);

    loadingEl.classList.add("hidden");
    contentEl.classList.remove("hidden");
  } catch (error) {
    showAdminError(error.message || "Unable to load analytics.");
  }
}

async function downloadExport(format) {
  try {
    const response = await apiFetch(`/../feedback/export?format=${format}`);

    if (response.status === 403) {
      showToast("You do not have administrator access to export feedback.", "error");
      return;
    }
    if (!response.ok) {
      throw new Error("Export failed.");
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = format === "csv" ? "feedback_export.csv" : "feedback_export.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    showToast(`Downloaded feedback_export.${format}`, "success");
  } catch (error) {
    showToast(error.message || "Export failed.", "error");
  }
}

document.getElementById("export-json-button").addEventListener("click", () => downloadExport("json"));
document.getElementById("export-csv-button").addEventListener("click", () => downloadExport("csv"));

loadAnalytics();