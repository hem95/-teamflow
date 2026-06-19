# Import all models here so Alembic (migration tool) can discover them
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.channel import Channel, ChannelMember
from app.models.message import Message
from app.models.direct_message import DMConversation, DMParticipant, DirectMessage
from app.models.attachment import Attachment
