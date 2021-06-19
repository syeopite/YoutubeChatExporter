import argparse
import asyncio

import backends
from misc import styling


async def main(arguments):
    """Main entry into the program

    This function
      - fetches a backend (only pytchat for now)
      - Setup assets and directories
      - Initialize processing chain through the backend's begin method.
        - This means that messages would get asynchronously fetched, parsed, and exported into the selectred format
         all at once. Massively improving the speed

    Parameter:
        arguments: argparse results
    """
    for stream_id in arguments.youtube_id:
        # Fetch backend
        chosen_backend = "pytchat"
        raw_message_queue = asyncio.Queue(0)
        parsed_message_queue = asyncio.Queue(0)

        backend_constructor = getattr(backends, f"get_items_from_{chosen_backend}_backend", None)
        backend = backend_constructor(stream_id, arguments, raw_message_queue, parsed_message_queue)
        await backend.begin()


def validate_partitions(num):
    num = int(num)
    if num < 1:
        raise argparse.ArgumentTypeError("What? I can't create partitions with less than a single message each!")
    return num


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        prog="YoutubeChatExporter",
        description="A quick program to export YouTube live-chats in various different formats",
        formatter_class=lambda prog: styling.StylizedHelpFormatter(prog)
    )

    arg_parser.add_argument(
        "youtube_id",
        metavar="Youtube identifier",
        type=str,
        help="Youtube IDs or URLs of streams to extract chat from",
        nargs="+",
    )

    arg_parser.add_argument(
        "-o", "--output",
        type=str,
        metavar="output",
        help="directory to export live chat(s) to"
    )

    arg_parser.add_argument(
        "-f", "--format",
        type=str,
        metavar="format",
        choices=["DarkHtml", "LightHtml", "PlainText", "JSON"],
        default="DarkHtml",
        help="format to archive chat as. Acceptable values are: DarkHtml (default),"
             " LightHtml, PlainText, JSON"
    )

    arg_parser.add_argument(
        "-s", "--split",
        type=int,
        metavar="partitions",
        default=1,
        help="Split output into partitions with the given amount of messages"
    )

    arg_parser.add_argument(
        "--no-download-image",
        help="use pfp urls in html output instead of downloading to disk",
        action="store_true"
    )

    arg_parser.add_argument(
        "--update",
        help="Reconstruct output without redownloading assets.",
        action="store_true"
    )

    args = arg_parser.parse_args()
    asyncio.run(main(args))
