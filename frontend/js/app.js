// ── State ─────────────────────────────────────────────────────────────────
const API = ""; // same origin — frontend and backend both on port 8000
let state = {
  user:            null,
  workspaces:      [],
  channels:        [],
  activeWorkspace: null,
  activeChannel:   null,
  activeThreadId:  null,   // for threaded replies
};

// ── Bootstrap ─────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", async () => {
  const token = localStorage.getItem("access_token");
  if (!token) { window.location.href = "/index.html"; return; }

  state.user = JSON.parse(localStorage.getItem("user") || "null");
  if (!state.user) { window.location.href = "/index.html"; return; }

  renderUserInfo();
  await loadWorkspaces();
});

// ── API Helper ────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
      ...(opts.headers || {}),
    },
  });

  // If 401, try to refresh the token automatically
  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return apiFetch(path, opts);
    logout();
    return null;
  }

  return res;
}

async function refreshAccessToken() {
  const refresh_token = localStorage.getItem("refresh_token");
  if (!refresh_token) return false;
  try {
    const res = await fetch(`${API}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem("access_token",  data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return true;
  } catch { return false; }
}

// ── User Info ─────────────────────────────────────────────────────────────
function renderUserInfo() {
  document.getElementById("user-display-name").textContent = state.user.display_name;
  document.getElementById("user-avatar").textContent = state.user.display_name[0].toUpperCase();
}

function logout() {
  apiFetch("/api/auth/logout", { method: "POST" });
  localStorage.clear();
  window.location.href = "/index.html";
}

// ── Workspaces ────────────────────────────────────────────────────────────
async function loadWorkspaces() {
  const res = await apiFetch("/api/workspaces");
  if (!res) return;
  state.workspaces = await res.json();

  const list = document.getElementById("workspace-list");
  list.innerHTML = "";

  for (const ws of state.workspaces) {
    const li = document.createElement("li");
    li.innerHTML = `<a onclick="selectWorkspace(${ws.id})" class="${state.activeWorkspace?.id === ws.id ? 'active' : ''}">
      <span>🏢</span> ${ws.name}
    </a>`;
    list.appendChild(li);
  }

  // Auto-select first workspace
  if (state.workspaces.length && !state.activeWorkspace) {
    selectWorkspace(state.workspaces[0].id);
  }
}

async function selectWorkspace(workspaceId) {
  state.activeWorkspace = state.workspaces.find(w => w.id === workspaceId);
  document.getElementById("workspace-name").textContent = state.activeWorkspace?.name || "TeamFlow";
  await loadChannels(workspaceId);

  // Re-render to update active state
  document.querySelectorAll("#workspace-list a").forEach(a => a.classList.remove("active"));
}

// ── Channels ──────────────────────────────────────────────────────────────
async function loadChannels(workspaceId) {
  const res = await apiFetch(`/api/workspaces/${workspaceId}/channels`);
  if (!res) return;
  state.channels = await res.json();

  const list = document.getElementById("channel-list");
  list.innerHTML = "";

  for (const ch of state.channels) {
    const li = document.createElement("li");
    li.id = `ch-nav-${ch.id}`;
    const icon = ch.is_private ? "🔒" : "#";
    li.innerHTML = `<a onclick="selectChannel(${ch.id})" id="ch-link-${ch.id}">
      <span>${icon}</span> ${ch.name}
    </a>`;
    list.appendChild(li);
  }

  // Auto-select #general
  const general = state.channels.find(c => c.name === "general");
  if (general) selectChannel(general.id);
}

async function selectChannel(channelId) {
  // Disconnect old WebSocket
  disconnectWS();

  state.activeChannel = state.channels.find(c => c.id === channelId);
  state.activeThreadId = null;
  clearThread();

  // Update active nav link
  document.querySelectorAll("#channel-list a").forEach(a => a.classList.remove("active"));
  document.getElementById(`ch-link-${channelId}`)?.classList.add("active");

  document.getElementById("channel-name").textContent = state.activeChannel?.name || "";
  document.getElementById("message-input").placeholder = `Message #${state.activeChannel?.name}`;
  document.getElementById("message-input").disabled = false;
  document.getElementById("send-btn").disabled = false;
  document.getElementById("empty-state")?.remove();

  await loadMessages(channelId);
  connectWS(channelId);
}

// ── Messages ──────────────────────────────────────────────────────────────
async function loadMessages(channelId) {
  const container = document.getElementById("messages-container");
  container.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px">Loading...</div>';

  const res = await apiFetch(`/api/channels/${channelId}/messages?page=1&page_size=50`);
  if (!res) return;
  const data = await res.json();

  container.innerHTML = "";
  for (const msg of data.messages) {
    appendMessage(msg, false);
  }
  scrollToBottom();
}

function appendMessage(msg, animate = true) {
  const container = document.getElementById("messages-container");
  const div = document.createElement("div");
  div.className = "message";
  div.id = `msg-${msg.id}`;

  const initials = (msg.display_name || String(msg.user_id))[0].toUpperCase();
  const name = msg.display_name || `User ${msg.user_id}`;
  const time = new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  div.innerHTML = `
    <div class="msg-avatar">${initials}</div>
    <div class="msg-body">
      <div class="msg-header">
        <span class="msg-name">${escapeHtml(name)}</span>
        <span class="msg-time">${time}</span>
      </div>
      <div class="msg-content">${escapeHtml(msg.content)}</div>
      ${msg.is_edited ? '<span class="msg-edited">(edited)</span>' : ""}
      <button class="msg-reply-btn" onclick="setThread(${msg.id})">↩ Reply in thread</button>
    </div>
  `;

  if (animate) div.style.animation = "fadeIn .15s ease";
  container.appendChild(div);
}

// ── Send Message ──────────────────────────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById("message-input");
  const content = input.value.trim();
  if (!content || !state.activeChannel) return;

  input.value = "";
  autoResize(input);

  // Try WebSocket first (instant), fall back to HTTP
  if (!sendViaWS({ type: "message", content, parent_id: state.activeThreadId || null })) {
    const res = await apiFetch(`/api/channels/${state.activeChannel.id}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, parent_id: state.activeThreadId || null }),
    });
    if (res?.ok) {
      const msg = await res.json();
      appendMessage(msg);
      scrollToBottom();
    }
  }
}

function handleInputKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

// ── Threads ───────────────────────────────────────────────────────────────
function setThread(parentId) {
  state.activeThreadId = parentId;
  document.getElementById("thread-reply-banner").classList.remove("hidden");
  document.getElementById("message-input").focus();
}

function clearThread() {
  state.activeThreadId = null;
  document.getElementById("thread-reply-banner").classList.add("hidden");
}

// ── Modals ────────────────────────────────────────────────────────────────
function showNewWorkspaceModal() {
  document.getElementById("modal-content").innerHTML = `
    <h2>Create a Workspace</h2>
    <div class="form-group">
      <label>Workspace Name</label>
      <input type="text" id="ws-name-input" placeholder="e.g. Acme Corp" />
    </div>
    <div class="form-group">
      <label>Description (optional)</label>
      <input type="text" id="ws-desc-input" placeholder="What's this workspace for?" />
    </div>
    <div class="modal-actions">
      <button class="btn-secondary" onclick="closeModal()">Cancel</button>
      <button class="btn-primary" onclick="createWorkspace()">Create</button>
    </div>
  `;
  document.getElementById("modal-overlay").classList.remove("hidden");
}

async function createWorkspace() {
  const name        = document.getElementById("ws-name-input").value.trim();
  const description = document.getElementById("ws-desc-input").value.trim();
  if (!name) return;

  const res = await apiFetch("/api/workspaces", {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });

  if (res?.ok) {
    closeModal();
    await loadWorkspaces();
  }
}

function showNewChannelModal() {
  if (!state.activeWorkspace) { alert("Select a workspace first"); return; }
  document.getElementById("modal-content").innerHTML = `
    <h2>Create a Channel</h2>
    <div class="form-group">
      <label>Channel Name</label>
      <input type="text" id="ch-name-input" placeholder="e.g. engineering" />
    </div>
    <div class="form-group">
      <label>Description (optional)</label>
      <input type="text" id="ch-desc-input" placeholder="What's this channel for?" />
    </div>
    <div class="form-group">
      <label><input type="checkbox" id="ch-private" /> Private channel</label>
    </div>
    <div class="modal-actions">
      <button class="btn-secondary" onclick="closeModal()">Cancel</button>
      <button class="btn-primary" onclick="createChannel()">Create</button>
    </div>
  `;
  document.getElementById("modal-overlay").classList.remove("hidden");
}

async function createChannel() {
  const name        = document.getElementById("ch-name-input").value.trim();
  const description = document.getElementById("ch-desc-input").value.trim();
  const is_private  = document.getElementById("ch-private").checked;
  if (!name) return;

  const res = await apiFetch(`/api/workspaces/${state.activeWorkspace.id}/channels`, {
    method: "POST",
    body: JSON.stringify({ name, description, is_private }),
  });

  if (res?.ok) {
    closeModal();
    await loadChannels(state.activeWorkspace.id);
  }
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
}

// ── Utilities ─────────────────────────────────────────────────────────────
function scrollToBottom() {
  const c = document.getElementById("messages-container");
  c.scrollTop = c.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
