from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, request, url_for

from .database import (
    Bill,
    Customer,
    Invoice,
    InvoiceLineItem,
    Job,
    Payment,
    Quote,
    QuoteLineItem,
    bill_paid,
    dashboard_snapshot,
    get_session,
    invoice_paid,
    invoice_total,
    money,
    next_invoice_number,
    next_quote_number,
    quote_total,
)


def parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def register_routes(app):
    @app.template_filter("currency")
    def currency_filter(value):
        return f"${float(value or 0):,.2f}"

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
            jobs = session.query(Job).order_by(Job.name.asc()).all()
            return render_template(
                "quotes.html",
                quotes=quotes,
                customers=customers,
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

            session.add(quote)
        flash("Quote created.")
        return redirect(url_for("quotes"))

    @app.get("/invoices")
    def invoices():
        with get_session() as session:
            invoices = session.query(Invoice).order_by(Invoice.issue_date.desc()).all()
            customers = session.query(Customer).order_by(Customer.name.asc()).all()
            jobs = session.query(Job).order_by(Job.name.asc()).all()
            return render_template(
                "invoices.html",
                invoices=invoices,
                customers=customers,
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

            session.add(invoice)
        flash("Invoice created.")
        return redirect(url_for("invoices"))

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
