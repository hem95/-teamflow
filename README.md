# TeamFlow 💬

A Slack-like team communication platform built with Python. Teams can create workspaces, organise conversations into channels, and message each other in real time.

Built as a learning project to understand how modern web applications are architected — from authentication to real-time messaging to containerised deployment.

---

## What It Does

- **Authentication** — Register, log in, log out with secure JWT tokens
- **Workspaces** — Create a company or team workspace
- **Channels** — Organise conversations by topic (like #general, #engineering)
- **Real-time messaging** — Messages appear instantly for everyone in the channel without refreshing the page
- **Threaded replies** — Reply inside a thread to keep conversations organised
- **Online presence** — See who is currently active

---

## Live Demo

> Run it locally following the instructions below. No external server required.

---

## Tech Stack

| Layer | Tool | Why This Tool |
|-------|------|---------------|
| Language | Python | Readable, beginner friendly, massive ecosystem |
| Web Framework | FastAPI | Async support, auto-generated docs, fast |
| Database | PostgreSQL | Reliable, scales to millions of rows, free |
| ORM | SQLAlchemy | Write Python instead of SQL, prevents SQL injection |
| Password Security | bcrypt + Passlib | Industry standard one-way password hashing |
| Authentication | JWT (JSON Web Tokens) | Stateless auth, no database hit on every request |
| Real-time | WebSockets | Persistent connection for instant messaging |
| Caching / Scaling | Redis | Broadcasts messages across multiple server instances |
| Containerisation | Docker | Same environment on every machine |
| Orchestration | Docker Compose | Start all services with one command |

---

## Project Structure

```
teamflow/
├── backend/
│   ├── app/
│   │   ├── main.py              # App entry point — registers all routes
│   │   ├── config.py            # Settings loaded from .env file
│   │   ├── database.py          # PostgreSQL async connection pool
│   │   ├── models/              # Database table definitions
│   │   │   ├── user.py          # Users table
│   │   │   ├── workspace.py     # Workspaces + members table
│   │   │   ├── channel.py       # Channels + members table
│   │   │   └── message.py       # Messages table (supports threads)
│   │   ├── schemas/             # Request and response data shapes
│   │   │   ├── user.py          # Register / login / user response
│   │   │   ├── workspace.py     # Create workspace / workspace response
│   │   │   ├── channel.py       # Create channel / channel response
│   │   │   └── message.py       # Send message / paginated messages
│   │   ├── api/                 # HTTP route handlers
│   │   │   ├── auth.py          # Register, Login, Logout, Refresh token
│   │   │   ├── workspaces.py    # Create workspace, invite members
│   │   │   ├── channels.py      # Create, list, join channels
│   │   │   ├── messages.py      # Send, edit, delete messages
│   │   │   └── websocket.py     # Real-time WebSocket connection handler
│   │   └── core/
│   │       ├── security.py      # Password hashing + JWT token logic
│   │       └── dependencies.py  # Auth guard (get_current_user)
│   ├── alembic/                 # Database migration scripts
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile               # How to build the backend container
│   └── .env.example             # Template for your secrets file
├── frontend/
│   ├── index.html               # Login and register page
│   ├── app.html                 # Main chat interface
│   ├── css/
│   │   └── style.css            # Dark theme, Slack-inspired design
│   └── js/
│       ├── auth.js              # Login and register form logic
│       ├── app.js               # Workspaces, channels, messages
│       └── websocket.js         # Real-time WebSocket client
├── docker-compose.yml           # Runs all services together
├── .gitignore                   # Tells Git what not to upload (secrets etc.)
└── README.md                    # This file
```

---

## How to Run

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running

### Steps

**1. Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/teamflow.git
cd teamflow
```

**2. Create your secrets file**
```bash
# Mac / Linux
cp backend/.env.example backend/.env

# Windows
copy backend\.env.example backend\.env
```

**3. Start everything**
```bash
docker compose up --build
```

Docker will download and start four services:
- PostgreSQL database
- Redis
- FastAPI backend
- Frontend (served by FastAPI)

**4. Open your browser**
```
http://localhost:8000
```

That is it. Create an account and start chatting.

---

## API Documentation

Once running, visit:
```
http://localhost:8000/docs
```

FastAPI auto-generates interactive documentation for every endpoint. You can test the API directly from the browser.

---

## Architecture — How It All Connects

```
Browser (http://localhost:8000)
        │
        ├── GET  /              → Serves frontend HTML/CSS/JS
        │
        ├── POST /api/auth/register   → Creates account, returns JWT tokens
        ├── POST /api/auth/login      → Verifies password, returns JWT tokens
        │
        ├── GET  /api/workspaces      → Lists your workspaces
        ├── POST /api/workspaces      → Creates a workspace
        │
        ├── GET  /api/workspaces/{id}/channels    → Lists channels
        ├── POST /api/workspaces/{id}/channels    → Creates a channel
        │
        ├── GET  /api/channels/{id}/messages      → Fetches message history
        ├── POST /api/channels/{id}/messages      → Sends a message (HTTP)
        │
        └── WS   /ws/channels/{id}   → Real-time WebSocket connection
```

### What happens when you send a message

```
1. You type a message and press Enter
2. websocket.js sends it over the open WebSocket connection
3. FastAPI receives it and verifies your JWT token
4. The message is saved to PostgreSQL
5. FastAPI broadcasts it to every user connected to that channel
6. Their browsers receive it and display it instantly
```

---

## Key Concepts Explained

### Why JWT instead of sessions?

Traditional sessions store your login state in the database. Every request checks the database — "is this person still logged in?" At thousands of users making dozens of requests per minute, that is a lot of database reads.

JWT tokens are self-contained. The token itself proves who you are. The server just verifies the signature — no database needed. This scales to millions of users without changing anything.

### Why async programming?

Traditional servers handle one request at a time per worker. If a request is waiting for the database, the worker sits idle. Async programming lets one worker handle thousands of requests simultaneously by doing other work while waiting. This is why FastAPI can handle thousands of users without needing thousands of servers.

### Why bcrypt for passwords?

bcrypt is deliberately slow to compute. This sounds counterintuitive but it is the point. If someone steals your database, they cannot crack passwords quickly because each attempt takes significant computation time. MD5 and SHA-256 alone are too fast — an attacker can try billions of combinations per second. bcrypt limits them to thousands per second.

We also added SHA-256 pre-hashing before bcrypt. This means passwords of any length are supported safely — the SHA-256 step always produces a fixed 32-byte output before bcrypt ever sees it.

### Why WebSockets instead of refreshing the page?

Refreshing the page every second to check for new messages wastes bandwidth and adds server load. WebSocket keeps a single persistent connection open. The server pushes new messages to your browser the moment they arrive — like a phone call staying connected rather than dialling every few seconds.

### Why Docker?

Without Docker, every person running this project needs to manually install the exact right version of Python, PostgreSQL, Redis, and all dependencies — and hope they match. Docker packages everything into containers that run identically on any machine. One command starts the entire application regardless of what operating system you use.

---

## Scaling to Thousands of Users

The architecture is designed to grow:

- **Database connection pooling** — 60 simultaneous database connections ready at all times
- **Async everywhere** — one worker handles many requests without blocking
- **Redis pub/sub** — when you add more backend servers, Redis ensures messages broadcast across all of them
- **Stateless auth** — JWT means any server can verify any user without coordination
- **Docker** — add more backend instances behind a load balancer without code changes

---

## What Could Be Added Next

- [ ] Direct messages between users
- [ ] File and image uploads
- [ ] Push notifications when mentioned
- [ ] User profile pictures
- [ ] Message reactions (emoji)
- [ ] Search across messages
- [ ] HTTPS / SSL certificate for production
- [ ] Deploy to cloud (Railway, Render, AWS)

---

## Lessons Learned Building This

**Port conflicts on Windows** — Port 80 is occupied by IIS (Windows built-in web server) by default. Always use ports above 1024 for development on Windows to avoid conflicts.

**CORS exists for security** — Browsers block requests between different ports or domains by default. This is a protection against malicious websites stealing your data. For development, allowing all origins is fine. For production, restrict it to your specific domain.

**bcrypt has a 72-byte limit** — The bcrypt hashing algorithm only processes the first 72 bytes of a password. The solution is to pre-hash with SHA-256 first, which converts any length password into a fixed 32-byte output before bcrypt processes it.

**Docker restarts are required for Python changes** — Frontend files (HTML, CSS, JS) update immediately because they are served directly from disk. Python files require a container restart because the server loads them once at startup and keeps them in memory.

---

## Author

Built with the help of Claude Code (Anthropic) as a learning project exploring:
- Python backend development
- Real-time web applications
- Database design
- Authentication and security
- Containerised deployment

---

## License

MIT License — free to use, modify, and share.
