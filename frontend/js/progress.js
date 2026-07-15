/**
 * Progress bar and node-status rendering.
 *
 * This module is responsible ONLY for updating the progress bar fill
 * and node-status badges in the DOM. It contains no event-parsing or
 * transport logic.
 */

const NODE_LABELS = {
  planner: "Planning...",
  tool_router: "Retrieving Context...",
  transcriber: "Transcribing Audio...",
  generator: "Generating Answer...",
  evaluator: "Evaluating Response...",
};

/**
 * Update the progress bar fill percentage.
 *
 * @param {number} percent - Completion percent, 0-100.
 */
export function setProgress(percent) {
  const fill = document.getElementById("progress-bar-fill");
  if (fill) {
    fill.style.width = `${Math.min(Math.max(percent, 0), 100)}%`;
  }
}

/**
 * Mark a node as active in the node-status row.
 *
 * @param {string} node - The node name (e.g. "planner", "generator").
 */
export function setActiveNode(node) {
  const container = document.getElementById("node-status");
  if (!container) {
    return;
  }
  container.querySelectorAll(".node-badge").forEach((badge) => {
    badge.classList.toggle("active", badge.dataset.node === node);
    badge.classList.remove("complete");
  });
}

/**
 * Mark a node as complete in the node-status row.
 *
 * @param {string} node - The node name.
 */
export function setCompleteNode(node) {
  const container = document.getElementById("node-status");
  if (!container) {
    return;
  }
  const badge = container.querySelector(`.node-badge[data-node="${node}"]`);
  if (badge) {
    badge.classList.remove("active");
    badge.classList.add("complete");
  }
}

/**
 * Return a human-readable label for a node name.
 *
 * @param {string} node - The node name.
 * @returns {string}
 */
export function nodeLabel(node) {
  return NODE_LABELS[node] || node;
}