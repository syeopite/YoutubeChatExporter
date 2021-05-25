"""Module containing the logic to use the pytchat backend"""

import pytchat

from .base import *


class PytchatBackend(BaseBackend):
    """Backend for parsing and exporting live chat messages through the pytchat library.

    The entire thing is highly asynchronous with extraction, parsing and exporting all happening in "parallel". Here's
    how it works:
        - Pytchat.LiveChatAsync is immediately called telling pytchat to begin the
          extraction process immediately. A callback function is then issued to it which pytchat calls after extracting
          at least 20 messages.

        - Video information is then fetched for information needed to create the output directories. In this case that
          information is the stream title.

        - An asyncio task for the _parse function is created. Which awaits for an item from the raw_message_queue
          for processing (parsing).

        - Finally a exporter is fetched from what the user configured through the CLI interface. The exporter is also
          given access to the instance's parsed_message_queue in order to await for a parsed result which is
          immediately parsed into the chosen format once available.

        - When pytchat calls the callback method, the extracted messages would be fed into the raw_message_queue
          allowing the _parse method to respond and feed the parsed results into the parsed_message_queue

    Overall everything, as in the extraction, parsing and exporting, all happens asynchronously

    Parameter:
        stream_id: Youtube URL or ID of the live stream to export from
        arguments: CLI arguments
        raw_message_queue: Asyncio queue for storing the raw messages extracted from pytchat
        parsed_message_queue: Asyncio queue for storing parsed messages
    """

    def __init__(self, stream_id, arguments, raw_message_queue, parsed_message_queue):
        super().__init__(stream_id, arguments, raw_message_queue, parsed_message_queue)
        self.start = time.time()
        self.stream = pytchat.LiveChatAsync(stream_id, callback=self.stream_callback)

        video_information = utils.fetch_video_information(self.stream._video_id)
        self.title = video_information['title']

        # Tasks
        loop = asyncio.get_running_loop()
        self._parse_task = loop.create_task(self._parse())

        self.setup_output_directory()

        self.exporter = fetch_exporter(self.output_directory, self._parsed_messages,
                                       self.arguments, self.title, self._completion_event)

    async def _parse(self):
        """Parses raw messages into something the exporters can understand

        Each msg type is serialized into a different object.
            Superchat -> SuperChat
            Supersticker -> SuperSticker
            New sponsor -> NewSponsor
            Message -> Message

        This allows us to use the same eventual exporter with a variety of different backends.

        Please refer to backends/base.py for more information on each message type.
        """

        while self.stream.is_alive():
            msg = await self._raw_messages.get()

            author_name = msg.author.name
            author_id = msg.author.channelId
            profile_image = msg.author.imageUrl

            # Author attributes
            is_verified = msg.author.isVerified
            is_moderator = msg.author.isChatModerator
            is_sponsor = msg.author.isChatSponsor
            is_chat_owner = msg.author.isChatOwner

            badge_url = msg.author.badgeUrl
            contents = await self._parse_message_contents(getattr(msg, "messageEx", None))

            timestamp = datetime.datetime.strptime(msg.datetime, "%Y-%m-%d %H:%M:%S")
            timestamp = timestamp.strftime("%-m/%-d/%Y %-I:%M %p")

            basic_message = {
                "author_name": author_name,
                "author_id": author_id,
                "author_image_url": profile_image,
                "is_verified": is_verified,
                "is_moderator": is_moderator,
                "is_sponsor": is_sponsor,
                "is_chat_owner": is_chat_owner,
                "contents": contents,
                "badge_url": badge_url,
                "timestamp": timestamp,
            }

            if msg.type.startswith("super"):
                author_name_color = utils.translate_rgb_int_to_tuple(msg.colors.authorNameTextColor)
                currency_amount = msg.amountString

                if msg.type == "superChat":
                    header_color = utils.translate_rgb_int_to_tuple(msg.colors.headerBackgroundColor)
                    # The color for the currency text on superchats is the header text color
                    currency_color = utils.translate_rgb_int_to_tuple(msg.colors.headerTextColor)

                    body_color = utils.translate_rgb_int_to_tuple(msg.colors.bodyBackgroundColor)
                    timestamp_color = utils.translate_rgb_int_to_tuple(msg.colors.timestampColor)
                    message_color = msg.colors.bodyTextColor

                    msg_obj = SuperChat(**basic_message,
                                        author_name_color=author_name_color,
                                        currency_color=currency_color,
                                        currency_amount=currency_amount,
                                        timestamp_color=timestamp_color,
                                        header_color=header_color,
                                        body_color=body_color,
                                        message_color=message_color)
                else:
                    sticker = msg.sticker
                    currency_color = utils.translate_rgb_int_to_tuple(msg.colors.moneyChipTextColor)
                    bg_color = utils.translate_rgb_int_to_tuple(msg.colors.backgroundColor)

                    msg_obj = SuperSticker(**basic_message,
                                           author_name_color=author_name_color,
                                           currency_color=currency_color,
                                           currency_amount=currency_amount,
                                           sticker=sticker,
                                           body_color=bg_color)
            else:
                if msg.type == "newSponsor":
                    msg_obj = NewSponser(**basic_message)
                else:
                    msg_obj = Message(**basic_message)

            await self._parsed_messages.put(msg_obj)
            self._parsed_message_count += 1
            await self.report()

        print("Done!")

    async def begin(self):
        await self.exporter.export()

    async def stream_callback(self, message_bundle):
        """Callback method for pytchat once a certain number of messages has been fetched.

        Feeds the fetched messages into the raw_message_queue which is read by the _parse method

        Parameter
            message_bundle: A collection of messages fetched by pytchat
        """
        for message in message_bundle.items:
            await self._raw_messages.put(message)

        if not self.stream.is_alive():
            self._completion_event.set()
            self._parse_task.cancel()
            self._parsed_messages.put_nowait(None)

    @staticmethod
    async def _parse_message_contents(message_contents):
        """Parses the content array returned by pytchat

        The content array contains both normal text and emojis with each being represented by a str, and a dict.
        This method just quickly parses it into something we can understand.

        Parameters:
            message_contents: contents of the current youtube live chat message
        """
        content_array = []

        if not message_contents:
            return content_array

        for item in message_contents:
            if isinstance(item, str):
                content_array.append(item)
            else:  # Emojis
                # TODO make named tuple
                content_array.append((item["id"], item["url"]))

        return content_array
