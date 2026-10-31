"""CSV downloads for the lists. Each export runs the same filters as the list it sits beside."""

import csv
import io
from collections.abc import Iterable, Iterator
from datetime import date

from fastapi.responses import StreamingResponse

# A spreadsheet runs a cell that starts with one of these as a formula. Customer names are typed by people.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _cell(value) -> object:
    if value is None:
        return ""
    if isinstance(value, str) and value.startswith(_FORMULA_START):
        return "'" + value
    return value


def csv_response(name: str, header: list[str], rows: Iterable[Iterable]) -> StreamingResponse:
    """`name` becomes `<name>-<today>.csv`. Starts with a byte-order mark so Excel reads ₹ and accents."""

    def chunks() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        buffer.write("\ufeff")
        writer.writerow(header)
        for row in rows:
            writer.writerow([_cell(v) for v in row])
            if buffer.tell() > 64_000:
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate()
        yield buffer.getvalue()

    filename = f"{name}-{date.today()}.csv"
    return StreamingResponse(
        chunks(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
