from typing import Iterable, List

from fpdf import FPDF, XPos, YPos


def _sanitize_text(value: str) -> str:
    return value.encode("latin-1", "ignore").decode("latin-1")


class PdfTableBuilder:
    def __init__(self, title: str, headers: List[str], orientation: str = "L"):
        self.pdf = FPDF(orientation=orientation, unit="mm", format="A4")  # type: ignore
        self.pdf.set_auto_page_break(auto=True, margin=12)
        self.pdf.add_page()
        self.pdf.set_title(title)

        self.pdf.set_font("Helvetica", "B", 14)
        self.pdf.cell(
            0,
            10,
            _sanitize_text(title),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

        self.headers = headers
        self.col_widths = self._calc_col_widths(headers)
        self._render_header()
        self.line_height = 4

    def _calc_col_widths(self, headers: List[str]) -> List[float]:
        page_width = self.pdf.w - self.pdf.l_margin - self.pdf.r_margin
        base_width = page_width / len(headers)
        return [base_width for _ in headers]

    def _render_header(self) -> None:
        self.pdf.set_font("Helvetica", "B", 9)
        for header, width in zip(self.headers, self.col_widths):
            self.pdf.cell(width, 8, _sanitize_text(header), border=1)
        self.pdf.ln(8)

    def _wrap_text(self, text: str, width: float) -> List[str]:
        if not text:
            return [""]

        words = text.split(" ")
        lines: List[str] = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            if self.pdf.get_string_width(candidate) <= width:
                current = candidate
                continue

            if current:
                lines.append(current)
                current = word
                continue

            # Single word longer than width -> hard split
            chunk = ""
            for char in word:
                if self.pdf.get_string_width(chunk + char) <= width:
                    chunk += char
                else:
                    lines.append(chunk)
                    chunk = char
            current = chunk

        if current:
            lines.append(current)

        return lines

    def add_row(self, row: Iterable[str]) -> None:
        self.pdf.set_font("Helvetica", "", 8)
        values = [_sanitize_text(value) for value in row]
        wrapped = [
            self._wrap_text(value, width - 2)
            for value, width in zip(values, self.col_widths)
        ]
        max_lines = max(len(lines) for lines in wrapped) if wrapped else 1
        row_height = max_lines * self.line_height

        if self.pdf.get_y() + row_height > self.pdf.page_break_trigger:
            self.pdf.add_page()
            self._render_header()

        x_start = self.pdf.get_x()
        y_start = self.pdf.get_y()

        for lines, width in zip(wrapped, self.col_widths):
            self.pdf.set_xy(x_start, y_start)
            self.pdf.multi_cell(width, self.line_height, "\n".join(lines), border=1)
            x_start += width

        self.pdf.set_xy(self.pdf.l_margin, y_start + row_height)

    def output(self) -> bytes:
        pdf_bytes = self.pdf.output(dest="S")
        if isinstance(pdf_bytes, str):
            return pdf_bytes.encode("latin-1", "ignore")
        return pdf_bytes

    def output_to_file(self, file_path: str) -> None:
        self.pdf.output(file_path)
