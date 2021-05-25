from .pytchat_backend import PytchatBackend


def get_items_from_pytchat_backend(stream_id, arguments, raw_message_queue, parsed_message_queue):
    """Entry point to the pytchat backend for livechat parsing

    Parameters
        stream_id:        ID/URL of livestream
        arguments:        argparse results
    """

    return PytchatBackend(stream_id, arguments, raw_message_queue, parsed_message_queue)
