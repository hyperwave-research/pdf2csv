import decimal
from dataclasses import dataclass, field
from datetime import date
from typing import Any

@dataclass
class Transaction:
    transaction_date: date
    account_id: str
    account_name: str
    ccy: str
    record_date: str
    description: str
    deposit: decimal
    withdrawal: decimal
    balance: decimal


@dataclass
class Statement:
    statement_date: date
    account_id: str
    account_name: str
    ccy: str
    statement_records: list[dict[str, Any]] = field(default_factory=list)

    def add_transaction_row(
        self,
        transaction_date: date,
        description: str,
        deposit: decimal,
        withdrawal: decimal,
        balance: decimal,
    ):

        record = Transaction(
            transaction_date=self.statement_date,
            account_id=self.account_id,
            account_name=self.account_name,
            ccy=self.ccy,
            record_date=transaction_date,
            description=description,
            deposit=deposit,
            withdrawal=withdrawal,
            balance=balance,
        )
        self.statement_records.append(record)
