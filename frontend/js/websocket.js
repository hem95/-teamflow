// ── WebSocket Client ───────────────────────────────────────────────────────
// This file manages the live connection to the server.
// When a message arrives, we display it instantly — no page refresh needed.

let ws = null;
let typingTimer = null;
let reconnectDelay = 1000;  // start at 1s, grows with each failed reconnect

function connectWS(channelId) {
  const token = localStorage.getItem("access_token");
  if (!token) return;

  // Use ws:// for local dev, wss:// (secure) for production
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${location.host}/ws/channels/${channelId}?token=${token}`;

  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log(`[WS] Connected to channel ${channelId}`);
    reconnectDelay = 1000;  // reset backoff on successful connect
  };

  ws.onmessage = (event) => {
    const payload = JSON.parse(event.data);

    switch (payload.type) {
      case "message":
        handleIncomingMessage(payload);
        break;

      case "typing":
        showTypingIndicator(payload.user_id);
        break;

      case "user_joined":
        console.log(`[WS] User ${payload.user_id} joined, online: ${payload.online_count}`);
        break;

      case "user_left":
        console.log(`[WS] User ${payload.user_id} left, online: ${payload.online_count}`);
        break;

      case "pong":
        // Server acknowledged our ping — connection is alive
        break;

      case "error":
        console.error("[WS] Server error:", payload.detail);
        break;
    }
  };

  ws.onerror = (err) => {
    console.error("[WS] Error:", err);
  };

  ws.onclose = (event) => {
    ws = null;
    if (event.code === 4001 || event.code === 4003) {
      // Auth error or not a member — don't reconnect
      console.warn("[WS] Closed due to auth/permission error");
      return;
    }
    // Reconnect with exponential backoff (1s → 2s → 4s → 8s max)
    console.log(`[WS] Disconnected, reconnecting in ${reconnectDelay}ms...`);
    setTimeout(() => {
      if (state.activeChannel?.id === channelId) {
        connectWS(channelId);
      }
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 8000);
  };

  // Send a ping every 30s to keep the connection alive through firewalls/proxies
  setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "ping" }));
    }
  }, 30_000);
}

function disconnectWS() {
  if (ws) {
    ws.close(1000, "Channel switch");
    ws = null;
  }
}

function sendViaWS(payload) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
    return true;
  }
  return false;  // caller should fall back to HTTP
}

function handleIncomingMessage(payload) {
  // Don't duplicate messages we sent ourselves via WebSocket
  // (the server broadcasts back to all including sender)
  if (document.getElementById(`msg-${payload.id}`)) return;

  appendMessage(payload);
  scrollToBottom();
}

// ── Typing Indicator ──────────────────────────────────────────────────────
let typingUsers = new Set();
let typingTimeout = null;

function showTypingIndicator(userId) {
  if (userId === state.user?.id) return;
  typingUsers.add(userId);
  updateTypingIndicator();

  // Clear after 3s with no new "typing" events
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => {
    typingUsers.clear();
    updateTypingIndicator();
  }, 3000);
}

function updateTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (typingUsers.size === 0) {
    el.classList.add("hidden");
  } else {
    el.textContent = `${typingUsers.size} person${typingUsers.size > 1 ? "s" : ""} typing...`;
    el.classList.remove("hidden");
  }
}

function sendTyping() {
  // Throttle: only send a typing event once per second
  if (typingTimer) return;
  sendViaWS({ type: "typing" });
  typingTimer = setTimeout(() => { typingTimer = null; }, 1000);
}
