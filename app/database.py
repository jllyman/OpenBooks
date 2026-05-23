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
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="customer")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    jobs: Mapped[list["Job"]] = relationship(back_populates="department")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="department")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="department")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="department")
    job_fields: Mapped[list["JobDetailField"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
        order_by="JobDetailField.sort_order",
    )


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(160), default="OpenBooks")
    logo_filename: Mapped[str | None] = mapped_column(String(240))
    ein: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    website: Mapped[str | None] = mapped_column(String(160))
    address_line_1: Mapped[str | None] = mapped_column(String(160))
    address_line_2: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(40))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    theme_background: Mapped[str | None] = mapped_column(String(20), default="#f7f8fa")
    theme_paper: Mapped[str | None] = mapped_column(String(20), default="#ffffff")
    theme_ink: Mapped[str | None] = mapped_column(String(20), default="#1f2933")
    theme_muted: Mapped[str | None] = mapped_column(String(20), default="#64748b")
    theme_line: Mapped[str | None] = mapped_column(String(20), default="#d9e0e8")
    theme_accent: Mapped[str | None] = mapped_column(String(20), default="#2563eb")
    theme_accent_2: Mapped[str | None] = mapped_column(String(20), default="#0f766e")
    theme_warn: Mapped[str | None] = mapped_column(String(20), default="#b45309")
    app_font: Mapped[str | None] = mapped_column(String(40), default="system")
    app_density: Mapped[str | None] = mapped_column(String(40), default="compact")
    app_nav_layout: Mapped[str | None] = mapped_column(String(40), default="top")
    app_content_width: Mapped[str | None] = mapped_column(String(40), default="full")
    app_corner_radius: Mapped[int | None] = mapped_column(default=6)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    role: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    address_line_1: Mapped[str | None] = mapped_column(String(160))
    address_line_2: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(40))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text)


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    company_name: Mapped[str | None] = mapped_column(String(160))
    specialty: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))
    address_line_1: Mapped[str | None] = mapped_column(String(160))
    address_line_2: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str | None] = mapped_column(String(40))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str | None] = mapped_column(Text)


class TicketType(Base):
    __tablename__ = "ticket_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    ticket_prefix: Mapped[str] = mapped_column(String(20), default="T-")
    description: Mapped[str | None] = mapped_column(Text)

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="ticket_type_record")
    fields: Mapped[list["TicketDetailField"]] = relationship(
        back_populates="ticket_type",
        cascade="all, delete-orphan",
        order_by="TicketDetailField.sort_order",
    )


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    account_type: Mapped[str] = mapped_column(String(40))
    detail_type: Mapped[str | None] = mapped_column(String(80))
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
    cash_transactions: Mapped[list["CashTransaction"]] = relationship(back_populates="account")


