import typer
from pdf_to_csv.version import __version__
from pdf_to_csv.pdf_extractor import extract_pdf_rows, parse_pdf, format_table

app = typer.Typer()


@app.command()
def output(
    filename: str,
):
    statements = parse_pdf(extract_pdf_rows(filename), "standard_chartered")

    for statement in statements:
        typer.echo(f"Account name : {statement.account_name}")
        typer.echo(f"Account Number: {statement.account_id}")
        typer.echo(format_table(statement.transactions))
        typer.echo("")
        typer.echo("")


@app.command()
def version():
    typer.echo(f"pdf-to-csv version ; {__version__}")
