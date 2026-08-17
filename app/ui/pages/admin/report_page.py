import os
import tempfile
import time

from PySide6.QtGui import QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services import report_service
from app.ui.widgets import DatePicker, create_full_width_button, format_money

REPORT_NOTES = [
    "The \"Net Price Contribution\" in this report is the product's net return after "
    "subtracting the raw material cost.",
    "Different processing steps of the same product (e.g. \"Step 1\", \"Step 2\") are shown "
    "on separate lines; each line is the sum of all production records entered for that "
    "step on that day.",
    "Duration values are calculated from the unit processing time and indicate the time "
    "spent producing the stated quantity.",
]

REPORTS_LIST_VISIBLE_ROWS = 20
REPORT_ROW_HEIGHT = 38
DOWNLOAD_BUTTON_MIN_WIDTH = 120


def _format_hours_minutes(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{hours}:{minutes:02d}"


def _build_report_html(data: report_service.ReportData) -> str:
    date_text = data.report_date.strftime("%d.%m.%Y")
    notes_html = "".join(f"<li>{note}</li>" for note in REPORT_NOTES)

    parts = [
        f"<h1>Daily Production Report — {date_text}</h1>",
        "<h3>Important Notes</h3>",
        f"<ul>{notes_html}</ul>",
        "<h2>Daily Production</h2>",
    ]

    if not data.sections:
        parts.append("<p>There are no production records for this date.</p>")

    for section in data.sections:
        parts.append(f"<h3>{section.customer_name}</h3><ul>")
        for line in section.lines:
            parts.append(
                f"<li>{line.product_name} (Step {line.step_no}) — {line.quantity} units, "
                f"{format_money(line.price_contribution)} net price contribution, "
                f"{_format_hours_minutes(line.work_seconds)} (h:mm) time spent</li>"
            )
        parts.append("</ul>")

    totals = data.totals
    parts.append("<h2>Summary</h2>")
    parts.append(f"<p><b>Customers:</b> {', '.join(totals.customer_names) or '—'}</p>")
    parts.append(f"<p><b>Products:</b> {', '.join(totals.product_names) or '—'}</p>")
    parts.append(f"<p><b>Total Quantity Produced:</b> {totals.quantity}</p>")
    parts.append(
        f"<p><b>Total Net Price Contribution:</b> {format_money(totals.price_contribution)}</p>"
    )
    parts.append(
        f"<p><b>Total Time Spent:</b> {_format_hours_minutes(totals.work_seconds)} (h:mm)</p>"
    )

    return "<html><body>" + "".join(parts) + "</body></html>"


TEMP_FILE_DELETE_ATTEMPTS = 3
TEMP_FILE_DELETE_RETRY_SECONDS = 0.1


def _remove_temp_file_safely(path: str) -> None:
    """On Windows a newly written file can stay locked briefly (antivirus scan, file
    indexer, etc.) and os.remove() can raise PermissionError. Retries a few times with
    short delays; gives up silently if it still can't be deleted — the OS periodically
    cleans the temp folder anyway, so this isn't a critical error.
    """
    for attempt in range(TEMP_FILE_DELETE_ATTEMPTS):
        try:
            os.remove(path)
            return
        except OSError:
            if attempt == TEMP_FILE_DELETE_ATTEMPTS - 1:
                return
            time.sleep(TEMP_FILE_DELETE_RETRY_SECONDS)


def _render_pdf_bytes(html: str) -> bytes:
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setOutputFileName(temp_path)

        document = QTextDocument()
        document.setHtml(html)
        document.print_(printer)

        with open(temp_path, "rb") as pdf_file:
            return pdf_file.read()
    finally:
        _remove_temp_file_safely(temp_path)


class _ReportListRow(QWidget):
    def __init__(self, report_id: int, display_name: str, on_download, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addWidget(QLabel(display_name), 1)

        download_button = QPushButton("Download")
        download_button.setMinimumWidth(DOWNLOAD_BUTTON_MIN_WIDTH)
        download_button.clicked.connect(lambda: on_download(report_id, display_name))
        layout.addWidget(download_button)


class ReportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.date_input = DatePicker()

        generate_button = create_full_width_button("Generate Report")
        generate_button.clicked.connect(self._on_generate_clicked)

        self.reports_list = QListWidget()
        self.reports_list.setFixedHeight(REPORTS_LIST_VISIBLE_ROWS * REPORT_ROW_HEIGHT)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Report Date:"))
        layout.addWidget(self.date_input)
        layout.addWidget(generate_button)
        layout.addWidget(QLabel("Recently Generated Reports:"))
        layout.addWidget(self.reports_list)
        layout.addStretch(1)

        self.refresh()

    def refresh(self) -> None:
        self._reports = report_service.list_recent_reports()
        self.reports_list.clear()
        for report in self._reports:
            item = QListWidgetItem()
            row_widget = _ReportListRow(report.id, report.display_name, self._on_download)
            item.setSizeHint(row_widget.sizeHint())
            self.reports_list.addItem(item)
            self.reports_list.setItemWidget(item, row_widget)

    def _on_generate_clicked(self) -> None:
        report_date = self.date_input.date().toPython()

        if not report_service.has_production_for_date(report_date):
            QMessageBox.warning(
                self,
                "No Data Found",
                f"There is no data entered for {report_date.strftime('%d.%m.%Y')}.",
            )
            return

        data = report_service.build_report_data(report_date)
        html = _build_report_html(data)
        pdf_data = _render_pdf_bytes(html)
        report_service.save_report(report_date, pdf_data)

        self.refresh()

    def _on_download(self, report_id: int, display_name: str) -> None:
        pdf_data = report_service.get_report_pdf(report_id)
        if pdf_data is None:
            QMessageBox.warning(self, "Error", "Report not found.")
            return

        file_path, _selected_filter = QFileDialog.getSaveFileName(
            self, "Save Report", f"{display_name}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        with open(file_path, "wb") as pdf_file:
            pdf_file.write(pdf_data)
