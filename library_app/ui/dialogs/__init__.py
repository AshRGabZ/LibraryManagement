"""Modal dialogs used by the main tabs."""

from .book_dialog import BookDialog
from .borrow_dialog import BorrowDialog
from .label_preview_dialog import LabelPreviewDialog
from .manage_copies_dialog import ManageCopiesDialog
from .renew_dialog import RenewDialog

__all__ = [
    "BookDialog",
    "BorrowDialog",
    "LabelPreviewDialog",
    "ManageCopiesDialog",
    "RenewDialog",
]
