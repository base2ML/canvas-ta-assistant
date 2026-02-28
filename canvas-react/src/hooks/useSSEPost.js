// Source: React docs pattern for external system synchronization + AbortController
import { useCallback, useRef } from 'react';
import { BACKEND_URL } from '../api';

export function useSSEPost() {
  const abortRef = useRef(null);

  const startPosting = useCallback(async (assignmentId, requestBody, handlers) => {
    // handlers: { onStarted, onProgress, onPosted, onSkipped, onError, onDry_run, onComplete, onCancelled }
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    let response;
    try {
      response = await fetch(
        `${BACKEND_URL}/api/comments/post/${assignmentId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
          signal,
        }
      );
    } catch (err) {
      if (err.name === 'AbortError') return;
      throw err;
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE lines: "event: name\ndata: json\n\n"
        const messages = buffer.split('\n\n');
        buffer = messages.pop(); // last partial chunk kept

        for (const message of messages) {
          const lines = message.split('\n');
          let eventType = 'message';
          let data = '';
          for (const line of lines) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            if (line.startsWith('data: ')) data = line.slice(6).trim();
          }
          if (!data) continue;
          const parsed = JSON.parse(data);
          // Map event name to handler: capitalize first letter and prepend "on"
          // Special case: "dry_run" -> "onDry_run" (preserve underscore)
          const handlerKey = `on${eventType.charAt(0).toUpperCase() + eventType.slice(1)}`;
          const handler = handlers[handlerKey];
          if (handler) handler(parsed);
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      throw err;
    }
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { startPosting, cancel };
}
