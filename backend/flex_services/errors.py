"""Shared exception types for Flex Report adapters."""


class FlexInputError(ValueError):
    """An uploaded file is unusable — wrong columns, wrong sheet, wrong layout.

    Raised only for problems the operator can fix by uploading a corrected file, so the
    API can return a 400 with the message shown verbatim. Every other exception is a
    genuine failure and is logged with a traceback as a 500.
    """

    def __init__(self, message, validation=None, *, title=None, summary=None, guidance=None,
                 files=None, employee_ids=None):
        super().__init__(message)
        self.validation = validation or []
        self.feedback = {
            'title': title or 'Check the uploaded files',
            'message': summary or message,
            'guidance': guidance or 'Review the file details above, then upload the corrected workbook and try again.',
            'files': files or [],
            'employee_ids': list(employee_ids) if employee_ids is not None else [],
        }
