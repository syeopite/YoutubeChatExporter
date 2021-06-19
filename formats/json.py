import json
import time

import backends.base as m_types
from formats.base import BaseExporter


class JSON(BaseExporter):
    def __init__(self, output_directory, message_queue, arguments, title, completion_event):
        super().__init__(output_directory, message_queue, arguments, title, completion_event)

    async def _process_message_type(self, msg):
        message_json = {"author": msg.author_name, "author_image": msg.author_image_url, "id": msg.author_id,
                        "badge_url": msg.badge_url,
                        "attributes": {"is_sponsor": msg.is_sponsor,
                                       "is_moderator": msg.is_moderator,
                                       "is_verified": msg.is_verified,
                                       "is_chat_owner": msg.is_chat_owner,
                                       }, "contents": msg.contents,
                        "timestamp_text": msg.timestamp,
                        "timestamp": time.mktime(time.strptime(msg.timestamp, "%m/%d/%Y %I:%M %p")),
                        "type": str(type(msg).__name__)}

        if isinstance(msg, (m_types.SuperChat, m_types.SuperSticker)):
            message_json["renderer"] = {
                "author_name_color_rgb": msg.author_name_color,
                "currency_amount": msg.currency_amount,
                "currency_color_rgb": msg.currency_color,
                "body_color_rgb": msg.body_color,
            }

            if isinstance(msg, m_types.SuperChat):
                message_json["renderer"]["header_color_rgb"] = msg.header_color
                message_json["renderer"]["message_color"] = msg.message_color
                message_json["renderer"]["timestamp_color"] = msg.timestamp_color
            else:
                message_json["renderer"]["sticker"] = msg.sticker

        return message_json

    async def create_format(self, **kwargs):
        messages = []
        while not self.completion_event.is_set():
            if 1 < self.arguments.split == self.processed_message_count:
                break

            # Fetch a message and if downloading is enabled pass then passes it to the download_task
            # in order to have the images get processed
            msg = await self.messages.get()

            # Since we're waiting for an item from the queue the chat message we receive could very well be the last
            # thus we'll do a check for it
            if self.completion_event.is_set():
                break

            messages.append(await self._process_message_type(msg))

            self.processed_message_count += 1

        return json.dumps(messages)

    async def export(self, *_):
        """Begins the exportation process of livechat messages into json."""

        partition_counter = 0
        while not self.completion_event.is_set():
            if 1 < self.arguments.split:
                doc = await self.create_format()

                if self.arguments.split == self.processed_message_count:
                    partition_counter += 1
                    self.processed_message_count = 0

                await self._write_to_file(doc, name=f"{partition_counter}.json")
            else:
                doc = await self.create_format()
                await self._write_to_file(doc, name=f"json")
