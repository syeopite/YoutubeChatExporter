"""Module containing the base exporter that all exporters are derived """

import asyncio

import aiofiles

import backends.base as m_types


class BaseExporter:
    """The parent backend that backends are derived from"""

    def __init__(self, output_directory, message_queue, arguments, title, completion_event):
        self.output_directory = output_directory
        self.messages: asyncio.Queue[m_types.MessageTypes] = message_queue
        self.arguments = arguments
        self.title = title
        self.completion_event = completion_event

        self.processed_message_count = 0

    async def create_format(self, accumulate=True):
        accumulator = ""
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

            if accumulate:
                accumulator += await self._process_message_type(msg)
            else:
                await self._process_message_type(msg)

            self.processed_message_count += 1
        return accumulator

    async def _process_message_type(self, msg):
        pass

    async def export(self, ext):
        """Begins the exportation process of livechat messages into the selected format."""
        partition_counter = 0
        while not self.completion_event.is_set():
            if 1 < self.arguments.split:
                doc = await self.create_format()

                if self.arguments.split == self.processed_message_count:
                    partition_counter += 1
                    self.processed_message_count = 0

                await self._write_to_file(doc, name=f"{partition_counter}.{ext}")
            else:
                doc = await self.create_format()
                await self._write_to_file(doc, name=f"exported.{ext}")

    async def _write_to_file(self, doc, name):
        path = f"{self.output_directory}/{name}"

        async with aiofiles.open(path, mode='w') as file:
            await file.write(str(doc))
