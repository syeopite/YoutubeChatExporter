import asyncio
import pathlib
import shutil

import aiofiles
import aiohttp
from dominate import document, tags

import backends.base as m_types
from formats.base import BaseExporter


class HtmlFormat(BaseExporter):
    def __init__(self, output_directory, message_queue, theme, arguments, title, completion_event):
        super().__init__(output_directory, message_queue, arguments, title, completion_event)

        self.theme = theme
        self.pass_to_download_task: asyncio.Queue[m_types.MessageTypes] = asyncio.Queue(0)
        self.image_aggregator = []
        self.setup_output_directory()

        if not self.arguments.no_download_image and not self.arguments.update:
            loop = asyncio.get_event_loop()
            loop.create_task(self._download_images())

    async def _extract_images_to_download(self, msg):
        """Scans through livestream messages for images to extract"""
        images_to_download = []

        def package_image(url, name, media_type, sanitize=False):
            images_to_download.append({"url": url, "name": name, "media_type": media_type, "sanitize": sanitize})
            self.image_aggregator.append(url)

        if msg.author_image_url not in self.image_aggregator:
            package_image(url=msg.author_image_url, name=msg.author_id, media_type="profile_pictures")

        if msg.badge_url and msg.badge_url not in self.image_aggregator:
            package_image(url=msg.badge_url, name=msg.badge_url, media_type="badges", sanitize=True)

        if isinstance(msg, m_types.SuperSticker) and msg.sticker not in self.image_aggregator:
            package_image(url=msg.sticker, name=msg.sticker, media_type="superstickers", sanitize=True)

        if any(isinstance(t, tuple) for t in msg.contents):
            for text_item in msg.contents:
                if isinstance(text_item, tuple) and text_item[0] not in self.image_aggregator:
                    package_image(url=text_item[1], name=text_item[0], media_type="emojis")

        return images_to_download

    async def _download_images(self):
        while not self.completion_event.is_set():
            msg = await self.pass_to_download_task.get()
            images_to_download = await self._extract_images_to_download(msg)

            for img in images_to_download:
                await self._download_image(img)

    async def _download_image(self, arguments):
        url = arguments["url"]
        name = arguments["name"]
        sanitize = arguments["sanitize"]
        media_type = arguments["media_type"]

        if sanitize:
            name = self.sanitize(name)

        path = f"{self.output_directory}/assets/{media_type}/{name}.png"
        async with aiofiles.open(path, mode='wb') as img_file:
            # TODO use predefined clients for certain URLs in order to improve speed.
            # Create a aiohttp client for fetching image
            async with aiohttp.ClientSession() as session:
                async with session.post(url) as response:
                    if response.status == 400:
                        return

                    await img_file.write(await response.read())

    def setup_output_directory(self):
        """Setup required assets in output directory

        This function creates the folders for all possible media_types and then copies any predefined
        assets into their respective folders.

        """
        # Setup media directories
        for media_type in ["profile_pictures", "badges", "superstickers", "emojis"]:
            pathlib.Path(f"{self.output_directory}/assets/{media_type}").mkdir(parents=True, exist_ok=True)

        # Copy assets to their respective locations
        shutil.copy(f"assets/style-{self.theme}.css", f"{self.output_directory}/assets/style-{self.theme}.css")

        for badges in ["mod-icon.png", "verified_icon.png"]:
            shutil.copy(f"assets/{badges}", f"{self.output_directory}/assets/badges/{badges}")

    @staticmethod
    def get_special_identifier(msg, member_badge_path):
        """Fetches the special identifiers of a message along with the styling it needs.

        This includes:
            - Verification status
            - Is moderator
            - Is sponsor (member)

        If a message includes any of them then the special identifiers are added to a set() with the location of the
        icon for the identifier being added to another set().

        set() are used here to make sure no duplicates (literally only "special_icon" class) are added.

        Parameters:
            msg: MessageType
                See base.py for more information
            member_badge_path: Path of the member badge icon

        """
        # Handles special message authors
        special_author_classes = set()
        special_author_badges = set()

        if msg.is_verified:
            special_author_classes.update({"special_icon"})
            special_author_badges.update({"assets/badges/verified_icon.png"})
        if msg.is_moderator:
            special_author_classes.update({"special_icon", "mod"})
            special_author_badges.update({"assets/badges/mod-icon.png"})
        if msg.is_sponsor:
            special_author_classes.update({"special_icon", "member"})
            special_author_badges.update({member_badge_path})

        return special_author_classes, special_author_badges

    def create_p_with_emojis(self, raw_msg_content, **kwargs):
        """Parses the content to produce a paragraph with emojis"""
        with tags.p(**kwargs) as message:
            for raw in raw_msg_content:
                if isinstance(raw, str):
                    message.add_raw_string(raw)
                else:
                    if not self.arguments.no_download_image:
                        message.add(tags.img(src=f"assets/emojis/{raw[0]}.png", cls="emoji"))
                    else:
                        message.add(tags.img(src=f"{raw[1]}", cls="emoji"))

    async def create_format(self, **kwargs):
        index = kwargs.get("index")

        with document(title=f"{self.title}{index}") as doc:
            tags.link(rel="stylesheet", href=f"assets/style-{self.theme}.css")
            await super().create_format(accumulate=False)
        return doc

    async def _process_message_type(self, msg):
        # Check message for any images we can download if user wants to archive everything.
        if not self.arguments.no_download_image and not self.arguments.update:
            await self.pass_to_download_task.put(msg)

        # Paths for the images; local if downloaded, url if remote.
        if self.arguments.no_download_image:
            pfp_path = msg.author_image_url
            badge_path = msg.badge_url
        else:
            pfp_path = f"assets/profile_pictures/{msg.author_id}.png"
            badge_path = f"assets/badges/{self.sanitize(msg.badge_url)}.png"

        # Fetches the special identifiers of a message along with the styling it needs
        design_classes, badges = self.get_special_identifier(msg, badge_path)

        # The following dominate code here is undocumented.
        # It needs a proper clean up.
        if isinstance(msg, m_types.SuperSticker):
            with tags.div(cls=f"supersticker chat_item", style=f"background: RGB{str(msg.body_color)};"):
                with tags.div(cls="cover_containers"):
                    tags.img(src=f"{pfp_path}")
                    with tags.div(cls="container_data"):
                        with tags.div(cls="container-author"):
                            with tags.div(cls="special_icon"):
                                tags.h4(f"{msg.author_name}", style=f"color: RGB{msg.author_name_color}")
                                for badge in badges:
                                    tags.img(src=badge)
                                tags.p(msg.timestamp, cls="date", style=f"color: "
                                                                        f"RGBA{msg.author_name_color + (0.6,)}")

                            tags.p(msg.currency_amount, style=f"color: RGB{msg.currency_color}")

                        if self.arguments.no_download_image:
                            sticker_path = msg.sticker
                        else:
                            sticker_path = f"assets/superstickers/{self.sanitize(msg.sticker)}.png"

                        tags.img(src=sticker_path)

        elif isinstance(msg, m_types.SuperChat):
            with tags.div(cls=f"superchat chat_item", style=f"background: RGB{str(msg.body_color)};"):
                with tags.div(cls="header_container", style=f"background: RGB{msg.header_color};"):
                    tags.img(src=f"{pfp_path}")
                    with tags.div(cls="header_data"):
                        with tags.div(cls="container-author"):
                            with tags.div(cls="special_icon"):
                                tags.h4(f"{msg.author_name}", style=f"color: RGB{msg.author_name_color}")
                                for badge in badges:
                                    tags.img(src=badge)
                                tags.p(msg.timestamp, cls="date", style=f"color: "
                                                                        f"RGBA{msg.timestamp_color + (0.6,)}")

                            tags.p(msg.currency_amount, style=f"color: RGB{msg.currency_color}")

        elif isinstance(msg, m_types.NewSponser):
            with tags.div(cls=f"new_member chat_item"):
                with tags.div(cls="cover_containers"):
                    tags.img(src=f"{pfp_path}")
                    with tags.div(cls="container_data"):
                        with tags.div(cls="container-author"):
                            with tags.div(cls="special_icon"):
                                tags.h4(f"{msg.author_name}")
                                for badge in badges:
                                    tags.img(src=badge)
                                tags.p(msg.timestamp, cls="date")

                        self.create_p_with_emojis(msg.contents)

        else:
            with tags.div(cls=f"message chat_item"):
                with tags.div(cls="message-author"):
                    tags.p(msg.timestamp, cls="date")
                    tags.img(src=f"{pfp_path}")

                    if design_classes:
                        with tags.div(cls=" ".join(design_classes)):
                            tags.h4(f"{msg.author_name}")
                            for badge in badges:
                                tags.img(src=badge)
                    elif msg.is_chat_owner:
                        tags.h4(f"{msg.author_name}", cls="owner")
                    else:
                        tags.h4(f"{msg.author_name}")
                self.create_p_with_emojis(msg.contents)

    async def export(self, *_):
        """Begins the exportation process of livechat messages into the HTML format."""
        partition_counter = 0
        while not self.completion_event.is_set():
            if 1 < self.arguments.split:
                doc = await self.create_format(index=f"[{partition_counter}]")

                if self.arguments.split == self.processed_message_count:
                    partition_counter += 1
                    self.processed_message_count = 0

                await self._write_to_file(doc, name=f"{partition_counter}.html")
            else:
                doc = await self.create_format()
                await self._write_to_file(doc, name=f"exported.html")

    @staticmethod
    def sanitize(url):
        return "".join([x for x in url if x.isalnum()])
