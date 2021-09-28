import decimal
import re
from abc import ABCMeta, abstractmethod
from calendar import month_abbr
from dataclasses import dataclass
from datetime import date, datetime

from pdf_to_csv.currencies import ISO_CODE
from pdf_to_csv.model import Statement

MONTH_ABBR = [m for m in month_abbr]


def get_statement_date(day: int, month: str, year: int) -> date:
    momth_int = datetime.strptime(month, "%b").month
    return date(year, momth_int, day)


def format_float_str(s_number: str) -> str:
    return s_number.replace(",", "")


def is_float(s_number: str) -> bool:
    return format_float_str(s_number).replace(".", "", 1).isdigit()



class State(metaclass=ABCMeta):
    @property
    @abstractmethod
    def statements(self) -> list[Statement]:
        ...

    _state_name = "Unknow"

    def __str__(self) -> str:
        return f"State => {self._state_name}"


class StateStart(State):
    @property
    def statements(self) -> list[Statement]:
        return self._statements

    def __init__(self, statements: list[Statement] = []):
        self._statements = statements

    _state_name = "Start"
    DAY_OFFSET = 1
    MONTH_OFFSET = 2
    YEAR_OFFSET = 3

    def __call__(self, row: list[str]) -> State:
        if self.is_statement_row(row) and self.is_statement_date(row):
            statement_date = self.extract_statement_date(row)
            return StateLookAccountNumber(statement_date, self._statements)
        return self

    def is_statement_row(self, row) -> bool:
        if len(row) < 2:
            return False

        return row[0] == "Statement" and row[1] == "Date"

    def is_statement_date(self, row: list[str]) -> bool:
        semi_colon_index = row.index(":")
        return (
            row[semi_colon_index + self.DAY_OFFSET].isdigit()
            and row[semi_colon_index + self.YEAR_OFFSET].isdigit()
            and len(row[semi_colon_index + self.MONTH_OFFSET]) == 3
        )

    def extract_statement_date(self, row: list[str]) -> date:
        if not self.is_statement_date(row):
            return None

        semi_colon_index = row.index(":")
        return get_statement_date(
            int(row[semi_colon_index + self.DAY_OFFSET]),
            row[semi_colon_index + self.MONTH_OFFSET],
            int(row[semi_colon_index + self.YEAR_OFFSET]),
        )


def is_account_number(row: list[str]) -> bool:
    account_number_regex = re.compile(r"^\d{3}−\d−\d{6}−\d")
    return account_number_regex.match(row[-1]) != None


def get_account_id(row: list[str]) -> str:
    return row[-1]


def get_account_name(row: list[str]) -> list[str]:
    semi_colon_id = row.index(":")
    return row[:semi_colon_id]


class StateLookAccountNumber(State):
    @property
    def statements(self) -> list[Statement]:
        return self._statements

    def __init__(self, statement_date: date, statements: list[Statement]):
        self._statement_date = statement_date
        self._statements = statements
        self.found_account_number = False
        self.account_id = None
        self.account_name_list = None

    def __call__(self, row: list[str]) -> State:
        if not self.found_account_number and is_account_number(row):
            self.found_account_number = True
            self.account_id = get_account_id(row)
            self.account_name_list = get_account_name(row)
            return self
        if self.found_account_number:
            self.account_name_list = self.account_name_list + row
            account_name = " ".join(self.account_name_list)
            return StateSearchTableHeader(
                self._statement_date, self.account_id, account_name, self._statements
            )
        return self


