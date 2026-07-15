/**
 * SSE/fetch-streaming client for the real-time agent pipeline.
 *
 * This module is responsible ONLY for opening a stream to
 * `/stream/query` (via `EventSource`, GET) or `/stream/voice` (via
 * `fetch()` + a `ReadableStream` reader, POST — `EventSource` cannot
 * upload a file body) and forwarding parsed events to a dispatcher. It
 * contains no DOM rendering itself; callers (app.js) supply render
 * callbacks via the dispatcher from events.js.
 */

import { getAccessToken } from "./storage.js";
import { createEventDispatcher, parseStreamEvent } from "./events.js";

const API_BASE = "/stream";

/**
 * Stream a text question via SSE (`GET /stream/query`).
 *
 * @param {string} question - The question to ask.
 * @param {string|null} conversationId - Optional existing conversation ID.
 * @param {ReturnType<typeof createEventDispatcher>} dispatcher - Event dispatcher.
 * @returns {EventSource} The underlying EventSource, so callers can close it early.
 */
export function streamQuery(question, conversationId, dispatcher) {
  const token = getAccessToken();
  const params = new URLSearchParams({ question });
  if (conversationId) {
    params.set("conversation_id", conversationId);
  }
  if (token) {
    params.set("token", token);
  }

  const source = new EventSource(`${API_BASE}/query?${params.toString()}`);

  const eventTypes = [
    "token", "node_start", "node_complete", "tool_start", "tool_complete",
    "citation", "evaluation", "progress", "heartbeat", "finished", "error",
  ];

  eventTypes.forEach((eventType) => {
    source.addEventListener(eventType, (rawEvent) => {
      // rawEvent.data is the full JSON-encoded StreamEvent, i.e.
      // {event, data, timestamp} — dispatch it as-is rather than
      // re-wrapping it, or handlers end up receiving the outer
      // envelope instead of the inner payload.
      const parsed = parseStreamEvent(rawEvent.data);
      dispatcher.dispatch(parsed);
      if (eventType === "finished" || eventType === "error") {
        source.close();
      }
    });
  });

  source.onerror = () => {
    dispatcher.dispatch({ event: "error", data: { detail: "Connection lost." } });
    source.close();
  };

  return source;
}

/**
 * Stream a voice question via `fetch()` (`POST /stream/voice`), reading
 * the `text/event-stream` response body manually since `EventSource`
 * cannot send a multipart file upload.
 *
 * @param {File} audioFile - The audio file to upload.
 * @param {string|null} conversationId - Optional existing conversation ID.
 * @param {ReturnType<typeof createEventDispatcher>} dispatcher - Event dispatcher.
 * @returns {Promise<void>}
 */
export async function streamVoiceQuery(audioFile, conversationId, dispatcher) {
  const token = getAccessToken();
  const formData = new FormData();
  formData.append("file", audioFile);
  if (conversationId) {
    formData.append("conversation_id", conversationId);
  }

  const params = new URLSearchParams();
  if (conversationId) {
    params.set("conversation_id", conversationId);
  }

  const response = await fetch(`${API_BASE}/voice?${params.toString()}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!response.ok || !response.body) {
    dispatcher.dispatch({
      event: "error",
      data: { detail: `Stream request failed with status ${response.status}.` },
    });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    const messages = buffer.split("\n\n");
    buffer = messages.pop() || "";

    for (const message of messages) {
      const lines = message.split("\n");
      const dataLine = lines.find((line) => line.startsWith("data: "));
      if (!dataLine) {
        continue;
      }
      // Same fix as above: the data line already contains the full
      // {event, data, timestamp} envelope, so dispatch it directly.
      const parsed = parseStreamEvent(dataLine.replace("data: ", ""));
      dispatcher.dispatch(parsed);
    }
  }
}