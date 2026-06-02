from decimal import Decimal

from django.db import transaction

from . import models


DEFAULT_ACCOUNTS = {
    "1000": ("Bank", models.Account.AccountType.ASSET),
    "1100": ("Accounts Receivable", models.Account.AccountType.ASSET),
    "1200": ("Salary Advances Receivable", models.Account.AccountType.ASSET),
    "2000": ("Accounts Payable", models.Account.AccountType.LIABILITY),
    "2100": ("Salary Payable", models.Account.AccountType.LIABILITY),
    "2200": ("NSSF Payable", models.Account.AccountType.LIABILITY),
    "2300": ("VAT Payable", models.Account.AccountType.LIABILITY),
    "3000": ("Owner Equity", models.Account.AccountType.EQUITY),
    "4000": ("Security Service Revenue", models.Account.AccountType.INCOME),
    "5000": ("Salary Expense", models.Account.AccountType.EXPENSE),
    "5100": ("Employer NSSF Expense", models.Account.AccountType.EXPENSE),
    "5200": ("Operating Expense", models.Account.AccountType.EXPENSE),
    "5300": ("Salary Advance Expense", models.Account.AccountType.EXPENSE),
}


def ensure_default_accounts():
    accounts = {}
    for code, (name, account_type) in DEFAULT_ACCOUNTS.items():
        account, _created = models.Account.objects.get_or_create(
            account_code=code,
            defaults={"account_name": name, "account_type": account_type},
        )
        accounts[code] = account
    return accounts


def replace_posted_entry(reference, entry_date, description, source_module, lines, posted_by=None):
    accounts = ensure_default_accounts()
    with transaction.atomic():
        models.JournalEntry.objects.filter(reference=reference).delete()
        entry = models.JournalEntry.objects.create(
            entry_date=entry_date,
            reference=reference,
            description=description,
            source_module=source_module,
            posted_by=posted_by,
            status=models.JournalEntry.EntryStatus.POSTED,
        )
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        for account_code, debit, credit, line_description in lines:
            debit = Decimal(debit).quantize(Decimal("0.01"))
            credit = Decimal(credit).quantize(Decimal("0.01"))
            total_debit += debit
            total_credit += credit
            models.JournalLine.objects.create(
                journal_entry=entry,
                account=accounts[account_code],
                debit=debit,
                credit=credit,
                description=line_description,
            )
        if total_debit != total_credit:
            raise ValueError(f"Journal entry {reference} is not balanced: {total_debit} != {total_credit}")
    return entry


def post_invoice(invoice, posted_by=None):
    return replace_posted_entry(
        reference=f"INV-{invoice.id}",
        entry_date=invoice.invoice_date,
        description=f"Invoice {invoice.invoice_number}",
        source_module="invoice",
        posted_by=posted_by,
        lines=[
            ("1100", invoice.total_amount, 0, "Customer invoice receivable"),
            ("4000", 0, invoice.subtotal_amount, "Security service revenue"),
            ("2300", 0, invoice.vat_amount, "VAT on invoice"),
        ],
    )


def post_payment(payment, posted_by=None):
    credit_account = "1100" if payment.invoice_id else "2100" if payment.employee_id else "2000"
    return replace_posted_entry(
        reference=f"PAY-{payment.id}",
        entry_date=payment.payment_date,
        description=f"Payment {payment.transaction_ref or payment.id}",
        source_module="payment",
        posted_by=posted_by,
        lines=[
            ("1000", payment.amount, 0, "Payment received or paid through bank"),
            (credit_account, 0, payment.amount, "Payment settlement"),
        ],
    )


def post_expense(expense, posted_by=None):
    return replace_posted_entry(
        reference=f"EXP-{expense.id}",
        entry_date=expense.expense_date,
        description=f"Expense {expense.category}",
        source_module="expense",
        posted_by=posted_by,
        lines=[
            ("5200", expense.amount, 0, expense.description or expense.category),
            ("1000", 0, expense.amount, "Expense paid from bank"),
        ],
    )


def post_salary(salary, posted_by=None):
    return replace_posted_entry(
        reference=f"PAYROLL-{salary.id}",
        entry_date=salary.pay_period_end,
        description=f"Payroll for {salary.employee.full_name}",
        source_module="payroll",
        posted_by=posted_by,
        lines=[
            ("5000", salary.gross_pay, 0, "Employee gross payroll"),
            ("5100", salary.nssf_employer, 0, "Employer NSSF contribution"),
            ("2100", 0, salary.net_salary, "Net salary payable"),
            ("2200", 0, salary.nssf_employee + salary.nssf_employer, "NSSF payable"),
            ("2000", 0, salary.deductions, "Other payroll deductions payable"),
            ("1200", 0, salary.advance_deduction, "Salary advance recovered from payroll"),
        ],
    )


def post_all_accounting(posted_by=None):
    ensure_default_accounts()
    entries = []
    for invoice in models.Invoice.objects.all():
        entries.append(post_invoice(invoice, posted_by=posted_by))
    for payment in models.Payment.objects.all():
        entries.append(post_payment(payment, posted_by=posted_by))
    for expense in models.Expense.objects.all():
        entries.append(post_expense(expense, posted_by=posted_by))
    for salary in models.Salary.objects.all():
        entries.append(post_salary(salary, posted_by=posted_by))
    return entries
