"use client";

import { useEffect } from "react";

function getSessionId(): string {
  const KEY = "vp_session_id";
  let id = sessionStorage.getItem(KEY);
  if (!id) {
    id = crypto.randomUUID().replace(/-/g, "");
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