class StateSearchTableHeader(State):
    @property
    def statements(self) -> list[Statement]:
        return self._statements

    def __init__(
        self,
        statement_date: date,
        account_id: str,
        account_name: str,
        statements: list[Statement],
    ):
        self._statement_date = statement_date
        self._account_id = account_id
        self._account_name = account_name
        self._statements = statements

    def is_statement_header(self, row: list[str]) -> bool:
        return row == [
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

    def __call__(self, row: list[str]) -> State:
        if not self.is_statement_header(row):
            return self

        return StateSearchCcyOrAccountNumber(
            self._statement_date, self._account_id, self._account_name, self._statements
        )


class StateSearchCcyOrAccountNumber(State):
    @property
    def statements(self) -> list[Statement]:
        return self._statements

    def __init__(
        self,
        statement_date: date,
        account_id: str,
        account_name: str,
        statements: list[Statement],
    ):
        self._statement_date = statement_date
        self._account_id = account_id
        self._account_name = account_name
        self._statements = statements

    def __call__(self, row: list[str]) -> State:

        if len([w for w in row if w != ""]) == 1 and row[0] in ISO_CODE:
            return StateProcessTable(
                statement_date=self._statement_date,
                account_id=self._account_id,
                account_name=self._account_name,
                ccy=row[0],
                statements=self._statements,
            )
        if is_account_number(row):
            new_state = StateLookAccountNumber(
                statement_date=self._statement_date, statements=self.statements
            )
            return new_state(row)
        return self


class StateProcessTable(State):
    @property
    def statements(self) -> list[Statement]:
        return self._statements

    @dataclass
    class _TempRow:
        transaction_date: str
        description: str
        deposit: decimal
        withdrawal: decimal
        balance: decimal

    def __init__(
        self,
        statement_date: date,
        account_id: str,
        account_name: str,
        ccy: str,
        statements: list[Statement],
    ):
        self._statement = Statement(
            statement_date=statement_date,
            account_id=account_id,
            account_name=account_name,
            ccy=ccy,
        )
        self._statements = statements
        self._first_row = True
        self._current_row_date = date.min
        self._temp_row = None

    def _is_open_balance_row(self, row: list[str]) -> bool:
        open_balance_words = set(["BALANCE", "FROM", "PREVIOUS", "STATEMENT"])
        return open_balance_words.issubset(row)

    def _is_closing_balance_row(self, row: list[str]) -> bool:
        closing_balance_words = set(["CLOSING", "BALANCE"])
        return closing_balance_words.issubset(row)

    def is_row_start_with_date(self, row: list[str]) -> bool:
        return str.isdigit(row[0]) and (row[1] in MONTH_ABBR)

    def is_transaction_row(self, row: list[str]) -> bool:
        return is_float(row[-1]) and (is_float(row[-2]) or is_float(row[-4]))

    def get_description(self, row: list[str]) -> str:
        low_index = 2 if self.is_row_start_with_date(row) else 0
        high_index = -4
        return " ".join(row[low_index:high_index])

    def get_float_value(self, row: list[str], index: int) -> float:
        return float(format_float_str(row[index])) if is_float(row[index]) else 0

    def get_date(self, row: list[str]) -> date:
        if not (self.is_row_start_with_date(row)):
            raise Exception(f"Current row doesn't start with date. {row}")

        day = int(row[0])
        month = MONTH_ABBR.index(row[1])
        year = (
            self._statement.statement_date.year
            if self._statement.statement_date.month - month >= 0
            else self._statement.statement_date.year - 1
        )

        return date(year, month, day)

    def __call__(self, row: list[str]) -> State:
        if self._first_row:
            if self._is_open_balance_row(row):
                self._current_row_date = self.get_date(row)
                self._first_row = False
                return self
            else:
                raise AttributeError(f"Expected open Balance Row. got {row}")

        if self.is_transaction_row(row):
            if self._temp_row != None:
                self._statement.add_transaction_row(
                    transaction_date=self._temp_row.transaction_date,
                    description=self._temp_row.description,
                    deposit=self._temp_row.deposit,
                    withdrawal=self._temp_row.withdrawal,
                    balance=self._temp_row.balance,
                )
                self._temp_row = None

            if self.is_row_start_with_date(row):
                self._current_row_date = self.get_date(row)

            self._temp_row = StateProcessTable._TempRow(
                transaction_date=self._current_row_date,
                description=self.get_description(row),
                deposit=self.get_float_value(row, -4),
                withdrawal=self.get_float_value(row, -2),
                balance=self.get_float_value(row, -1),
            )

            return self

        if self._is_closing_balance_row(row):
            if self._temp_row != None:
                self._statement.add_transaction_row(
                    transaction_date=self._temp_row.transaction_date,
                    description=self._temp_row.description,
                    deposit=self._temp_row.deposit,
                    withdrawal=self._temp_row.withdrawal,
                    balance=self._temp_row.balance,
                )
                self._temp_row = None

            self._statements.append(self._statement)
            return StateSearchCcyOrAccountNumber(
                statement_date=self._statement.statement_date,
                account_id=self._statement.account_id,
                account_name=self._statement.account_name,
                statements=self.statements,
            )

        self._temp_row.description = f"{self._temp_row.description} {' '.join(row)}"
        return self
