import backends.base as m_types
from formats.base import BaseExporter


class PlainText(BaseExporter):
    def __init__(self, output_directory, message_queue, arguments, title, completion_event):
        super().__init__(output_directory, message_queue, arguments, title, completion_event)

    async def _process_message_type(self, msg):
        special = []
        msg = await self.messages.get()
        if msg.is_verified:
            special.append("verified")
        if msg.is_chat_owner:
            special.append("owner")
        if msg.is_moderator:
            special.append("moderator")

        if msg.is_sponsor:
            if isinstance(msg, m_types.NewSponser):
                special.append("new/upgraded membership")
            else:
                special.append("member")

        if isinstance(msg, m_types.SuperChat):
            special.append(f"superchat: {msg.currency_amount}")
        if isinstance(msg, m_types.SuperSticker):
            special.append(f"supersticker: {msg.currency_amount}")

        if special:
            special = f"[{', '.join(special)}]"
        else:
            special = ""

        message_to_add = f"{msg.timestamp} {msg.author_name}"
        if special:
            message_to_add += f" {special}"
        message_to_add += f": {msg.get_plain_text_contents()}\n\n"

        return message_to_add

    async def export(self):
        """Begins the exportation process of livechat messages into the plaintext format."""

        partition_counter = 0
        while not self.completion_event.is_set():
            if 1 < self.arguments.split:
                doc = await self.create_format()

                if self.arguments.split == self.processed_message_count:
                    partition_counter += 1
                    self.processed_message_count = 0

                await self._write_to_file(doc, name=f"{partition_counter}.txt")
            else:
                doc = await self.create_format()
                await self._write_to_file(doc, name=f"exported.txt")
