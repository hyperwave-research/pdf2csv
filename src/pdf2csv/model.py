import decimal
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Transaction:
    transaction_date: date
    statement_date: date
    account_id: str
    account_name: str
    ccy: str
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
    transactions: list[Transaction] = field(default_factory=list)

    def add_transaction_row(
        self,
        transaction_date: date,
        description: str,
        deposit: decimal,
        withdrawal: decimal,
        balance: decimal,
    ):

        record = Transaction(
            statement_date=self.statement_date,
            account_id=self.account_id,
            account_name=self.account_name,
            ccy=self.ccy,
            transaction_date=transaction_date,
            description=description,
            deposit=deposit,
            withdrawal=withdrawal,
            balance=balance,
        )
        self.transactions.append(record)
