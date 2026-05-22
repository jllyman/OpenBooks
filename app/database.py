from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, create_engine, func, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)

    jobs: Mapped[list["Job"]] = relationship(back_populates="customer")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="customer")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    quotes: Mapped[list["Quote"]] = relationship(back_populates="department")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="department")


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(160), default="OpenBooks")
    logo_filename: Mapped[str | None] = mapped_column(String(240))
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    website: Mapped[str | None] = mapped_column(String(160))
    address_line_1: Mapped[str | None] = mapped_column(String(160))
    address_line_2: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(40))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    name: Mapped[str] = mapped_column(String(140))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="Planned")
    due_date: Mapped[date | None] = mapped_column(Date)
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    customer: Mapped[Customer] = relationship(back_populates="jobs")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="job")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="job")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    quote_number: Mapped[str] = mapped_column(String(40), unique=True)
    issue_date: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    notes: Mapped[str | None] = mapped_column(Text)

    customer: Mapped[Customer] = relationship(back_populates="quotes")
    department: Mapped[Department | None] = relationship(back_populates="quotes")
    job: Mapped[Job | None] = relationship(back_populates="quotes")
    line_items: Mapped[list["QuoteLineItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )
    images: Mapped[list["WorkImage"]] = relationship(back_populates="quote", cascade="all, delete-orphan")


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"))
    description: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    quote: Mapped[Quote] = relationship(back_populates="line_items")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True)
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    notes: Mapped[str | None] = mapped_column(Text)

    customer: Mapped[Customer] = relationship(back_populates="invoices")
    department: Mapped[Department | None] = relationship(back_populates="invoices")
    job: Mapped[Job | None] = relationship(back_populates="invoices")
    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")
    images: Mapped[list["WorkImage"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    description: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    invoice: Mapped[Invoice] = relationship(back_populates="line_items")


class WorkImage(Base):
    __tablename__ = "work_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id"))
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    filename: Mapped[str] = mapped_column(String(240))
    original_filename: Mapped[str | None] = mapped_column(String(240))
    caption: Mapped[str | None] = mapped_column(String(200))

    quote: Mapped[Quote | None] = relationship(back_populates="images")
    invoice: Mapped[Invoice | None] = relationship(back_populates="images")


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_name: Mapped[str] = mapped_column(String(140))
    reference: Mapped[str | None] = mapped_column(String(60))
    category: Mapped[str | None] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Open")
    notes: Mapped[str | None] = mapped_column(Text)

    payments: Mapped[list["Payment"]] = relationship(back_populates="bill")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_type: Mapped[str] = mapped_column(String(40))
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"))
    bill_id: Mapped[int | None] = mapped_column(ForeignKey("bills.id"))
    payment_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    method: Mapped[str | None] = mapped_column(String(60))
    notes: Mapped[str | None] = mapped_column(Text)

    invoice: Mapped[Invoice | None] = relationship(back_populates="payments")
    bill: Mapped[Bill | None] = relationship(back_populates="payments")


engine = None
SessionLocal = None


def init_db(database_path: Path) -> None:
    global engine, SessionLocal
    engine = create_engine(f"sqlite:///{database_path}", future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    ensure_schema_compatibility()


def ensure_schema_compatibility() -> None:
    if engine is None:
        return

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    with engine.begin() as connection:
        if "quotes" in table_names:
            quote_columns = {column["name"] for column in inspector.get_columns("quotes")}
            if "department_id" not in quote_columns:
                connection.execute(text("ALTER TABLE quotes ADD COLUMN department_id INTEGER"))

        if "invoices" in table_names:
            invoice_columns = {column["name"] for column in inspector.get_columns("invoices")}
            if "department_id" not in invoice_columns:
                connection.execute(text("ALTER TABLE invoices ADD COLUMN department_id INTEGER"))


@contextmanager
def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database has not been initialized.")
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def money(value: Decimal | int | float | None) -> Decimal:
    if value in (None, ""):
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def invoice_total(invoice: Invoice) -> Decimal:
    total = Decimal("0.00")
    for item in invoice.line_items:
        total += money(item.quantity) * money(item.unit_price)
    return total


def quote_total(quote: Quote) -> Decimal:
    total = Decimal("0.00")
    for item in quote.line_items:
        total += money(item.quantity) * money(item.unit_price)
    return total


def invoice_paid(invoice: Invoice) -> Decimal:
    total = Decimal("0.00")
    for payment in invoice.payments:
        if payment.payment_type == "AR":
            total += money(payment.amount)
    return total


def bill_paid(bill: Bill) -> Decimal:
    total = Decimal("0.00")
    for payment in bill.payments:
        if payment.payment_type == "AP":
            total += money(payment.amount)
    return total


def dashboard_snapshot(session: Session) -> dict[str, Decimal | int]:
    invoices = session.scalars(select(Invoice)).all()
    bills = session.scalars(select(Bill)).all()
    jobs = session.scalars(select(Job)).all()

    ar_open = Decimal("0.00")
    for invoice in invoices:
        ar_open += max(invoice_total(invoice) - invoice_paid(invoice), Decimal("0.00"))

    ap_open = Decimal("0.00")
    for bill in bills:
        ap_open += max(money(bill.amount) - bill_paid(bill), Decimal("0.00"))

    revenue = sum((invoice_total(invoice) for invoice in invoices), Decimal("0.00"))
    expenses = sum((money(bill.amount) for bill in bills), Decimal("0.00"))
    active_jobs = sum(1 for job in jobs if job.status not in {"Done", "Cancelled"})

    return {
        "ar_open": ar_open,
        "ap_open": ap_open,
        "revenue": revenue,
        "expenses": expenses,
        "active_jobs": active_jobs,
    }


def next_invoice_number(session: Session) -> str:
    count = session.scalar(select(func.count(Invoice.id))) or 0
    return f"INV-{count + 1:04d}"


def next_quote_number(session: Session) -> str:
    count = session.scalar(select(func.count(Quote.id))) or 0
    return f"Q-{count + 1:04d}"


def get_company_settings(session: Session) -> CompanySettings:
    settings = session.get(CompanySettings, 1)
    if settings is None:
        settings = CompanySettings(id=1, company_name="OpenBooks")
        session.add(settings)
        session.flush()
    return settings
