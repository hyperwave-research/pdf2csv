from typing import List, Union
import pytest
from datetime import date
from pdf_to_csv.standard_chartered.states import (
    StateLookAccountNumber,
    StateProcessTable,
    StateSearchCcyOrAccountNumber,
    StateSearchTableHeader,
    StateStart,
    Statement,
    get_statement_date,
)


class TestGetStatementDate:
    @pytest.mark.parametrize(
        ["day", "month", "year", "expected_date"],
        [(1, "Jan", 2020, date(2020, 1, 1)), (1, "Dec", 2018, date(2018, 12, 1))],
    )
    def test_get_date(self, day: int, month: str, year: int, expected_date: date):
        result_date = get_statement_date(day, month, year)
        assert expected_date == result_date


class TestStateFindDateStatement:
    @pytest.mark.parametrize(
        ["row", "new_state"],
        [
            ([], StateStart),
            (
                "Statement Date : 17 Jan 2019".split(" "),
                StateLookAccountNumber,
            ),
            (
                "Statement Date : Jan 2019".split(" "),
                StateStart,
            ),
        ],
    )
    def test_extract_statement_date(self, row: List[str], new_state: type):
        state = StateStart()
        new_state_return = state(row)
        assert isinstance(new_state_return, new_state)

    def test_extract_statement_date_set_statement_date(self):
        row = "Statement Date : 17 Jan 2019".split(" ")
        expected_date = date(2019, 1, 17)
        state = StateStart()

        new_state_return = state(row)
        assert isinstance(new_state_return, StateLookAccountNumber)
        assert new_state_return._statement_date == expected_date


class TestStateLookAccountNumber:
    def test_cannot_find_account_id(self):
        state = StateLookAccountNumber(date.today(), [])
        row = "YOUR ACCOUNT ACTIVITIES".split(" ")
        new_state = state(row)
        assert isinstance(new_state, StateLookAccountNumber)
        assert new_state.found_account_number == False

    def test_find_account_row(self):
        state = StateLookAccountNumber(date.today(), [])
        account_id = "123−4−567890−1"
        row = f"My secret account  : {account_id}".split(" ")
        new_state = state(row)
        assert isinstance(new_state, StateLookAccountNumber)
        assert new_state.found_account_number == True
        assert new_state.account_id == account_id
        assert new_state.account_name_list == ["My", "secret", "account", ""]
        assert new_state.found_account_number == True

    def test_find_second_account_row_return_StateSearchTableHeader(self):
        statement_date = date(2020, 7, 14)
        account_id = "123−4−567890−1"
        state = StateLookAccountNumber(statement_date, [])
        state.account_id = account_id
        state.account_name_list = ["My", "secret", "account", ""]
        state.found_account_number = True
        new_state = state(
            [
                "John",
                "Doe",
            ]
        )
        assert isinstance(new_state, StateSearchTableHeader)
        assert new_state._statement_date == statement_date
        assert new_state._account_id == account_id
        assert new_state._account_name == "My secret account  John Doe"


