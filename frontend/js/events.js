/**
 * Stream event parsing/dispatch.
 *
 * This module is responsible ONLY for parsing raw SSE/WebSocket
 * message text into structured events and dispatching them to
 * registered handlers by event type. It contains no DOM rendering
 * (see progress.js and streaming.js's own renderers) or transport
 * connection logic.
 */

/**
 * Parse a raw event payload (already-decoded JSON string) into a
 * {event, data, timestamp} object.
 *
 * @param {string} rawJson - The JSON-encoded event payload.
 * @returns {{event: string, data: object, timestamp: string} | null}
 */
export function parseStreamEvent(rawJson) {
  try {
    return JSON.parse(rawJson);
  } catch (error) {
    return null;
  }
}

/**
 * Create a simple dispatcher: register handlers per event type, then
 * feed it parsed events to invoke the matching handler.
 *
 * @returns {{on: Function, dispatch: Function}}
 */
export function createEventDispatcher() {
  const handlers = {};

  return {
    on(eventType, handler) {
      handlers[eventType] = handler;
    },
    dispatch(event) {
      if (!event || !event.event) {
        return;
      }
      const handler = handlers[event.event];
      if (handler) {
        handler(event.data || {});
      }
    },
  };
}