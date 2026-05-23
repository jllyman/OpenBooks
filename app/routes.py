from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from flask import current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from .database import (
    Account,
    AppUser,
    Bill,
    CashTransaction,
    CompanySettings,
    Contractor,
    Customer,
    Department,
    Employee,
    Invoice,
    InvoiceLineItem,
    Job,
    JobDetailField,
    JobDetailValue,
    Payment,
    Quote,
    QuoteLineItem,
    Ticket,
    TicketDetailField,
    TicketDetailValue,
    TicketType,
    WorkImage,
    add_default_job_fields,
    bill_paid,
    dashboard_snapshot,
    get_company_settings,
    get_session,
    invoice_paid,
    invoice_total,
    money,
    next_invoice_number,
    next_quote_number,
    next_ticket_number,
    quote_total,
)


ALLOWED_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
ALLOWED_JOB_FILE_EXTENSIONS = {
    ".3dm",
    ".3mf",
    ".ai",
    ".dwg",
    ".dxf",
    ".fcstd",
    ".f3d",
    ".iges",
    ".igs",
    ".jpeg",
    ".jpg",
    ".obj",
    ".pdf",
    ".png",
    ".sldasm",
    ".sldprt",
    ".skp",
    ".step",
    ".stl",
    ".stp",
    ".svg",
    ".webp",
}
DEFAULT_APPEARANCE = {
    "theme_background": "#f7f8fa",
    "theme_paper": "#ffffff",
    "theme_ink": "#1f2933",
    "theme_muted": "#64748b",
    "theme_line": "#d9e0e8",
    "theme_accent": "#2563eb",
    "theme_accent_2": "#0f766e",
    "theme_warn": "#b45309",
    "app_font": "system",
    "app_density": "compact",
    "app_nav_layout": "top",
    "app_content_width": "full",
    "app_corner_radius": 6,
}
FONT_OPTIONS = {"serif", "sans", "system"}
DENSITY_OPTIONS = {"comfortable", "compact", "spacious"}
NAV_LAYOUT_OPTIONS = {"top", "sidebar"}
CONTENT_WIDTH_OPTIONS = {"full", "contained", "wide"}
TAX_CATEGORIES = [
    ("advertising", "Advertising"),
    ("car_truck", "Car and truck expenses"),
    ("commissions_fees", "Commissions and fees"),
    ("contract_labor", "Contract labor"),
    ("depletion", "Depletion"),
    ("depreciation_section_179", "Depreciation and section 179"),
    ("employee_benefits", "Employee benefit programs"),
    ("insurance", "Insurance, other than health"),
    ("interest_mortgage", "Interest, mortgage"),
    ("interest_other", "Interest, other"),
    ("legal_professional", "Legal and professional services"),
    ("office", "Office expense"),
    ("pension_profit_sharing", "Pension and profit-sharing plans"),
    ("rent_vehicles_equipment", "Rent or lease, vehicles/equipment"),
    ("rent_other", "Rent or lease, other business property"),
    ("repairs_maintenance", "Repairs and maintenance"),
    ("supplies", "Supplies"),
    ("taxes_licenses", "Taxes and licenses"),
    ("travel", "Travel"),
    ("deductible_meals", "Deductible meals"),
    ("utilities", "Utilities"),
    ("wages", "Wages"),
    ("energy_buildings", "Energy efficient commercial buildings deduction"),
    ("other_expenses", "Other expenses"),
    ("business_use_home", "Business use of home"),
    ("cost_of_goods_sold", "Cost of goods sold / materials"),
    ("uncategorized", "Uncategorized"),
]
TAX_CATEGORY_LABELS = dict(TAX_CATEGORIES)
TICKET_STATUSES = ["Open", "Scheduled", "In Progress", "Waiting", "Resolved", "Closed", "Cancelled"]
TICKET_PRIORITIES = ["Low", "Normal", "High", "Urgent"]
FIELD_TYPES = ["text", "number", "date", "checkbox", "long_text"]
PUBLIC_ENDPOINTS = {"login", "login_post", "setup_admin", "create_admin_user", "static"}


def parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def users_exist() -> bool:
    with get_session() as db_session:
        return (db_session.query(AppUser.id).limit(1).first()) is not None


