import dataclasses
import decimal
import pdfplumber
from datetime import date
from pdf_to_csv.model import Statement, Transaction
from pdf_to_csv.parsers.standard_chartered.states import StateStart
from prettytable import PrettyTable, MARKDOWN

parsers = {"standard_chartered": StateStart()}


def extract_pdf_rows(filename: str) -> enumerate[list[str]]:
    pdf_file = pdfplumber.open(filename)

    for page in pdf_file.pages:
        for row in page.extract_text().split("\n"):
            yield row


def parse_pdf(rows: enumerate[list[str]], document_type: str) -> list[Statement]:
    parser = parsers[document_type]

    for row in rows:
        parser = parser(row.split(" "))

    return parser.statements


def format_table(transactions: list[Transaction]) -> str:
    table = PrettyTable()
    table.set_style(MARKDOWN)
    table.field_names = [field.name for field in dataclasses.fields(Transaction)]
    table.align = "l"
    for transaction in transactions:
        table.add_row(transaction.__dict__.copy().values())

    for col_float in [
        field.name
        for field in dataclasses.fields(Transaction)
        if (field.type is float) | (field.type is decimal)
    ]:
        table.float_format[col_float] = "3.2"
        table.align[col_float] = "r"

    for col_float in [
        field.name for field in dataclasses.fields(Transaction) if (field.type is date)
    ]:
        table.align[col_float] = "r"

    return table.get_string(
        fields=[
            f_name
            for f_name in table.field_names
            if f_name not in ["account_name", "account_id", "statement_date"]
        ]
    )
