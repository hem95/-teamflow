import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.channel import ChannelMember
from app.models.message import Message
from app.core.security import decode_token

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Manages all active WebSocket connections.

    Structure:
        channel_connections: { channel_id → set of WebSocket connections }

    When a message is sent to channel 5, we broadcast it to every
    WebSocket in channel_connections[5].

    For production with multiple servers, replace the in-memory sets
    with Redis pub/sub so all server instances share the same broadcast.
    """

    def __init__(self):
        self.channel_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_id: int):
        await websocket.accept()
        if channel_id not in self.channel_connections:
            self.channel_connections[channel_id] = set()
        self.channel_connections[channel_id].add(websocket)

    def disconnect(self, websocket: WebSocket, channel_id: int):
        if channel_id in self.channel_connections:
            self.channel_connections[channel_id].discard(websocket)
            if not self.channel_connections[channel_id]:
                del self.channel_connections[channel_id]

    async def broadcast(self, channel_id: int, payload: dict, exclude: WebSocket = None):
        """Send a message to every connection in a channel."""
        if channel_id not in self.channel_connections:
            return
        dead = set()
        for ws in self.channel_connections[channel_id]:
            if ws is exclude:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.channel_connections[channel_id].discard(ws)

    def connection_count(self, channel_id: int) -> int:
        return len(self.channel_connections.get(channel_id, set()))


manager = ConnectionManager()


@router.websocket("/ws/channels/{channel_id}")
async def websocket_channel(websocket: WebSocket, channel_id: int):
    """
    WebSocket endpoint — clients connect here to receive live messages.

    Flow:
      1. Client connects:  ws://server/ws/channels/5?token=<jwt>
      2. We verify the token and check channel membership
      3. We keep the connection open, broadcasting messages as they arrive
      4. On disconnect, we clean up
    """
    # ── Authenticate ──────────────────────────────────────────────────────
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = int(payload["sub"])

    # ── Check channel membership ──────────────────────────────────────────
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ChannelMember).where(
                ChannelMember.channel_id == channel_id,
                ChannelMember.user_id == user_id,
            )
        )
        if not result.scalar_one_or_none():
            await websocket.close(code=4003, reason="Not a channel member")
            return

        # Mark user online
        await db.execute(update(User).where(User.id == user_id).values(is_online=True))
        await db.commit()

    # ── Accept and register connection ────────────────────────────────────
    await manager.connect(websocket, channel_id)

    # Notify others that someone joined
    await manager.broadcast(channel_id, {
        "type": "user_joined",
        "user_id": user_id,
        "channel_id": channel_id,
        "online_count": manager.connection_count(channel_id),
    }, exclude=websocket)

    try:
        while True:
            # Wait for a message from this client
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            msg_type = data.get("type")

            # ── Handle: new message ───────────────────────────────────────
            if msg_type == "message":
                content = (data.get("content") or "").strip()
                if not content:
                    continue

                async with AsyncSessionLocal() as db:
                    message = Message(
                        channel_id=channel_id,
                        user_id=user_id,
                        content=content,
                        parent_id=data.get("parent_id"),
                    )
                    db.add(message)
                    await db.flush()
                    await db.refresh(message)
                    await db.commit()

                    broadcast_payload = {
                        "type": "message",
                        "id": message.id,
                        "content": message.content,
                        "user_id": message.user_id,
                        "channel_id": message.channel_id,
                        "parent_id": message.parent_id,
                        "created_at": message.created_at.isoformat(),
                    }

                # Broadcast to everyone in the channel (including sender)
                await manager.broadcast(channel_id, broadcast_payload)

            # ── Handle: typing indicator ──────────────────────────────────
            elif msg_type == "typing":
                await manager.broadcast(channel_id, {
                    "type": "typing",
                    "user_id": user_id,
                    "channel_id": channel_id,
                }, exclude=websocket)

            # ── Handle: ping (keep-alive) ─────────────────────────────────
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_id)

        async with AsyncSessionLocal() as db:
            await db.execute(update(User).where(User.id == user_id).values(is_online=False))
            await db.commit()

        await manager.broadcast(channel_id, {
            "type": "user_left",
            "user_id": user_id,
            "channel_id": channel_id,
            "online_count": manager.connection_count(channel_id),
        })
