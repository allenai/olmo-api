from core.message.message_chunk import Chunk, MessageStreamError

type ChatStreamOutput = Chunk | MessageStreamError
