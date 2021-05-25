from .html import HtmlFormat
from .plaintext import PlainText


def darkhtml(output_directory, message_queue, arguments, title, completion_event):
    """Entry point to the dark theme HTML exporter

    Parameters
        output_directory: Directory to export data to
        message_queue:    Queue that stores the parsed messages from the parser.
        theme:            Theme to use for the exporter. IE Dark, or Light for HTML.
        arguments:        CLI arguments
        title:            Title of livestream
        completion_event: Event that sets when all chat messages has been fetched
    """
    return HtmlFormat(output_directory, message_queue, "dark", arguments, title, completion_event)


def lighthtml(output_directory, message_queue, arguments, title, completion_event):
    """Entry point to the light theme HTML exporter

    Parameters
        output_directory: Directory to export data to
        message_queue:    Queue that stores the parsed messages from the parser.
        theme:            Theme to use for the exporter. IE Dark, or Light for HTML.
        arguments:        CLI arguments
        title:            Title of livestream
        completion_event: Event that sets when all chat messages has been fetched
    """
    return HtmlFormat(output_directory, message_queue, "light", arguments, title, completion_event)


def plaintext(output_directory, message_queue, arguments, title, completion_event):
    """Entry point to the plaintext exporter

    Parameters
        output_directory: Directory to export data to
        message_queue:    Queue that stores parsed messages
        arguments:        CLI arguments
        title:            Title of livestream
        completion_event: Event that sets when all chat messages has been fetched
    """
    return PlainText(output_directory, message_queue, arguments, title, completion_event)