class TestStateSearchTableHeader:
    def test_not_header_row(self):
        statement_date = date(2020, 7, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        state = StateSearchTableHeader(statement_date, account_id, account_name, [])
        new_state = state(["random", "row"])
        assert isinstance(new_state, StateSearchTableHeader)
        assert state is new_state

    def test_header_row_return_new_state(self):
        statement_date = date(2020, 7, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        state = StateSearchTableHeader(statement_date, account_id, account_name, [])
        new_state = state(
            [
                "Date",
                "",
                "Description",
                "",
                "Deposit",
                "",
                "Withdrawal",
                "",
                "Balance",
            ]
        )
        assert isinstance(new_state, StateSearchCcyOrAccountNumber)
        assert new_state._statement_date == statement_date
        assert new_state._account_id == account_id
        assert new_state._account_name == account_name


class TestStateSearchCcyOrAccountNumber:
    @pytest.mark.parametrize("row", [(["random"]), (["random", "row"])])
    def test_when_row_unknow_return_self(self, row: List[str]):
        statement_date = date(2020, 7, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        state = StateSearchCcyOrAccountNumber(
            statement_date, account_id, account_name, []
        )
        new_state = state(row)
        assert new_state is state

    @pytest.mark.parametrize("row", [(["USD", ""]), (["JPY"])])
    def test_when_row_is_ccy_return_process_table_state(self, row: List[str]):
        statement_date = date(2020, 7, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"

        state = StateSearchCcyOrAccountNumber(
            statement_date, account_id, account_name, []
        )
        new_state = state(row)
        assert isinstance(new_state, StateProcessTable)
        assert new_state._statement.ccy == row[0]

    def test_when_row_is_account_return_StateLookAccountNumber(self):
        statement_date = date(2020, 7, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        account_id = "987−6−543210−1"
        row = f"My secret account  : {account_id}".split(" ")
        state = StateSearchCcyOrAccountNumber(
            statement_date, account_id, account_name, []
        )
        new_state = state(row)
        assert isinstance(new_state, StateLookAccountNumber)
        assert new_state.account_id == account_id
        assert new_state.found_account_number == True


class TestStateProcessTable:
    def test_first_row_not_open_balance(self):
        statement_date = date(2020, 7, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"
        row = ["Some", "random", "row"]
        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])
        with pytest.raises(AttributeError) as ex:
            state(row)
        assert "random" in str(ex.value)

    def test_first_row_is_open_balance(self):
        statement_date = date(2020, 8, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"
        row = "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" ")
        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])
        new_state = state(row)
        assert new_state is state
        assert isinstance(new_state, StateProcessTable)
        assert new_state._current_row_date == date(2020, 7, 17)
        assert new_state._first_row == False

    @pytest.mark.parametrize(
        "statement_date,row,expected_date",
        [
            (date(2020, 6, 15), ["30", "May"], date(2020, 5, 30)),
            (date(2020, 6, 15), ["05", "Jun"], date(2020, 6, 5)),
            (date(2020, 1, 15), ["23", "Dec"], date(2019, 12, 23)),
            (date(2020, 2, 15), ["23", "Dec"], date(2019, 12, 23)),
            (date(2020, 12, 15), ["23", "Jan"], date(2020, 1, 23)),
        ],
    )
    def test_get_date(self, statement_date: date, row: List[str], expected_date: date):
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"
        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])

        return_date = state.get_date(row)
        assert expected_date == return_date

    @pytest.mark.parametrize(
        "rows,result_row",
        [
            (
                [
                    "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" "),
                    "26 Jul SCB ATM QR WDL 0108 0913   200,000.00 800,000.99".split(
                        " "
                    ),
                ],
                StateProcessTable._TempRow(
                    transaction_date=date(2020, 7, 26),
                    description=" ".join("SCB ATM QR WDL 0108 0913".split(" ")),
                    deposit=0,
                    withdrawal=200000.0,
                    balance=800000.99,
                ),
            ),
            (
                [
                    "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" "),
                    "26 Jul SCB ATM QR WDL 0108 0913 200,000.00   1200,000.99".split(
                        " "
                    ),
                ],
                StateProcessTable._TempRow(
                    transaction_date=date(2020, 7, 26),
                    description=" ".join("SCB ATM QR WDL 0108 0913".split(" ")),
                    deposit=200000.0,
                    withdrawal=0,
                    balance=1200000.99,
                ),
            ),
            (
                [
                    "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" "),
                    "SCB ATM QR WDL 0108 0913 200,000.00   1200,000.99".split(" "),
                ],
                StateProcessTable._TempRow(
                    transaction_date=date(2020, 7, 17),
                    description=" ".join("SCB ATM QR WDL 0108 0913".split(" ")),
                    deposit=200000.0,
                    withdrawal=0,
                    balance=1200000.99,
                ),
            ),
        ],
    )
    def test_parse_transaction_row(
        self, rows: List[List[str]], result_row: StateProcessTable._TempRow
    ):
        statement_date = date(2020, 8, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"

        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])
        for row in rows:
            state = state(row)

        assert isinstance(state, StateProcessTable)
        assert state._temp_row == result_row

    def test_add_transaction_row_to_statement_when_new_transaction_row(self):
        statement_date = date(2020, 8, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"
        rows = [
            "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" "),
            "26 Jul SCB ATM QR WDL       0108 0913 200,000.00   1200,000.99".split(" "),
            "SCB ATM QR WDL       0108 0913 200,000.00   1200,000.99".split(" "),
        ]
        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])
        for row in rows:
            state = state(row)

        assert isinstance(state, StateProcessTable)
        assert len(state._statement.statement_records) == 1

    def test_no_transaction_added_on_first_row(self):
        statement_date = date(2020, 8, 4)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"
        rows = [
            "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" "),
            "SCB ATM QR WDL       0108 0913 200,000.00   1200,000.99".split(" "),
        ]
        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])
        for row in rows:
            state = state(row)
        assert isinstance(state, StateProcessTable)
        assert len(state._statement.statement_records) == 0

    def test_closing_balance_row_return_StateSearchCcyOrAccountTable(self):
        statement_date = date(2020, 8, 17)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"
        rows = [
            "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" "),
            "SCB ATM QR WDL       0108 0913 200,000.00   1200,000.99".split(" "),
            "17 Aug CLOSING BALANCE 1200,000.99".split(" "),
        ]

        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])
        for row in rows:
            state = state(row)
        assert isinstance(state, StateSearchCcyOrAccountNumber)
        assert len(state.statements) == 1
        assert len(state.statements[0].statement_records) == 1

    def test_closing_balance_row_without_transactions(self):
        statement_date = date(2020, 8, 17)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"
        rows = [
            "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" "),
            "17 Aug CLOSING BALANCE 1200,000.99".split(" "),
        ]

        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])
        for row in rows:
            state = state(row)
        assert isinstance(state, StateSearchCcyOrAccountNumber)
        assert len(state.statements) == 1
        assert len(state.statements[0].statement_records) == 0

    def test_multi_row_transactions_description(self):
        statement_date = date(2020, 8, 17)
        account_id = "123−4−567890−1"
        account_name = "My secret account  John Doe"
        ccy = "USD"
        rows = [
            "17 Jul BALANCE FROM PREVIOUS STATEMENT 1,000,000.99".split(" "),
            "26 Jul my transaction 200,000.00   1200,000.99".split(" "),
            "another row of my transaction".split(" "),
        ]

        state = StateProcessTable(statement_date, account_id, account_name, ccy, [])
        for row in rows:
            state = state(row)
        assert isinstance(state, StateProcessTable)
        assert (
            state._temp_row.description
            == "my transaction another row of my transaction"
        )


def test_run_pdf():
    import pdfplumber

    pdf = pdfplumber.open("../notebook/eStatement-201908.pdf")
    state = StateStart()
    for page in pdf.pages:
        for row in page.extract_text().split("\n"):
            state = state(row.split(" "))
    assert len(state.statements) == 4
