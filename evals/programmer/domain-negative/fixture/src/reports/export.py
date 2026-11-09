import csv
import io
from collections.abc import Sequence

from reports.invoices import InvoiceRow


def export_csv(rows: Sequence[InvoiceRow]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Invoice", "Issued", "Due", "Total"])
    for row in rows:
        writer.writerow(
            [
                f"INV-{row.number:05d}",
                row.issued_on.strftime("%d %B %Y"),
                row.due_on.strftime("%d %B %Y"),
                f"£{row.total_pence // 100:,}.{row.total_pence % 100:02d}",
            ]
        )
    return buffer.getvalue()


def export_markdown(rows: Sequence[InvoiceRow]) -> str:
    lines = ["| Invoice | Issued | Due | Total |", "| --- | --- | --- | --- |"]
    for row in rows:
        number = f"INV-{row.number:05d}"
        issued = row.issued_on.strftime("%d %B %Y")
        due = row.due_on.strftime("%d %B %Y")
        total = f"£{row.total_pence // 100:,}.{row.total_pence % 100:02d}"
        lines.append(f"| {number} | {issued} | {due} | {total} |")
    return "\n".join(lines)