class CashTransaction(Base):
    __tablename__ = "cash_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_type: Mapped[str] = mapped_column(String(20))
    transaction_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    category: Mapped[str | None] = mapped_column(String(80))
    tax_category: Mapped[str | None] = mapped_column(String(120))
    contact_name: Mapped[str | None] = mapped_column(String(140))
    reference: Mapped[str | None] = mapped_column(String(80))
    method: Mapped[str | None] = mapped_column(String(60))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    account: Mapped[Account | None] = relationship(back_populates="cash_transactions")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(140))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="Planned")
    due_date: Mapped[date | None] = mapped_column(Date)
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    drawing_filename: Mapped[str | None] = mapped_column(String(240))
    drawing_original_filename: Mapped[str | None] = mapped_column(String(240))
    model_filename: Mapped[str | None] = mapped_column(String(240))
    model_original_filename: Mapped[str | None] = mapped_column(String(240))

    customer: Mapped[Customer] = relationship(back_populates="jobs")
    department: Mapped[Department | None] = relationship(back_populates="jobs")
    detail_values: Mapped[list["JobDetailValue"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    quotes: Mapped[list["Quote"]] = relationship(back_populates="job")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="job")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="job")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_number: Mapped[str] = mapped_column(String(40), unique=True)
    ticket_type: Mapped[str] = mapped_column(String(40), default="Automotive")
    status: Mapped[str] = mapped_column(String(40), default="Open")
    priority: Mapped[str] = mapped_column(String(40), default="Normal")
    subject: Mapped[str] = mapped_column(String(160))
    ticket_type_id: Mapped[int | None] = mapped_column(ForeignKey("ticket_types.id"))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    requested_by: Mapped[str | None] = mapped_column(String(140))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    assigned_to: Mapped[str | None] = mapped_column(String(120))
    opened_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    vehicle_year: Mapped[str | None] = mapped_column(String(20))
    vehicle_make: Mapped[str | None] = mapped_column(String(80))
    vehicle_model: Mapped[str | None] = mapped_column(String(80))
    vehicle_vin: Mapped[str | None] = mapped_column(String(40))
    vehicle_plate: Mapped[str | None] = mapped_column(String(40))
    vehicle_mileage: Mapped[str | None] = mapped_column(String(40))
    it_asset_tag: Mapped[str | None] = mapped_column(String(80))
    it_device_type: Mapped[str | None] = mapped_column(String(80))
    it_system: Mapped[str | None] = mapped_column(String(120))
    it_location: Mapped[str | None] = mapped_column(String(120))

    customer: Mapped[Customer | None] = relationship(back_populates="tickets")
    department: Mapped[Department | None] = relationship(back_populates="tickets")
    job: Mapped[Job | None] = relationship(back_populates="tickets")
    ticket_type_record: Mapped[TicketType | None] = relationship(back_populates="tickets")
    detail_values: Mapped[list["TicketDetailValue"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )


class TicketDetailField(Base):
    __tablename__ = "ticket_detail_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_type_id: Mapped[int] = mapped_column(ForeignKey("ticket_types.id"))
    label: Mapped[str] = mapped_column(String(120))
    field_type: Mapped[str] = mapped_column(String(40), default="text")
    sort_order: Mapped[int] = mapped_column(default=0)

    ticket_type: Mapped[TicketType] = relationship(back_populates="fields")
    values: Mapped[list["TicketDetailValue"]] = relationship(
        back_populates="field",
        cascade="all, delete-orphan",
    )


class TicketDetailValue(Base):
    __tablename__ = "ticket_detail_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    field_id: Mapped[int] = mapped_column(ForeignKey("ticket_detail_fields.id"))
    value: Mapped[str | None] = mapped_column(Text)

    ticket: Mapped[Ticket] = relationship(back_populates="detail_values")
    field: Mapped[TicketDetailField] = relationship(back_populates="values")


class JobDetailField(Base):
    __tablename__ = "job_detail_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    label: Mapped[str] = mapped_column(String(120))
    field_type: Mapped[str] = mapped_column(String(40), default="text")
    sort_order: Mapped[int] = mapped_column(default=0)

    department: Mapped[Department] = relationship(back_populates="job_fields")
    values: Mapped[list["JobDetailValue"]] = relationship(
        back_populates="field",
        cascade="all, delete-orphan",
    )


class JobDetailValue(Base):
    __tablename__ = "job_detail_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    field_id: Mapped[int] = mapped_column(ForeignKey("job_detail_fields.id"))
    value: Mapped[str | None] = mapped_column(Text)

    job: Mapped[Job] = relationship(back_populates="detail_values")
    field: Mapped[JobDetailField] = relationship(back_populates="values")


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
    tax_category: Mapped[str | None] = mapped_column(String(120))
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
    seed_default_accounts()
    seed_default_ticket_types()
    seed_default_job_fields()


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

        if "jobs" in table_names:
            job_columns = {column["name"] for column in inspector.get_columns("jobs")}
            if "department_id" not in job_columns:
                connection.execute(text("ALTER TABLE jobs ADD COLUMN department_id INTEGER"))

            job_file_columns = {
                "drawing_filename": "VARCHAR(240)",
                "drawing_original_filename": "VARCHAR(240)",
                "model_filename": "VARCHAR(240)",
                "model_original_filename": "VARCHAR(240)",
            }
            for column_name, column_type in job_file_columns.items():
                if column_name not in job_columns:
                    connection.execute(text(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}"))

        if "company_settings" in table_names:
            company_columns = {column["name"] for column in inspector.get_columns("company_settings")}
            if "ein" not in company_columns:
                connection.execute(text("ALTER TABLE company_settings ADD COLUMN ein VARCHAR(40)"))
            appearance_columns = {
                "theme_background": "VARCHAR(20)",
                "theme_paper": "VARCHAR(20)",
                "theme_ink": "VARCHAR(20)",
                "theme_muted": "VARCHAR(20)",
                "theme_line": "VARCHAR(20)",
                "theme_accent": "VARCHAR(20)",
                "theme_accent_2": "VARCHAR(20)",
                "theme_warn": "VARCHAR(20)",
                "app_font": "VARCHAR(40)",
                "app_density": "VARCHAR(40)",
                "app_nav_layout": "VARCHAR(40)",
                "app_content_width": "VARCHAR(40)",
                "app_corner_radius": "INTEGER",
            }
            for column_name, column_type in appearance_columns.items():
                if column_name not in company_columns:
                    connection.execute(text(f"ALTER TABLE company_settings ADD COLUMN {column_name} {column_type}"))

        if "bills" in table_names:
            bill_columns = {column["name"] for column in inspector.get_columns("bills")}
            if "tax_category" not in bill_columns:
                connection.execute(text("ALTER TABLE bills ADD COLUMN tax_category VARCHAR(120)"))

        if "cash_transactions" in table_names:
            transaction_columns = {column["name"] for column in inspector.get_columns("cash_transactions")}
            if "tax_category" not in transaction_columns:
                connection.execute(text("ALTER TABLE cash_transactions ADD COLUMN tax_category VARCHAR(120)"))

        if "tickets" in table_names:
            ticket_columns = {column["name"] for column in inspector.get_columns("tickets")}
            if "ticket_type_id" not in ticket_columns:
                connection.execute(text("ALTER TABLE tickets ADD COLUMN ticket_type_id INTEGER"))

        address_columns = {
            "address_line_1": "VARCHAR(160)",
            "address_line_2": "VARCHAR(160)",
            "city": "VARCHAR(80)",
            "state": "VARCHAR(40)",
            "postal_code": "VARCHAR(20)",
        }
        for table_name in ["employees", "contractors"]:
            if table_name in table_names:
                existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
                for column_name, column_type in address_columns.items():
                    if column_name not in existing_columns:
                        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def seed_default_accounts() -> None:
    if SessionLocal is None:
        return

    defaults = [
        ("Checking", "Asset", "Bank", "Primary operating cash account"),
        ("Accounts Receivable", "Asset", "Accounts Receivable", "Customer invoices not yet paid"),
        ("Inventory Asset", "Asset", "Inventory", "Material or product value on hand"),
        ("Accounts Payable", "Liability", "Accounts Payable", "Vendor bills not yet paid"),
        ("Sales Revenue", "Income", "Service/Product Income", "Revenue from invoices"),
        ("Job Materials", "Expense", "Cost of Goods Sold", "Materials and shop costs"),
        ("Rent and Utilities", "Expense", "Operating Expense", "Facilities and utilities"),
        ("Owner Equity", "Equity", "Owner Equity", "Owner investment and retained value"),
    ]

    with SessionLocal() as session:
        existing_names = {name for (name,) in session.query(Account.name).all()}
        for name, account_type, detail_type, description in defaults:
            if name not in existing_names:
                session.add(
                    Account(
                        name=name,
                        account_type=account_type,
                        detail_type=detail_type,
                        description=description,
                    )
                )
        session.commit()


def seed_default_ticket_types() -> None:
    if SessionLocal is None:
        return

    defaults = [
        ("Automotive", "AUTO-", "Vehicle service and repair work"),
        ("IT", "IT-", "Computer, network, and systems support"),
        ("General", "T-", "General service requests"),
    ]

    with SessionLocal() as session:
        existing_names = {name for (name,) in session.query(TicketType.name).all()}
        for name, prefix, description in defaults:
            if name not in existing_names:
                session.add(TicketType(name=name, ticket_prefix=prefix, description=description))
        session.flush()
        ticket_types_by_name = {ticket_type.name: ticket_type for ticket_type in session.query(TicketType).all()}
        for ticket in session.query(Ticket).filter(Ticket.ticket_type_id.is_(None)).all():
            ticket_type = ticket_types_by_name.get(ticket.ticket_type) or ticket_types_by_name.get("General")
            if ticket_type:
                ticket.ticket_type_id = ticket_type.id
                ticket.ticket_type = ticket_type.name
        session.commit()


def seed_default_job_fields() -> None:
    if SessionLocal is None:
        return

    with SessionLocal() as session:
        departments = session.query(Department).all()
        for department in departments:
            add_default_job_fields(department)
        session.commit()


def add_default_job_fields(department: Department) -> None:
    defaults = {
        "3d": [
            ("Material", "text"),
            ("Filament color", "text"),
            ("Nozzle size", "text"),
            ("Layer height", "text"),
            ("Infill", "text"),
            ("Supports", "checkbox"),
            ("Print temperature", "text"),
            ("Bed temperature", "text"),
            ("Estimated print time", "text"),
        ],
        "fabrication": [
            ("Material", "text"),
            ("Material thickness", "text"),
            ("Cut length", "text"),
            ("Weld process", "text"),
            ("Finish", "text"),
            ("Hardware", "long_text"),
            ("Inspection notes", "long_text"),
        ],
    }

    name = department.name.lower()
    fields = defaults.get("3d") if "3d" in name or "print" in name else None
    if fields is None and "fabrication" in name:
        fields = defaults["fabrication"]
    if not fields or department.job_fields:
        return

    for sort_order, (label, field_type) in enumerate(fields, start=1):
        department.job_fields.append(
            JobDetailField(label=label, field_type=field_type, sort_order=sort_order)
        )


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
    cash_transactions = session.scalars(select(CashTransaction)).all()
    jobs = session.scalars(select(Job)).all()
    tickets = session.scalars(select(Ticket)).all()

    ar_open = Decimal("0.00")
    for invoice in invoices:
        ar_open += max(invoice_total(invoice) - invoice_paid(invoice), Decimal("0.00"))

    ap_open = Decimal("0.00")
    for bill in bills:
        ap_open += max(money(bill.amount) - bill_paid(bill), Decimal("0.00"))

    revenue = sum((invoice_total(invoice) for invoice in invoices), Decimal("0.00"))
    revenue += sum(
        (money(transaction.amount) for transaction in cash_transactions if transaction.transaction_type == "Income"),
        Decimal("0.00"),
    )
    expenses = sum((money(bill.amount) for bill in bills), Decimal("0.00"))
    expenses += sum(
        (money(transaction.amount) for transaction in cash_transactions if transaction.transaction_type == "Expense"),
        Decimal("0.00"),
    )
    active_jobs = sum(1 for job in jobs if job.status not in {"Done", "Cancelled"})
    open_tickets = sum(1 for ticket in tickets if ticket.status not in {"Resolved", "Closed", "Cancelled"})

    return {
        "ar_open": ar_open,
        "ap_open": ap_open,
        "revenue": revenue,
        "expenses": expenses,
        "active_jobs": active_jobs,
        "open_tickets": open_tickets,
    }


def next_invoice_number(session: Session) -> str:
    count = session.scalar(select(func.count(Invoice.id))) or 0
    return f"INV-{count + 1:04d}"


def next_quote_number(session: Session) -> str:
    count = session.scalar(select(func.count(Quote.id))) or 0
    return f"Q-{count + 1:04d}"


def next_ticket_number(session: Session, ticket_type: TicketType | None = None) -> str:
    prefix = ticket_type.ticket_prefix if ticket_type else "T-"
    count = session.scalar(select(func.count(Ticket.id)).where(Ticket.ticket_number.like(f"{prefix}%"))) or 0
    return f"{prefix}{count + 1:04d}"


def get_company_settings(session: Session) -> CompanySettings:
    settings = session.get(CompanySettings, 1)
    if settings is None:
        settings = CompanySettings(id=1, company_name="OpenBooks")
        session.add(settings)
        session.flush()
    return settings
