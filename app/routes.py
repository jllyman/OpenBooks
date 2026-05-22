from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .database import (
    Account,
    Bill,
    CompanySettings,
    Customer,
    Department,
    Invoice,
    InvoiceLineItem,
    Job,
    Payment,
    Quote,
    QuoteLineItem,
    WorkImage,
    bill_paid,
    dashboard_snapshot,
    get_company_settings,
    get_session,
    invoice_paid,
    invoice_total,
    money,
    next_invoice_number,
    next_quote_number,
    quote_total,
)


ALLOWED_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}


def parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def open_invoice_amount(invoice: Invoice) -> Decimal:
    return max(invoice_total(invoice) - invoice_paid(invoice), Decimal("0.00"))


def open_bill_amount(bill: Bill) -> Decimal:
    return max(money(bill.amount) - bill_paid(bill), Decimal("0.00"))


def build_reports_context(session):
    invoices = session.query(Invoice).order_by(Invoice.issue_date.desc()).all()
    bills = session.query(Bill).order_by(Bill.due_date.asc()).all()
    jobs = session.query(Job).order_by(Job.name.asc()).all()
    accounts = session.query(Account).order_by(Account.account_type.asc(), Account.name.asc()).all()

    revenue = sum((invoice_total(invoice) for invoice in invoices), Decimal("0.00"))
    expenses = sum((money(bill.amount) for bill in bills), Decimal("0.00"))
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
            "expenses": expenses,
            "gross_profit": gross_profit,
            "ar_open": ar_open,
            "ap_open": ap_open,
            "estimated_pipeline": estimated_pipeline,
        },
        "invoices": invoices,
        "bills": bills,
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


def register_routes(app):
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
                }
            }

    @app.get("/")
    def dashboard():
        with get_session() as session:
            snapshot = dashboard_snapshot(session)
            recent_invoices = session.query(Invoice).order_by(Invoice.issue_date.desc()).limit(5).all()
            recent_bills = session.query(Bill).order_by(Bill.due_date.asc()).limit(5).all()
            jobs = session.query(Job).order_by(Job.due_date.asc()).limit(5).all()
            return render_template(
                "dashboard.html",
                snapshot=snapshot,
                recent_invoices=recent_invoices,
                recent_bills=recent_bills,
                jobs=jobs,
                invoice_total=invoice_total,
                invoice_paid=invoice_paid,
                bill_paid=bill_paid,
            )

    @app.get("/settings")
    def settings():
        with get_session() as session:
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            departments = session.query(Department).order_by(Department.name.asc()).all()
            return render_template("settings.html", company=company, departments=departments)

    @app.post("/settings/company")
    def update_company_settings():
        with get_session() as session:
            company = get_company_settings(session)
            company.company_name = request.form.get("company_name", "").strip() or "OpenBooks"
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
        return redirect(url_for("settings"))

    @app.get("/departments")
    def departments():
        return redirect(url_for("settings"))

    @app.post("/departments")
    def create_department():
        with get_session() as session:
            session.add(
                Department(
                    name=request.form["name"].strip(),
                    description=request.form.get("description", "").strip() or None,
                )
            )
        flash("Department created.")
        return redirect(url_for("settings"))

    @app.get("/accounting")
    def accounting():
        with get_session() as session:
            accounts = session.query(Account).order_by(Account.account_type.asc(), Account.name.asc()).all()
            return render_template("accounting.html", accounts=accounts)

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
            return render_template("reports.html", **build_reports_context(session))

    @app.get("/reports/print")
    def print_reports():
        with get_session() as session:
            company = session.get(CompanySettings, 1) or CompanySettings(id=1, company_name="OpenBooks")
            return render_template("reports_print.html", company=company, **build_reports_context(session))

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
            return render_template("jobs.html", jobs=jobs, customers=customers)

    @app.post("/jobs")
    def create_job():
        with get_session() as session:
            session.add(
                Job(
                    customer_id=int(request.form["customer_id"]),
                    name=request.form["name"].strip(),
                    description=request.form.get("description", "").strip() or None,
                    status=request.form["status"],
                    due_date=parse_date(request.form.get("due_date", "")),
                    estimated_amount=money(request.form.get("estimated_amount", "0")),
                    actual_cost=money(request.form.get("actual_cost", "0")),
                )
            )
        flash("Job created.")
        return redirect(url_for("jobs"))

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
            return render_template("bills.html", bills=bills, bill_paid=bill_paid)

    @app.post("/bills")
    def create_bill():
        with get_session() as session:
            session.add(
                Bill(
                    vendor_name=request.form["vendor_name"].strip(),
                    reference=request.form.get("reference", "").strip() or None,
                    category=request.form.get("category", "").strip() or None,
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
