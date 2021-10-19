import typer
from pdf_to_csv.model import Transaction
from pdf_to_csv.version import __version__
from pdf_to_csv.pdf_extractor import extract_pdf_rows, parse_pdf, format_table
from dataclass_csv import DataclassWriter

app = typer.Typer()


@app.command()
def display(input_file: str, file_format: str = "standard_chartered"):
    statements = parse_pdf(extract_pdf_rows(input_file), file_format)

    for statement in statements:
        typer.echo(f"Account name : {statement.account_name}")
        typer.echo(f"Account Number: {statement.account_id}")
        typer.echo(format_table(statement.transactions))
        typer.echo("")
        typer.echo("")


@app.command()
def extract(
    input_file: str,
    output_file: str = "./{account_id}_{ccy}_{statement_date}.csv",
    file_format: str = "standard_chartered",
    one_per_account: bool = False,
):

    statements = parse_pdf(extract_pdf_rows(input_file), file_format)
    for statement in statements:
        output_path = output_file.format(**statement.__dict__)
        with open(output_path, "w") as f:

            w = DataclassWriter(f, statement.transactions, Transaction)
            w.write()


@app.command()
def version():
    typer.echo(f"pdf-to-csv version ; {__version__}")
