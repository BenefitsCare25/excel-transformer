"""Shared exception types for Flex Report adapters."""


class FlexInputError(ValueError):
    """An uploaded file is unusable — wrong columns, wrong sheet, wrong layout.

    Raised only for problems the operator can fix by uploading a corrected file, so the
    API can return a 400 with the message shown verbatim. Every other exception is a
    genuine failure and is logged with a traceback as a 500.
    """
