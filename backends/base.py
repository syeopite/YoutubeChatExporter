"""Module containing things that all backends depends on or is derived from"""

import argparse
import asyncio
import datetime
import pathlib
import sys
import time
from dataclasses import dataclass
from typing import Optional, Union

from pytchat.processors.default.processor import Chat as ChatObject

import formats
from misc import utils


@dataclass
class Message:
    """Object for representing a live stream message"""

    # TODO Refactor make a special data class for author attribute
    author_name: str
    author_id: str
    author_image_url: str

    # Author attributes
    is_sponsor: bool
    is_moderator: bool
    is_verified: bool
    is_chat_owner: bool

    contents: Optional[list]
    badge_url: str
    emojis = str

    timestamp: datetime.datetime

    def get_plain_text_contents(self):
        string = ""
        for msg in self.contents:
            if isinstance(msg, str):
                string += msg
        return string


@dataclass
class SuperChat(Message):
    """Object for representing a Youtube SuperChat message"""
    author_name_color: str
    currency_amount: str
    currency_color: str
    timestamp_color: tuple

    header_color: tuple
    body_color: tuple
    message_color: tuple


@dataclass
class SuperSticker(Message):
    """Object for representing a Youtube SuperSticker message"""
    author_name_color: tuple
    currency_amount: str
    currency_color: tuple
    sticker: str

    body_color: tuple


@dataclass
class NewSponser(Message):
    """Object for representing a new sponsor announcement from Youtube"""
    pass


MessageTypes = Union[Message, SuperChat, SuperSticker, NewSponser]


# #  output_directory, fetched_messages, "dark", arguments, title
@dataclass
class BaseBackend:
    """The parent backend that backends are derived from"""
    stream_id: str
    arguments: argparse.Namespace
    _raw_messages: asyncio.Queue[ChatObject]
    _parsed_messages: asyncio.Queue[MessageTypes]

    output_directory: str = ""
    _completion_event: asyncio.Event = asyncio.Event()
    _new_message_parsed_event: asyncio.Event = asyncio.Event()
    _parsed_message_count: int = 0

    def setup_output_directory(self):
        """Setup the directory to output the exported live chat into"""
        assert hasattr(self, "title") is True

        title = utils.clean_path(self.title)
        if self.arguments.output:
            location = f"{self.arguments.output}/{title}"
        else:
            location = f"chat/{title}"

        self.output_directory = location
        pathlib.Path(location).mkdir(parents=True, exist_ok=True)

    async def report(self):
        """Prints a dynamically updated message showing progress on message exportation.

        The output message is quite basic. It contains the total amount of messages exported, the rate at which messages
        are being exported and the total elapsed time. This should be changed in the future to show more information.
        """
        await asyncio.sleep(0.1)
        current_time = time.time()
        elapsed_time = round(current_time - self.start)
        rate = round(self._parsed_message_count / elapsed_time)

        sys.stdout.write(f"\rExporting {self._parsed_message_count} messages at {rate}/s ({elapsed_time}s)")
        sys.stdout.flush()


def fetch_exporter(location, message_queue, arguments, title, completion_event):
    """Fetch exporter for the selected output format"""

    exporter = getattr(formats, arguments.format.lower())
    return exporter(location, message_queue, arguments, title, completion_event)
