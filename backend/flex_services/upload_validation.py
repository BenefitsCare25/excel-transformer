"""Content-signature validation for Flex Report uploads.

A file's extension can lie. A real .xlsx/.xlsm is a ZIP archive (starts with ``PK``);
a password-protected workbook and the legacy binary .xls format are both OLE2 compound
documents (``D0 CF 11 E0``). Either passes an extension check yet later crashes pandas
deep in a run with "XLRDError: Can't find workbook in OLE2 compound document". Sniffing
the first bytes on upload turns that cryptic failure into an actionable message.
"""

_OLE2_SIGNATURE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
# Encrypted OOXML stores the real workbook in an 'EncryptedPackage' stream; the stream
# name lives UTF-16LE in the compound-file directory, so scanning the bytes tells an
# encrypted (password-protected) file apart from a genuine legacy .xls.
_ENCRYPTED_MARKER = 'EncryptedPackage'.encode('utf-16-le')
# The directory sector of a real uploaded data file sits well within this; a bounded read
# keeps a multi-MB workbook off the heap. A miss only downgrades the message specificity -
# the file is rejected either way.
_SCAN_LIMIT = 1024 * 1024


def flex_signature_error(path, label):
    """Operator-facing message if the file content isn't a real .xlsx/.xlsm workbook,
    else None. I/O errors defer to the downstream reader."""
    try:
        with open(path, 'rb') as fh:
            head = fh.read(8)
            if head.startswith(b'PK'):
                return None
            if head.startswith(_OLE2_SIGNATURE):
                encrypted = _ENCRYPTED_MARKER in head + fh.read(_SCAN_LIMIT)
            else:
                encrypted = False
    except OSError:
        return None
    if head.startswith(_OLE2_SIGNATURE):
        if encrypted:
            return (f"'{label}' is password-protected (encrypted). Open it in Excel, remove the "
                    "password (File -> Info -> Protect Workbook -> Encrypt with Password -> clear it "
                    "and OK), save, then re-upload.")
        return (f"'{label}' is an old-format Excel file (.xls) saved with a .xlsx name. "
                "Open it in Excel, choose File -> Save As -> Excel Workbook (.xlsx), then re-upload.")
    return (f"'{label}' isn't a valid .xlsx/.xlsm workbook. Re-save it in Excel as "
            "Excel Workbook (.xlsx), then re-upload.")
