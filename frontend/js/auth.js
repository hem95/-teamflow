// If the user is already logged in, skip the login page
if (localStorage.getItem("access_token")) {
  window.location.href = "/app.html";
}

const API = ""; // same origin — frontend and backend both on port 8000

function showTab(tab) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".auth-form").forEach(f => f.classList.add("hidden"));

  event.target.classList.add("active");
  document.getElementById(tab + "-form").classList.remove("hidden");
}

function showError(id, message) {
  const el = document.getElementById(id);
  el.textContent = message;
  el.classList.remove("hidden");
}

async function handleLogin(event) {
  event.preventDefault();
  const email    = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;

  try {
    const res = await fetch(`${API}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (res.status === 429) {
      showError("login-error", "Too many login attempts. Please wait a minute and try again.");
      return;
    }

    const data = await res.json();

    if (!res.ok) {
      showError("login-error", data.detail || "Login failed");
      return;
    }

    // Save tokens to localStorage (like a cookie but accessible to JS)
    localStorage.setItem("access_token",  data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("user",          JSON.stringify(data.user));

    window.location.href = "/app.html";
  } catch (err) {
    showError("login-error", "Network error — is the server running?");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const display_name = document.getElementById("reg-display").value;
  const username     = document.getElementById("reg-username").value.toLowerCase();
  const email        = document.getElementById("reg-email").value;
  const password     = document.getElementById("reg-password").value;

  try {
    const res = await fetch(`${API}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name, username, email, password }),
    });

    if (res.status === 429) {
      showError("reg-error", "Too many signup attempts. Please wait a minute and try again.");
      return;
    }

    const data = await res.json();

    if (!res.ok) {
      // data.detail can be a string or an array of validation errors
      const msg = Array.isArray(data.detail)
        ? data.detail.map(e => e.msg).join(", ")
        : (data.detail || "Registration failed");
      showError("reg-error", msg);
      return;
    }

    localStorage.setItem("access_token",  data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("user",          JSON.stringify(data.user));

    window.location.href = "/app.html";
  } catch (err) {
    showError("reg-error", "Network error — is the server running?");
  }
}