def safe_next_url(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("dashboard")


def clean_color(value: str | None, fallback: str) -> str:
    value = (value or "").strip()
    if len(value) == 7 and value.startswith("#") and all(character in "0123456789abcdefABCDEF" for character in value[1:]):
        return value
    return fallback


def clean_choice(value: str | None, allowed_values: set[str], fallback: str) -> str:
    value = (value or "").strip()
    return value if value in allowed_values else fallback


def clean_radius(value: str | None) -> int:
    try:
        radius = int(value or DEFAULT_APPEARANCE["app_corner_radius"])
    except ValueError:
        radius = int(DEFAULT_APPEARANCE["app_corner_radius"])
    return max(4, min(radius, 32))


def appearance_settings(settings: CompanySettings | None) -> dict[str, str | int]:
    appearance = DEFAULT_APPEARANCE.copy()
    if settings is None:
        return appearance

    for key, fallback in DEFAULT_APPEARANCE.items():
        appearance[key] = getattr(settings, key, None) or fallback
    return appearance


def open_invoice_amount(invoice: Invoice) -> Decimal:
    return max(invoice_total(invoice) - invoice_paid(invoice), Decimal("0.00"))


def open_bill_amount(bill: Bill) -> Decimal:
    return max(money(bill.amount) - bill_paid(bill), Decimal("0.00"))


def transaction_total(transactions: list[CashTransaction], transaction_type: str) -> Decimal:
    return sum(
        (money(transaction.amount) for transaction in transactions if transaction.transaction_type == transaction_type),
        Decimal("0.00"),
    )


def clean_tax_category(value: str | None) -> str:
    value = (value or "").strip()
    return value if value in TAX_CATEGORY_LABELS else "uncategorized"


def clean_ticket_choice(value: str | None, choices: list[str], fallback: str) -> str:
    value = (value or "").strip()
    return value if value in choices else fallback


def optional_int(value: str | None) -> int | None:
    return int(value) if value else None


def apply_ticket_form(session, ticket: Ticket) -> TicketType | None:
    ticket_type_id = optional_int(request.form.get("ticket_type_id"))
    ticket_type = session.get(TicketType, ticket_type_id) if ticket_type_id else None
    ticket.ticket_type_id = ticket_type_id
    ticket.ticket_type = ticket_type.name if ticket_type else "General"
    ticket.status = clean_ticket_choice(request.form.get("status"), TICKET_STATUSES, "Open")
    ticket.priority = clean_ticket_choice(request.form.get("priority"), TICKET_PRIORITIES, "Normal")
    ticket.subject = request.form["subject"].strip()
    ticket.customer_id = optional_int(request.form.get("customer_id"))
    ticket.department_id = optional_int(request.form.get("department_id"))
    ticket.job_id = optional_int(request.form.get("job_id"))
    ticket.requested_by = request.form.get("requested_by", "").strip() or None
    ticket.contact_phone = request.form.get("contact_phone", "").strip() or None
    ticket.assigned_to = request.form.get("assigned_to", "").strip() or None
    ticket.opened_date = parse_date(request.form.get("opened_date", "")) or date.today()
    ticket.due_date = parse_date(request.form.get("due_date", ""))
    ticket.completed_date = parse_date(request.form.get("completed_date", ""))
    ticket.description = request.form.get("description", "").strip() or None
    ticket.resolution = request.form.get("resolution", "").strip() or None
    ticket.vehicle_year = request.form.get("vehicle_year", "").strip() or None
    ticket.vehicle_make = request.form.get("vehicle_make", "").strip() or None
    ticket.vehicle_model = request.form.get("vehicle_model", "").strip() or None
    ticket.vehicle_vin = request.form.get("vehicle_vin", "").strip() or None
    ticket.vehicle_plate = request.form.get("vehicle_plate", "").strip() or None
    ticket.vehicle_mileage = request.form.get("vehicle_mileage", "").strip() or None
    ticket.it_asset_tag = request.form.get("it_asset_tag", "").strip() or None
    ticket.it_device_type = request.form.get("it_device_type", "").strip() or None
    ticket.it_system = request.form.get("it_system", "").strip() or None
    ticket.it_location = request.form.get("it_location", "").strip() or None
    return ticket_type


def ticket_detail_value_map(ticket: Ticket) -> dict[int, TicketDetailValue]:
    return {detail_value.field_id: detail_value for detail_value in ticket.detail_values}


def save_ticket_detail_values(ticket: Ticket, fields: list[TicketDetailField]) -> None:
    values_by_field_id = ticket_detail_value_map(ticket)
    for field in fields:
        form_key = f"ticket_field_{field.id}"
        value = "Yes" if field.field_type == "checkbox" and request.form.get(form_key) else request.form.get(form_key, "")
        value = value.strip() if value else None

        detail_value = values_by_field_id.get(field.id)
        if detail_value is None:
            detail_value = TicketDetailValue(field_id=field.id)
            ticket.detail_values.append(detail_value)
        detail_value.value = value


def tax_year_options() -> list[int]:
    current_year = date.today().year
    return list(range(current_year, current_year - 7, -1))


def build_tax_report_context(session, year: int) -> dict:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    invoices = session.query(Invoice).filter(Invoice.issue_date >= start, Invoice.issue_date <= end).order_by(Invoice.issue_date.asc()).all()
    income_transactions = session.query(CashTransaction).filter(
        CashTransaction.transaction_type == "Income",
        CashTransaction.transaction_date >= start,
        CashTransaction.transaction_date <= end,
    ).order_by(CashTransaction.transaction_date.asc()).all()
    bills = session.query(Bill).filter(Bill.due_date >= start, Bill.due_date <= end).order_by(Bill.due_date.asc()).all()
    transactions = session.query(CashTransaction).filter(
        CashTransaction.transaction_type == "Expense",
        CashTransaction.transaction_date >= start,
        CashTransaction.transaction_date <= end,
    ).order_by(CashTransaction.transaction_date.asc()).all()

    category_totals = {key: Decimal("0.00") for key, _label in TAX_CATEGORIES}
    income_rows = []
    invoice_income = Decimal("0.00")
    direct_income = Decimal("0.00")
    for invoice in invoices:
        amount = invoice_total(invoice)
        invoice_income += amount
        income_rows.append(
            {
                "date": invoice.issue_date,
                "source": "Invoice",
                "name": invoice.customer.name,
                "reference": invoice.invoice_number,
                "category": "Invoice revenue",
                "amount": amount,
            }
        )

    for transaction in income_transactions:
        amount = money(transaction.amount)
        direct_income += amount
        income_rows.append(
            {
                "date": transaction.transaction_date,
                "source": "Direct income",
                "name": transaction.contact_name or "-",
                "reference": transaction.reference,
                "category": transaction.category or "Direct income",
                "amount": amount,
            }
        )

    rows = []
    for bill in bills:
        category = clean_tax_category(bill.tax_category or "uncategorized")
        amount = money(bill.amount)
        category_totals[category] += amount
        rows.append(
            {
                "date": bill.due_date,
                "source": "Bill",
                "name": bill.vendor_name,
                "reference": bill.reference,
                "category": category,
                "amount": amount,
            }
        )

    for transaction in transactions:
        category = clean_tax_category(transaction.tax_category or "uncategorized")
        amount = money(transaction.amount)
        category_totals[category] += amount
        rows.append(
            {
                "date": transaction.transaction_date,
                "source": "Direct expense",
                "name": transaction.contact_name or "-",
                "reference": transaction.reference,
                "category": category,
                "amount": amount,
            }
        )

    income_rows.sort(key=lambda row: row["date"])
    rows.sort(key=lambda row: row["date"])
    total_income = invoice_income + direct_income
    total_expenses = sum(category_totals.values(), Decimal("0.00"))
    return {
        "year": year,
        "year_options": tax_year_options(),
        "tax_categories": TAX_CATEGORIES,
        "tax_category_labels": TAX_CATEGORY_LABELS,
        "income_rows": income_rows,
        "invoice_income": invoice_income,
        "direct_income": direct_income,
        "total_income": total_income,
        "category_totals": category_totals,
        "expense_rows": rows,
        "expense_total": total_expenses,
        "net_profit": total_income - total_expenses,
    }


def build_reports_context(session):
    invoices = session.query(Invoice).order_by(Invoice.issue_date.desc()).all()
    bills = session.query(Bill).order_by(Bill.due_date.asc()).all()
    cash_transactions = session.query(CashTransaction).order_by(CashTransaction.transaction_date.desc()).all()
    jobs = session.query(Job).order_by(Job.name.asc()).all()
    accounts = session.query(Account).order_by(Account.account_type.asc(), Account.name.asc()).all()

    invoice_revenue = sum((invoice_total(invoice) for invoice in invoices), Decimal("0.00"))
    direct_income = transaction_total(cash_transactions, "Income")
    bill_expenses = sum((money(bill.amount) for bill in bills), Decimal("0.00"))
    direct_expenses = transaction_total(cash_transactions, "Expense")
    revenue = invoice_revenue + direct_income
    expenses = bill_expenses + direct_expenses
    gross_profit = revenue - expenses
    ar_open = sum((open_invoice_amount(invoice) for invoice in invoices), Decimal("0.00"))
    ap_open = sum((open_bill_amount(bill) for bill in bills), Decimal("0.00"))
    estimated_pipeline = sum(
        (money(job.estimated_amount) for job in jobs if job.status not in {"Done", "Cancelled"}),
        Decimal("0.00"),
    )

    return {
        "report": {
            "revenue": revenue,
            "invoice_revenue": invoice_revenue,
            "direct_income": direct_income,
            "expenses": expenses,
            "bill_expenses": bill_expenses,
            "direct_expenses": direct_expenses,
            "gross_profit": gross_profit,
            "ar_open": ar_open,
            "ap_open": ap_open,
            "estimated_pipeline": estimated_pipeline,
        },
        "invoices": invoices,
        "bills": bills,
        "cash_transactions": cash_transactions,
        "accounts": accounts,
        "invoice_total": invoice_total,
        "open_invoice_amount": open_invoice_amount,
        "open_bill_amount": open_bill_amount,
    }


def save_work_images(files: list[FileStorage]) -> list[WorkImage]:
    upload_dir = Path(current_app.static_folder) / "uploads" / "work_images"
    upload_dir.mkdir(parents=True, exist_ok=True)

    images = []
    for uploaded_file in files:
        if not uploaded_file or not uploaded_file.filename:
            continue

        original_filename = secure_filename(uploaded_file.filename)
        extension = Path(original_filename).suffix.lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            continue

        filename = f"{uuid4().hex}{extension}"
        uploaded_file.save(upload_dir / filename)
        images.append(
            WorkImage(
                filename=f"uploads/work_images/{filename}",
                original_filename=original_filename,
            )
        )

    return images


def save_logo(uploaded_file: FileStorage | None) -> str | None:
    if not uploaded_file or not uploaded_file.filename:
        return None

    original_filename = secure_filename(uploaded_file.filename)
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    upload_dir = Path(current_app.static_folder) / "uploads" / "company"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"logo-{uuid4().hex}{extension}"
    uploaded_file.save(upload_dir / filename)
    return f"uploads/company/{filename}"


def save_job_file(uploaded_file: FileStorage | None, file_type: str) -> tuple[str, str] | None:
    if not uploaded_file or not uploaded_file.filename:
        return None

    original_filename = secure_filename(uploaded_file.filename)
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_JOB_FILE_EXTENSIONS:
        return None

    upload_dir = Path(current_app.static_folder) / "uploads" / "job_files"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{file_type}-{uuid4().hex}{extension}"
    uploaded_file.save(upload_dir / filename)
    return f"uploads/job_files/{filename}", original_filename


def delete_static_file(filename: str | None) -> None:
    if not filename:
        return

    static_root = Path(current_app.static_folder).resolve()
    file_path = (static_root / filename).resolve()
    if static_root in file_path.parents and file_path.exists():
        file_path.unlink()


def field_value_map(job: Job) -> dict[int, JobDetailValue]:
    return {detail_value.field_id: detail_value for detail_value in job.detail_values}


def save_job_detail_values(job: Job, fields: list[JobDetailField]) -> None:
    values_by_field_id = field_value_map(job)
    for field in fields:
        form_key = f"field_{field.id}"
        value = "Yes" if field.field_type == "checkbox" and request.form.get(form_key) else request.form.get(form_key, "")
        value = value.strip() if value else None

        detail_value = values_by_field_id.get(field.id)
        if detail_value is None:
            detail_value = JobDetailValue(field_id=field.id)
            job.detail_values.append(detail_value)
        detail_value.value = value


def contractor_ids_from_form() -> list[int]:
    contractor_ids = []
    for value in request.form.getlist("contractor_ids"):
        if value:
            contractor_ids.append(int(value))
    return contractor_ids


def assign_job_contractors(session, job: Job) -> None:
    contractor_ids = contractor_ids_from_form()
    job.contractors = (
        session.query(Contractor)
        .filter(Contractor.id.in_(contractor_ids))
        .order_by(Contractor.name.asc())
        .all()
        if contractor_ids
        else []
    )


def register_routes(app):
    @app.before_request
    def require_login():
        endpoint = request.endpoint or ""
        if endpoint in PUBLIC_ENDPOINTS or endpoint.startswith("static"):
            return None

        has_users = users_exist()
        if not has_users:
            return redirect(url_for("setup_admin"))

        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("login", next=request.full_path if request.query_string else request.path))

        with get_session() as db_session:
            user = db_session.get(AppUser, user_id)
            if user is None or not user.is_active:
                session.clear()
                return redirect(url_for("login"))
            g.current_user = {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name or user.username,
            }

        return None

    @app.template_filter("currency")
    def currency_filter(value):
        return f"${float(value or 0):,.2f}"

    @app.context_processor
    def inject_company_settings():
        with get_session() as session:
            settings = session.get(CompanySettings, 1)
            company_name = settings.company_name if settings else "OpenBooks"
            logo_filename = settings.logo_filename if settings else None
            return {
                "company_settings": {
                    "company_name": company_name,
                    "logo_filename": logo_filename,
                },
                "appearance": appearance_settings(settings),
                "current_user": getattr(g, "current_user", None),
            }

    @app.get("/setup")
    def setup_admin():
        if users_exist():
            return redirect(url_for("login"))
        return render_template("setup.html")

    @app.post("/setup")
    def create_admin_user():
        if users_exist():
            return redirect(url_for("login"))

        username = request.form["username"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        display_name = request.form.get("display_name", "").strip() or None

        if len(username) < 3:
            flash("Username must be at least 3 characters.")
            return redirect(url_for("setup_admin"))
        if len(password) < 10:
            flash("Password must be at least 10 characters.")
            return redirect(url_for("setup_admin"))
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("setup_admin"))

        with get_session() as db_session:
            db_session.add(
                AppUser(
                    username=username,
                    display_name=display_name,
                    password_hash=generate_password_hash(password),
                )
            )

        flash("Admin user created. Sign in to continue.")
        return redirect(url_for("login"))

    @app.get("/login")
    def login():
        if not users_exist():
            return redirect(url_for("setup_admin"))
        return render_template("login.html", next_url=safe_next_url(request.args.get("next")))

    @app.post("/login")
    def login_post():
        if not users_exist():
            return redirect(url_for("setup_admin"))

        username = request.form["username"].strip()
        password = request.form["password"]
        next_url = safe_next_url(request.form.get("next"))

        with get_session() as db_session:
            user = db_session.query(AppUser).filter(AppUser.username == username).first()
            if user is None or not user.is_active or not check_password_hash(user.password_hash, password):
                flash("Invalid username or password.")
                return redirect(url_for("login", next=next_url))

            session.clear()
            session["user_id"] = user.id

        return redirect(next_url)

    @app.post("/logout")
    def logout():
        session.clear()
        flash("Signed out.")
        return redirect(url_for("login"))

    @app.get("/")
    def dashboard():
        with get_session() as session:
            snapshot = dashboard_snapshot(session)
            recent_invoices = session.query(Invoice).order_by(Invoice.issue_date.desc()).limit(5).all()
            recent_bills = session.query(Bill).order_by(Bill.due_date.asc()).limit(5).all()
            jobs = session.query(Job).order_by(Job.due_date.asc()).limit(5).all()
            tickets = session.query(Ticket).order_by(Ticket.due_date.asc(), Ticket.opened_date.desc()).limit(5).all()
            return render_template(
                "dashboard.html",
                snapshot=snapshot,
                recent_invoices=recent_invoices,
                recent_bills=recent_bills,
                jobs=jobs,
                tickets=tickets,
                invoice_total=invoice_total,
                invoice_paid=invoice_paid,
                bill_paid=bill_paid,
            )

    @app.get("/settings")
    @app.get("/settings/<section>")
    def settings(section: str = "menu"):
        valid_sections = {"menu", "company", "employees", "contractors", "departments", "tickets", "appearance"}
        if section not in valid_sections:
            return redirect(url_for("settings"))

        with get_session() as session:
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            employees = session.query(Employee).order_by(Employee.name.asc()).all()
            contractors = session.query(Contractor).order_by(Contractor.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            ticket_types = session.query(TicketType).order_by(TicketType.name.asc()).all()
            return render_template(
                "settings.html",
                company=company,
                employees=employees,
                contractors=contractors,
                departments=departments,
                ticket_types=ticket_types,
                field_types=FIELD_TYPES,
                active_section=section,
            )

    @app.post("/settings/company")
    def update_company_settings():
        with get_session() as session:
            company = get_company_settings(session)
            company.company_name = request.form.get("company_name", "").strip() or "OpenBooks"
            company.ein = request.form.get("ein", "").strip() or None
            company.email = request.form.get("email", "").strip() or None
            company.phone = request.form.get("phone", "").strip() or None
            company.website = request.form.get("website", "").strip() or None
            company.address_line_1 = request.form.get("address_line_1", "").strip() or None
            company.address_line_2 = request.form.get("address_line_2", "").strip() or None
            company.city = request.form.get("city", "").strip() or None
            company.state = request.form.get("state", "").strip() or None
            company.postal_code = request.form.get("postal_code", "").strip() or None
            company.notes = request.form.get("notes", "").strip() or None

            logo_filename = save_logo(request.files.get("logo"))
            if logo_filename:
                company.logo_filename = logo_filename

        flash("Company settings updated.")
        return redirect(url_for("settings", section="company"))

    @app.post("/settings/appearance")
    def update_appearance_settings():
        with get_session() as session:
            company = get_company_settings(session)
            for field in [
                "theme_background",
                "theme_paper",
                "theme_ink",
                "theme_muted",
                "theme_line",
                "theme_accent",
                "theme_accent_2",
                "theme_warn",
            ]:
                setattr(company, field, clean_color(request.form.get(field), str(DEFAULT_APPEARANCE[field])))

            company.app_font = clean_choice(request.form.get("app_font"), FONT_OPTIONS, str(DEFAULT_APPEARANCE["app_font"]))
            company.app_density = clean_choice(
                request.form.get("app_density"),
                DENSITY_OPTIONS,
                str(DEFAULT_APPEARANCE["app_density"]),
            )
            company.app_nav_layout = clean_choice(
                request.form.get("app_nav_layout"),
                NAV_LAYOUT_OPTIONS,
                str(DEFAULT_APPEARANCE["app_nav_layout"]),
            )
            company.app_content_width = clean_choice(
                request.form.get("app_content_width"),
                CONTENT_WIDTH_OPTIONS,
                str(DEFAULT_APPEARANCE["app_content_width"]),
            )
            company.app_corner_radius = clean_radius(request.form.get("app_corner_radius"))

        flash("Appearance settings updated.")
        return redirect(url_for("settings", section="appearance"))

    @app.post("/employees")
    def create_employee():
        with get_session() as session:
            session.add(
                Employee(
                    name=request.form["name"].strip(),
                    role=request.form.get("role", "").strip() or None,
                    email=request.form.get("email", "").strip() or None,
                    phone=request.form.get("phone", "").strip() or None,
                    address_line_1=request.form.get("address_line_1", "").strip() or None,
                    address_line_2=request.form.get("address_line_2", "").strip() or None,
                    city=request.form.get("city", "").strip() or None,
                    state=request.form.get("state", "").strip() or None,
                    postal_code=request.form.get("postal_code", "").strip() or None,
                    is_active=bool(request.form.get("is_active")),
                    notes=request.form.get("notes", "").strip() or None,
                )
            )
        flash("Employee added.")
        return redirect(url_for("settings", section="employees"))

    @app.post("/employees/<int:employee_id>")
    def update_employee(employee_id: int):
        with get_session() as session:
            employee = session.get(Employee, employee_id)
            if employee is None:
                flash("Employee not found.")
                return redirect(url_for("settings", section="employees"))

            employee.name = request.form["name"].strip()
            employee.role = request.form.get("role", "").strip() or None
            employee.email = request.form.get("email", "").strip() or None
            employee.phone = request.form.get("phone", "").strip() or None
            employee.address_line_1 = request.form.get("address_line_1", "").strip() or None
            employee.address_line_2 = request.form.get("address_line_2", "").strip() or None
            employee.city = request.form.get("city", "").strip() or None
            employee.state = request.form.get("state", "").strip() or None
            employee.postal_code = request.form.get("postal_code", "").strip() or None
            employee.is_active = bool(request.form.get("is_active"))
            employee.notes = request.form.get("notes", "").strip() or None

        flash("Employee updated.")
        return redirect(url_for("settings", section="employees"))

    @app.post("/contractors")
    def create_contractor():
        with get_session() as session:
            session.add(
                Contractor(
                    name=request.form["name"].strip(),
                    company_name=request.form.get("company_name", "").strip() or None,
                    specialty=request.form.get("specialty", "").strip() or None,
                    email=request.form.get("email", "").strip() or None,
                    phone=request.form.get("phone", "").strip() or None,
                    address_line_1=request.form.get("address_line_1", "").strip() or None,
                    address_line_2=request.form.get("address_line_2", "").strip() or None,
                    city=request.form.get("city", "").strip() or None,
                    state=request.form.get("state", "").strip() or None,
                    postal_code=request.form.get("postal_code", "").strip() or None,
                    is_active=bool(request.form.get("is_active")),
                    notes=request.form.get("notes", "").strip() or None,
                )
            )
        flash("Contractor added.")
        return redirect(url_for("settings", section="contractors"))

    @app.post("/contractors/<int:contractor_id>")
    def update_contractor(contractor_id: int):
        with get_session() as session:
            contractor = session.get(Contractor, contractor_id)
            if contractor is None:
                flash("Contractor not found.")
                return redirect(url_for("settings", section="contractors"))

            contractor.name = request.form["name"].strip()
            contractor.company_name = request.form.get("company_name", "").strip() or None
            contractor.specialty = request.form.get("specialty", "").strip() or None
            contractor.email = request.form.get("email", "").strip() or None
            contractor.phone = request.form.get("phone", "").strip() or None
            contractor.address_line_1 = request.form.get("address_line_1", "").strip() or None
            contractor.address_line_2 = request.form.get("address_line_2", "").strip() or None
            contractor.city = request.form.get("city", "").strip() or None
            contractor.state = request.form.get("state", "").strip() or None
            contractor.postal_code = request.form.get("postal_code", "").strip() or None
            contractor.is_active = bool(request.form.get("is_active"))
            contractor.notes = request.form.get("notes", "").strip() or None

        flash("Contractor updated.")
        return redirect(url_for("settings", section="contractors"))

    @app.get("/departments")
    def departments():
        return redirect(url_for("settings", section="departments"))

    @app.post("/departments")
    def create_department():
        with get_session() as session:
            department = Department(
                name=request.form["name"].strip(),
                description=request.form.get("description", "").strip() or None,
            )
            add_default_job_fields(department)
            session.add(department)
        flash("Department created.")
        return redirect(url_for("settings", section="departments"))

    @app.post("/departments/<int:department_id>/job-fields")
    def create_job_detail_field(department_id: int):
        with get_session() as session:
            department = session.get(Department, department_id)
            if department is None:
                flash("Department not found.")
                return redirect(url_for("settings", section="departments"))

            label = request.form["label"].strip()
            if not label:
                flash("Field label is required.")
                return redirect(url_for("settings", section="departments"))

            next_sort_order = max((field.sort_order for field in department.job_fields), default=0) + 1
            department.job_fields.append(
                JobDetailField(
                    label=label,
                    field_type=request.form.get("field_type", "text"),
                    sort_order=next_sort_order,
                )
            )

        flash("Job detail field added.")
        return redirect(url_for("settings", section="departments"))

    @app.post("/ticket-types")
    def create_ticket_type():
        with get_session() as session:
            session.add(
                TicketType(
                    name=request.form["name"].strip(),
                    ticket_prefix=request.form.get("ticket_prefix", "").strip() or "T-",
                    description=request.form.get("description", "").strip() or None,
                )
            )
        flash("Ticket type created.")
        return redirect(url_for("settings", section="tickets"))

    @app.post("/ticket-types/<int:ticket_type_id>")
    def update_ticket_type(ticket_type_id: int):
        with get_session() as session:
            ticket_type = session.get(TicketType, ticket_type_id)
            if ticket_type is None:
                flash("Ticket type not found.")
                return redirect(url_for("settings", section="tickets"))

            ticket_type.name = request.form["name"].strip()
            ticket_type.ticket_prefix = request.form.get("ticket_prefix", "").strip() or "T-"
            ticket_type.description = request.form.get("description", "").strip() or None

        flash("Ticket type updated.")
        return redirect(url_for("settings", section="tickets"))

    @app.post("/ticket-types/<int:ticket_type_id>/fields")
    def create_ticket_detail_field(ticket_type_id: int):
        with get_session() as session:
            ticket_type = session.get(TicketType, ticket_type_id)
            if ticket_type is None:
                flash("Ticket type not found.")
                return redirect(url_for("settings", section="tickets"))

            label = request.form["label"].strip()
            if not label:
                flash("Field label is required.")
                return redirect(url_for("settings", section="tickets"))

            field_type = request.form.get("field_type", "text")
            if field_type not in FIELD_TYPES:
                field_type = "text"

            next_sort_order = max((field.sort_order for field in ticket_type.fields), default=0) + 1
            ticket_type.fields.append(
                TicketDetailField(
                    label=label,
                    field_type=field_type,
                    sort_order=next_sort_order,
                )
            )

        flash("Ticket field added.")
        return redirect(url_for("settings", section="tickets"))

    @app.get("/accounting")
    def accounting():
        with get_session() as session:
            accounts = session.query(Account).order_by(Account.account_type.asc(), Account.name.asc()).all()
            return render_template("accounting.html", accounts=accounts)

    @app.get("/finance")
    def finance():
        with get_session() as session:
            transactions = session.query(CashTransaction).order_by(
                CashTransaction.transaction_date.desc(),
                CashTransaction.id.desc(),
            ).all()
            accounts = session.query(Account).filter(Account.is_active == True).order_by(Account.name.asc()).all()
            income_total = transaction_total(transactions, "Income")
            expense_total = transaction_total(transactions, "Expense")
            return render_template(
                "finance.html",
                transactions=transactions,
                accounts=accounts,
                income_total=income_total,
                expense_total=expense_total,
                tax_categories=TAX_CATEGORIES,
                tax_category_labels=TAX_CATEGORY_LABELS,
            )

    @app.post("/finance/transactions")
    def create_cash_transaction():
        transaction_type = request.form.get("transaction_type", "Expense")
        if transaction_type not in {"Income", "Expense"}:
            transaction_type = "Expense"

        with get_session() as session:
            session.add(
                CashTransaction(
                    transaction_type=transaction_type,
                    transaction_date=parse_date(request.form["transaction_date"]),
                    amount=money(request.form["amount"]),
                    category=request.form.get("category", "").strip() or None,
                    tax_category=clean_tax_category(request.form.get("tax_category")),
                    contact_name=request.form.get("contact_name", "").strip() or None,
                    reference=request.form.get("reference", "").strip() or None,
                    method=request.form.get("method", "").strip() or None,
                    account_id=int(request.form["account_id"]) if request.form.get("account_id") else None,
                    notes=request.form.get("notes", "").strip() or None,
                )
            )

        flash(f"{transaction_type} recorded.")
        return redirect(url_for("finance"))

    @app.post("/accounting/accounts")
    def create_account():
        with get_session() as session:
            session.add(
                Account(
                    name=request.form["name"].strip(),
                    account_type=request.form["account_type"],
                    detail_type=request.form.get("detail_type", "").strip() or None,
                    opening_balance=money(request.form.get("opening_balance", "0")),
                    description=request.form.get("description", "").strip() or None,
                    is_active=bool(request.form.get("is_active")),
                )
            )
        flash("Account created.")
        return redirect(url_for("accounting"))

    @app.post("/accounting/accounts/<int:account_id>")
    def update_account(account_id: int):
        with get_session() as session:
            account = session.get(Account, account_id)
            if account is None:
                flash("Account not found.")
                return redirect(url_for("accounting"))

            account.name = request.form["name"].strip()
            account.account_type = request.form["account_type"]
            account.detail_type = request.form.get("detail_type", "").strip() or None
            account.opening_balance = money(request.form.get("opening_balance", "0"))
            account.description = request.form.get("description", "").strip() or None
            account.is_active = bool(request.form.get("is_active"))

        flash("Account updated.")
        return redirect(url_for("accounting"))

    @app.get("/reports")
    def reports():
        with get_session() as session:
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            return render_template("reports.html", company=company, **build_reports_context(session))

    @app.get("/reports/tax")
    def tax_report():
        year = int(request.args.get("year", date.today().year))
        with get_session() as session:
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            return render_template("tax_report.html", company=company, **build_tax_report_context(session, year))

    @app.get("/reports/print")
    def print_reports():
        with get_session() as session:
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            return render_template("reports_print.html", company=company, **build_reports_context(session))

    @app.get("/reports/tax/print")
    def print_tax_report():
        year = int(request.args.get("year", date.today().year))
        with get_session() as session:
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            return render_template("tax_report_print.html", company=company, **build_tax_report_context(session, year))

    @app.get("/customers")
    def customers():
        with get_session() as session:
            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            return render_template("customers.html", customers=customers)

    @app.post("/customers")
    def create_customer():
        with get_session() as session:
            session.add(
                Customer(
                    name=request.form["name"].strip(),
                    email=request.form.get("email", "").strip() or None,
                    phone=request.form.get("phone", "").strip() or None,
                    notes=request.form.get("notes", "").strip() or None,
                )
            )
        flash("Customer added.")
        return redirect(url_for("customers"))

    @app.post("/customers/<int:customer_id>")
    def update_customer(customer_id: int):
        with get_session() as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                flash("Customer not found.")
                return redirect(url_for("customers"))

            customer.name = request.form["name"].strip()
            customer.email = request.form.get("email", "").strip() or None
            customer.phone = request.form.get("phone", "").strip() or None
            customer.notes = request.form.get("notes", "").strip() or None

        flash("Customer updated.")
        return redirect(url_for("customers"))

    @app.get("/jobs")
    def jobs():
        with get_session() as session:
            jobs = session.query(Job).order_by(Job.due_date.asc(), Job.name.asc()).all()
            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            contractors = session.query(Contractor).filter(Contractor.is_active.is_(True)).order_by(Contractor.name.asc()).all()
            return render_template("jobs.html", jobs=jobs, customers=customers, departments=departments, contractors=contractors)

    @app.post("/jobs")
    def create_job():
        with get_session() as session:
            job = Job(
                customer_id=int(request.form["customer_id"]),
                department_id=int(request.form["department_id"]) if request.form.get("department_id") else None,
                name=request.form["name"].strip(),
                description=request.form.get("description", "").strip() or None,
                status=request.form["status"],
                due_date=parse_date(request.form.get("due_date", "")),
                estimated_amount=money(request.form.get("estimated_amount", "0")),
                actual_cost=money(request.form.get("actual_cost", "0")),
            )

            drawing_file = save_job_file(request.files.get("drawing_file"), "drawing")
            if drawing_file:
                job.drawing_filename, job.drawing_original_filename = drawing_file

            model_file = save_job_file(request.files.get("model_file"), "model")
            if model_file:
                job.model_filename, job.model_original_filename = model_file

            session.add(job)
            assign_job_contractors(session, job)
        flash("Job created.")
        return redirect(url_for("jobs"))

    @app.get("/jobs/<int:job_id>")
    def edit_job(job_id: int):
        with get_session() as session:
            job = session.get(Job, job_id)
            if job is None:
                flash("Job not found.")
                return redirect(url_for("jobs"))

            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            contractors = session.query(Contractor).filter(Contractor.is_active.is_(True)).order_by(Contractor.name.asc()).all()
            detail_fields = job.department.job_fields if job.department else []
            return render_template(
                "job_edit.html",
                job=job,
                customers=customers,
                departments=departments,
                contractors=contractors,
                detail_fields=detail_fields,
                detail_values=field_value_map(job),
            )

    @app.post("/jobs/<int:job_id>")
    def update_job(job_id: int):
        with get_session() as session:
            job = session.get(Job, job_id)
            if job is None:
                flash("Job not found.")
                return redirect(url_for("jobs"))

            job.customer_id = int(request.form["customer_id"])
            job.department_id = int(request.form["department_id"]) if request.form.get("department_id") else None
            job.name = request.form["name"].strip()
            job.description = request.form.get("description", "").strip() or None
            job.status = request.form["status"]
            job.due_date = parse_date(request.form.get("due_date", ""))
            job.estimated_amount = money(request.form.get("estimated_amount", "0"))
            job.actual_cost = money(request.form.get("actual_cost", "0"))
            assign_job_contractors(session, job)

            drawing_file = save_job_file(request.files.get("drawing_file"), "drawing")
            model_file = save_job_file(request.files.get("model_file"), "model")

            if drawing_file:
                delete_static_file(job.drawing_filename)
                job.drawing_filename, job.drawing_original_filename = drawing_file
            if model_file:
                delete_static_file(job.model_filename)
                job.model_filename, job.model_original_filename = model_file

            department = session.get(Department, job.department_id) if job.department_id else None
            if department:
                save_job_detail_values(job, list(department.job_fields))

        flash("Job updated.")
        return redirect(url_for("edit_job", job_id=job_id))

    @app.post("/jobs/<int:job_id>/files")
    def update_job_files(job_id: int):
        with get_session() as session:
            job = session.get(Job, job_id)
            if job is None:
                flash("Job not found.")
                return redirect(url_for("jobs"))

            drawing_file = save_job_file(request.files.get("drawing_file"), "drawing")
            model_file = save_job_file(request.files.get("model_file"), "model")

            if drawing_file:
                delete_static_file(job.drawing_filename)
                job.drawing_filename, job.drawing_original_filename = drawing_file
            if model_file:
                delete_static_file(job.model_filename)
                job.model_filename, job.model_original_filename = model_file

            if drawing_file or model_file:
                flash("Job files updated.")
            else:
                flash("Choose a drawing or model file to upload.")
        return redirect(url_for("jobs"))

    @app.get("/tickets")
    def tickets():
        with get_session() as session:
            tickets = session.query(Ticket).order_by(Ticket.due_date.asc(), Ticket.opened_date.desc()).all()
            ticket_types = session.query(TicketType).order_by(TicketType.name.asc()).all()
            default_ticket_type = ticket_types[0] if ticket_types else None
            employees = session.query(Employee).filter(Employee.is_active.is_(True)).order_by(Employee.name.asc()).all()
            contractors = session.query(Contractor).filter(Contractor.is_active.is_(True)).order_by(Contractor.name.asc()).all()
            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            jobs = session.query(Job).order_by(Job.name.asc()).all()
            return render_template(
                "tickets.html",
                tickets=tickets,
                ticket_types=ticket_types,
                default_ticket_type=default_ticket_type,
                next_ticket_numbers={ticket_type.id: next_ticket_number(session, ticket_type) for ticket_type in ticket_types},
                employees=employees,
                contractors=contractors,
                customers=customers,
                departments=departments,
                jobs=jobs,
                ticket_statuses=TICKET_STATUSES,
                ticket_priorities=TICKET_PRIORITIES,
                today=date.today(),
            )

    @app.post("/tickets")
    def create_ticket():
        with get_session() as session:
            ticket = Ticket(ticket_number=request.form["ticket_number"].strip() or "T-0001", opened_date=date.today(), subject="")
            ticket_type = apply_ticket_form(session, ticket)
            if not request.form.get("ticket_number", "").strip():
                ticket.ticket_number = next_ticket_number(session, ticket_type)
            if ticket_type:
                save_ticket_detail_values(ticket, list(ticket_type.fields))
            session.add(ticket)
        flash("Ticket created.")
        return redirect(url_for("tickets"))

    @app.get("/tickets/<int:ticket_id>")
    def edit_ticket(ticket_id: int):
        with get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if ticket is None:
                flash("Ticket not found.")
                return redirect(url_for("tickets"))

            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            employees = session.query(Employee).filter(Employee.is_active.is_(True)).order_by(Employee.name.asc()).all()
            contractors = session.query(Contractor).filter(Contractor.is_active.is_(True)).order_by(Contractor.name.asc()).all()
            ticket_types = session.query(TicketType).order_by(TicketType.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            jobs = session.query(Job).order_by(Job.name.asc()).all()
            detail_fields = ticket.ticket_type_record.fields if ticket.ticket_type_record else []
            return render_template(
                "ticket_edit.html",
                ticket=ticket,
                ticket_types=ticket_types,
                employees=employees,
                contractors=contractors,
                customers=customers,
                departments=departments,
                jobs=jobs,
                next_ticket_numbers={ticket_type.id: next_ticket_number(session, ticket_type) for ticket_type in ticket_types},
                ticket_statuses=TICKET_STATUSES,
                ticket_priorities=TICKET_PRIORITIES,
                detail_fields=detail_fields,
                detail_values=ticket_detail_value_map(ticket),
            )

    @app.post("/tickets/<int:ticket_id>")
    def update_ticket(ticket_id: int):
        with get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if ticket is None:
                flash("Ticket not found.")
                return redirect(url_for("tickets"))

            ticket.ticket_number = request.form["ticket_number"].strip() or ticket.ticket_number
            ticket_type = apply_ticket_form(session, ticket)
            if ticket_type:
                save_ticket_detail_values(ticket, list(ticket_type.fields))

        flash("Ticket updated.")
        return redirect(url_for("edit_ticket", ticket_id=ticket_id))

    @app.get("/quotes")
    def quotes():
        with get_session() as session:
            quotes = session.query(Quote).order_by(Quote.issue_date.desc()).all()
            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            jobs = session.query(Job).order_by(Job.name.asc()).all()
            return render_template(
                "quotes.html",
                quotes=quotes,
                customers=customers,
                departments=departments,
                jobs=jobs,
                draft_number=next_quote_number(session),
                quote_total=quote_total,
            )

    @app.post("/quotes")
    def create_quote():
        descriptions = request.form.getlist("item_description")
        quantities = request.form.getlist("item_quantity")
        prices = request.form.getlist("item_unit_price")

        with get_session() as session:
            quote = Quote(
                customer_id=int(request.form["customer_id"]),
                department_id=int(request.form["department_id"]) if request.form.get("department_id") else None,
                job_id=int(request.form["job_id"]) if request.form.get("job_id") else None,
                quote_number=request.form["quote_number"].strip(),
                issue_date=parse_date(request.form["issue_date"]),
                valid_until=parse_date(request.form.get("valid_until", "")),
                status=request.form["status"],
                notes=request.form.get("notes", "").strip() or None,
            )

            for description, quantity, price in zip(descriptions, quantities, prices):
                if description.strip():
                    quote.line_items.append(
                        QuoteLineItem(
                            description=description.strip(),
                            quantity=money(quantity),
                            unit_price=money(price),
                        )
                    )

            quote.images.extend(save_work_images(request.files.getlist("work_images")))
            session.add(quote)
        flash("Quote created.")
        return redirect(url_for("quotes"))

    @app.get("/quotes/<int:quote_id>")
    def edit_quote(quote_id: int):
        with get_session() as session:
            quote = session.get(Quote, quote_id)
            if quote is None:
                flash("Quote not found.")
                return redirect(url_for("quotes"))

            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            jobs = session.query(Job).order_by(Job.name.asc()).all()
            return render_template(
                "quote_edit.html",
                quote=quote,
                customers=customers,
                departments=departments,
                jobs=jobs,
                quote_total=quote_total,
            )

    @app.get("/quotes/<int:quote_id>/print")
    def print_quote(quote_id: int):
        with get_session() as session:
            quote = session.get(Quote, quote_id)
            if quote is None:
                flash("Quote not found.")
                return redirect(url_for("quotes"))
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            return render_template("quote_print.html", quote=quote, company=company, quote_total=quote_total)

    @app.post("/quotes/<int:quote_id>")
    def update_quote(quote_id: int):
        descriptions = request.form.getlist("item_description")
        quantities = request.form.getlist("item_quantity")
        prices = request.form.getlist("item_unit_price")

        with get_session() as session:
            quote = session.get(Quote, quote_id)
            if quote is None:
                flash("Quote not found.")
                return redirect(url_for("quotes"))

            quote.customer_id = int(request.form["customer_id"])
            quote.department_id = int(request.form["department_id"]) if request.form.get("department_id") else None
            quote.job_id = int(request.form["job_id"]) if request.form.get("job_id") else None
            quote.quote_number = request.form["quote_number"].strip()
            quote.issue_date = parse_date(request.form["issue_date"])
            quote.valid_until = parse_date(request.form.get("valid_until", ""))
            quote.status = request.form["status"]
            quote.notes = request.form.get("notes", "").strip() or None
            quote.line_items.clear()

            for description, quantity, price in zip(descriptions, quantities, prices):
                if description.strip():
                    quote.line_items.append(
                        QuoteLineItem(
                            description=description.strip(),
                            quantity=money(quantity),
                            unit_price=money(price),
                        )
                    )

            quote.images.extend(save_work_images(request.files.getlist("work_images")))

        flash("Quote updated.")
        return redirect(url_for("edit_quote", quote_id=quote_id))

    @app.get("/invoices")
    def invoices():
        with get_session() as session:
            invoices = session.query(Invoice).order_by(Invoice.issue_date.desc()).all()
            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            jobs = session.query(Job).order_by(Job.name.asc()).all()
            return render_template(
                "invoices.html",
                invoices=invoices,
                customers=customers,
                departments=departments,
                jobs=jobs,
                draft_number=next_invoice_number(session),
                invoice_total=invoice_total,
                invoice_paid=invoice_paid,
            )

    @app.post("/invoices")
    def create_invoice():
        descriptions = request.form.getlist("item_description")
        quantities = request.form.getlist("item_quantity")
        prices = request.form.getlist("item_unit_price")

        with get_session() as session:
            invoice = Invoice(
                customer_id=int(request.form["customer_id"]),
                department_id=int(request.form["department_id"]) if request.form.get("department_id") else None,
                job_id=int(request.form["job_id"]) if request.form.get("job_id") else None,
                invoice_number=request.form["invoice_number"].strip(),
                issue_date=parse_date(request.form["issue_date"]),
                due_date=parse_date(request.form["due_date"]),
                status=request.form["status"],
                notes=request.form.get("notes", "").strip() or None,
            )

            for description, quantity, price in zip(descriptions, quantities, prices):
                if description.strip():
                    invoice.line_items.append(
                        InvoiceLineItem(
                            description=description.strip(),
                            quantity=money(quantity),
                            unit_price=money(price),
                        )
                    )

            invoice.images.extend(save_work_images(request.files.getlist("work_images")))
            session.add(invoice)
        flash("Invoice created.")
        return redirect(url_for("invoices"))

    @app.get("/invoices/<int:invoice_id>")
    def edit_invoice(invoice_id: int):
        with get_session() as session:
            invoice = session.get(Invoice, invoice_id)
            if invoice is None:
                flash("Invoice not found.")
                return redirect(url_for("invoices"))

            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            departments = session.query(Department).order_by(Department.name.asc()).all()
            jobs = session.query(Job).order_by(Job.name.asc()).all()
            return render_template(
                "invoice_edit.html",
                invoice=invoice,
                customers=customers,
                departments=departments,
                jobs=jobs,
                invoice_total=invoice_total,
                invoice_paid=invoice_paid,
            )

    @app.get("/invoices/<int:invoice_id>/print")
    def print_invoice(invoice_id: int):
        with get_session() as session:
            invoice = session.get(Invoice, invoice_id)
            if invoice is None:
                flash("Invoice not found.")
                return redirect(url_for("invoices"))
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            return render_template(
                "invoice_print.html",
                invoice=invoice,
                company=company,
                invoice_total=invoice_total,
                invoice_paid=invoice_paid,
            )

    @app.post("/invoices/<int:invoice_id>")
    def update_invoice(invoice_id: int):
        descriptions = request.form.getlist("item_description")
        quantities = request.form.getlist("item_quantity")
        prices = request.form.getlist("item_unit_price")

        with get_session() as session:
            invoice = session.get(Invoice, invoice_id)
            if invoice is None:
                flash("Invoice not found.")
                return redirect(url_for("invoices"))

            invoice.customer_id = int(request.form["customer_id"])
            invoice.department_id = int(request.form["department_id"]) if request.form.get("department_id") else None
            invoice.job_id = int(request.form["job_id"]) if request.form.get("job_id") else None
            invoice.invoice_number = request.form["invoice_number"].strip()
            invoice.issue_date = parse_date(request.form["issue_date"])
            invoice.due_date = parse_date(request.form["due_date"])
            invoice.status = request.form["status"]
            invoice.notes = request.form.get("notes", "").strip() or None
            invoice.line_items.clear()

            for description, quantity, price in zip(descriptions, quantities, prices):
                if description.strip():
                    invoice.line_items.append(
                        InvoiceLineItem(
                            description=description.strip(),
                            quantity=money(quantity),
                            unit_price=money(price),
                        )
                    )

            invoice.images.extend(save_work_images(request.files.getlist("work_images")))

        flash("Invoice updated.")
        return redirect(url_for("edit_invoice", invoice_id=invoice_id))

    @app.get("/bills")
    def bills():
        with get_session() as session:
            bills = session.query(Bill).order_by(Bill.due_date.asc()).all()
            return render_template(
                "bills.html",
                bills=bills,
                bill_paid=bill_paid,
                tax_categories=TAX_CATEGORIES,
                tax_category_labels=TAX_CATEGORY_LABELS,
            )

    @app.post("/bills")
    def create_bill():
        with get_session() as session:
            session.add(
                Bill(
                    vendor_name=request.form["vendor_name"].strip(),
                    reference=request.form.get("reference", "").strip() or None,
                    category=request.form.get("category", "").strip() or None,
                    tax_category=clean_tax_category(request.form.get("tax_category")),
                    amount=money(request.form["amount"]),
                    due_date=parse_date(request.form["due_date"]),
                    status=request.form["status"],
                    notes=request.form.get("notes", "").strip() or None,
                )
            )
        flash("Bill recorded.")
        return redirect(url_for("bills"))

    @app.get("/payments")
    def payments():
        with get_session() as session:
            payments = session.query(Payment).order_by(Payment.payment_date.desc()).all()
            invoices = session.query(Invoice).order_by(Invoice.invoice_number.asc()).all()
            bills = session.query(Bill).order_by(Bill.vendor_name.asc()).all()
            return render_template("payments.html", payments=payments, invoices=invoices, bills=bills)

    @app.post("/payments")
    def create_payment():
        with get_session() as session:
            session.add(
                Payment(
                    payment_type=request.form["payment_type"],
                    invoice_id=int(request.form["invoice_id"]) if request.form.get("invoice_id") else None,
                    bill_id=int(request.form["bill_id"]) if request.form.get("bill_id") else None,
                    payment_date=parse_date(request.form["payment_date"]),
                    amount=money(request.form["amount"]),
                    method=request.form.get("method", "").strip() or None,
                    notes=request.form.get("notes", "").strip() or None,
                )
            )
        flash("Payment saved.")
        return redirect(url_for("payments"))
