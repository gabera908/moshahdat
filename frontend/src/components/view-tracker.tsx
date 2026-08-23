"use client";

import { useEffect } from "react";

/**
 * crypto.randomUUID() is secure-context-only — unavailable on plain HTTP
 * (e.g. http://192.168.x.x). Build an id from getRandomValues instead.
 */
function randomId(): string {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    if (typeof crypto !== "undefined" && crypto.getRandomValues) {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    }
  } catch {
    /* fall through */
  }
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

function getSessionId(): string {
  const KEY = "vp_session_id";
  let id = sessionStorage.getItem(KEY);
  if (!id) {
    id = randomId();
    sessionStorage.setItem(KEY, id);
  }
  return id;
}

/**
 * Counts one view per browser session per hour (server-side dedupe).
 * Renders nothing.
 */
export default function ViewTracker({ videoId }: { videoId: number }) {
  useEffect(() => {
    const key = `viewed_${videoId}`;
    if (sessionStorage.getItem(key)) return;

    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/videos/${videoId}/view`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: getSessionId() }),
    })
      .then((res) => (res.ok ? sessionStorage.setItem(key, "1") : null))
      .catch(() => null); // silent: counting must never disturb viewing
  }, [videoId]);

  return null;
}
