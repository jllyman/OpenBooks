#include "storage.h"

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace {
std::string escapeCsv(const std::string& value) {
    if (value.find_first_of(",\"\n\r") == std::string::npos) {
        return value;
    }

    std::string escaped = "\"";
    for (char ch : value) {
        if (ch == '"') {
            escaped += "\"\"";
        } else {
            escaped += ch;
        }
    }
    escaped += "\"";
    return escaped;
}

std::vector<std::string> parseCsvRow(const std::string& line) {
    std::vector<std::string> fields;
    std::string current;
    bool inQuotes = false;

    for (std::size_t i = 0; i < line.size(); ++i) {
        const char ch = line[i];
        if (inQuotes) {
            if (ch == '"' && i + 1 < line.size() && line[i + 1] == '"') {
                current += '"';
                ++i;
            } else if (ch == '"') {
                inQuotes = false;
            } else {
                current += ch;
            }
        } else if (ch == ',') {
            fields.push_back(current);
            current.clear();
        } else if (ch == '"') {
            inQuotes = true;
        } else {
            current += ch;
        }
    }

    fields.push_back(current);
    return fields;
}

double parseDouble(const std::string& value) {
    return value.empty() ? 0.0 : std::stod(value);
}

int parseInt(const std::string& value) {
    return value.empty() ? 0 : std::stoi(value);
}

template <typename T>
int nextIdFor(const std::vector<T>& items) {
    int maxId = 0;
    for (const auto& item : items) {
        maxId = std::max(maxId, item.id);
    }
    return maxId + 1;
}

std::filesystem::path filePath(const std::filesystem::path& base, const std::string& name) {
    return base / name;
}
}

Storage::Storage(std::filesystem::path dataDirectory)
    : dataDirectory_(std::move(dataDirectory)) {
}

void Storage::load() {
    std::filesystem::create_directories(dataDirectory_);

    customers_.clear();
    jobs_.clear();
    invoices_.clear();
    invoiceItems_.clear();
    bills_.clear();
    payments_.clear();

    {
        std::ifstream in(filePath(dataDirectory_, "customers.csv"));
        std::string line;
        std::getline(in, line);
        while (std::getline(in, line)) {
            const auto fields = parseCsvRow(line);
            if (fields.size() < 5) {
                continue;
            }
            customers_.push_back({parseInt(fields[0]), fields[1], fields[2], fields[3], fields[4]});
        }
    }

    {
        std::ifstream in(filePath(dataDirectory_, "jobs.csv"));
        std::string line;
        std::getline(in, line);
        while (std::getline(in, line)) {
            const auto fields = parseCsvRow(line);
            if (fields.size() < 8) {
                continue;
            }
            jobs_.push_back({
                parseInt(fields[0]),
                parseInt(fields[1]),
                fields[2],
                fields[3],
                fields[4],
                fields[5],
                parseDouble(fields[6]),
                parseDouble(fields[7]),
            });
        }
    }

    {
        std::ifstream in(filePath(dataDirectory_, "invoices.csv"));
        std::string line;
        std::getline(in, line);
        while (std::getline(in, line)) {
            const auto fields = parseCsvRow(line);
            if (fields.size() < 8) {
                continue;
            }
            invoices_.push_back({
                parseInt(fields[0]),
                parseInt(fields[1]),
                parseInt(fields[2]),
                fields[3],
                fields[4],
                fields[5],
                fields[6],
                fields[7],
            });
        }
    }

    {
        std::ifstream in(filePath(dataDirectory_, "invoice_items.csv"));
        std::string line;
        std::getline(in, line);
        while (std::getline(in, line)) {
            const auto fields = parseCsvRow(line);
            if (fields.size() < 5) {
                continue;
            }
            invoiceItems_.push_back({
                parseInt(fields[0]),
                parseInt(fields[1]),
                fields[2],
                parseDouble(fields[3]),
                parseDouble(fields[4]),
            });
        }
    }

    {
        std::ifstream in(filePath(dataDirectory_, "bills.csv"));
        std::string line;
        std::getline(in, line);
        while (std::getline(in, line)) {
            const auto fields = parseCsvRow(line);
            if (fields.size() < 8) {
                continue;
            }
            bills_.push_back({
                parseInt(fields[0]),
                fields[1],
                fields[2],
                fields[3],
                parseDouble(fields[4]),
                fields[5],
                fields[6],
                fields[7],
            });
        }
    }

    {
        std::ifstream in(filePath(dataDirectory_, "payments.csv"));
        std::string line;
        std::getline(in, line);
        while (std::getline(in, line)) {
            const auto fields = parseCsvRow(line);
            if (fields.size() < 8) {
                continue;
            }
            payments_.push_back({
                parseInt(fields[0]),
                fields[1],
                parseInt(fields[2]),
                parseInt(fields[3]),
                fields[4],
                parseDouble(fields[5]),
                fields[6],
                fields[7],
            });
        }
    }
}

void Storage::save() const {
    std::filesystem::create_directories(dataDirectory_);

    {
        std::ofstream out(filePath(dataDirectory_, "customers.csv"));
        out << "id,name,email,phone,notes\n";
        for (const auto& item : customers_) {
            out << item.id << "," << escapeCsv(item.name) << "," << escapeCsv(item.email) << ","
                << escapeCsv(item.phone) << "," << escapeCsv(item.notes) << "\n";
        }
    }

    {
        std::ofstream out(filePath(dataDirectory_, "jobs.csv"));
        out << "id,customer_id,name,description,status,due_date,estimated_amount,actual_cost\n";
        for (const auto& item : jobs_) {
            out << item.id << "," << item.customerId << "," << escapeCsv(item.name) << ","
                << escapeCsv(item.description) << "," << escapeCsv(item.status) << ","
                << escapeCsv(item.dueDate) << "," << item.estimatedAmount << "," << item.actualCost << "\n";
        }
    }

    {
        std::ofstream out(filePath(dataDirectory_, "invoices.csv"));
        out << "id,customer_id,job_id,invoice_number,issue_date,due_date,status,notes\n";
        for (const auto& item : invoices_) {
            out << item.id << "," << item.customerId << "," << item.jobId << ","
                << escapeCsv(item.invoiceNumber) << "," << escapeCsv(item.issueDate) << ","
                << escapeCsv(item.dueDate) << "," << escapeCsv(item.status) << ","
                << escapeCsv(item.notes) << "\n";
        }
    }

    {
        std::ofstream out(filePath(dataDirectory_, "invoice_items.csv"));
        out << "id,invoice_id,description,quantity,unit_price\n";
        for (const auto& item : invoiceItems_) {
            out << item.id << "," << item.invoiceId << "," << escapeCsv(item.description) << ","
                << item.quantity << "," << item.unitPrice << "\n";
        }
    }

    {
        std::ofstream out(filePath(dataDirectory_, "bills.csv"));
        out << "id,vendor_name,reference,category,amount,due_date,status,notes\n";
        for (const auto& item : bills_) {
            out << item.id << "," << escapeCsv(item.vendorName) << "," << escapeCsv(item.reference) << ","
                << escapeCsv(item.category) << "," << item.amount << "," << escapeCsv(item.dueDate) << ","
                << escapeCsv(item.status) << "," << escapeCsv(item.notes) << "\n";
        }
    }

    {
        std::ofstream out(filePath(dataDirectory_, "payments.csv"));
        out << "id,payment_type,invoice_id,bill_id,payment_date,amount,method,notes\n";
        for (const auto& item : payments_) {
            out << item.id << "," << escapeCsv(item.paymentType) << "," << item.invoiceId << ","
                << item.billId << "," << escapeCsv(item.paymentDate) << "," << item.amount << ","
                << escapeCsv(item.method) << "," << escapeCsv(item.notes) << "\n";
        }
    }
}

std::vector<Customer>& Storage::customers() { return customers_; }
std::vector<Job>& Storage::jobs() { return jobs_; }
std::vector<Invoice>& Storage::invoices() { return invoices_; }
std::vector<InvoiceItem>& Storage::invoiceItems() { return invoiceItems_; }
std::vector<Bill>& Storage::bills() { return bills_; }
std::vector<Payment>& Storage::payments() { return payments_; }

const std::vector<Customer>& Storage::customers() const { return customers_; }
const std::vector<Job>& Storage::jobs() const { return jobs_; }
const std::vector<Invoice>& Storage::invoices() const { return invoices_; }
const std::vector<InvoiceItem>& Storage::invoiceItems() const { return invoiceItems_; }
const std::vector<Bill>& Storage::bills() const { return bills_; }
const std::vector<Payment>& Storage::payments() const { return payments_; }

int Storage::nextCustomerId() const { return nextIdFor(customers_); }
int Storage::nextJobId() const { return nextIdFor(jobs_); }
int Storage::nextInvoiceId() const { return nextIdFor(invoices_); }
int Storage::nextInvoiceItemId() const { return nextIdFor(invoiceItems_); }
int Storage::nextBillId() const { return nextIdFor(bills_); }
int Storage::nextPaymentId() const { return nextIdFor(payments_); }

double invoiceTotal(const Invoice& invoice, const std::vector<InvoiceItem>& items) {
    double total = 0.0;
    for (const auto& item : items) {
        if (item.invoiceId == invoice.id) {
            total += item.quantity * item.unitPrice;
        }
    }
    return total;
}

double invoicePaid(const Invoice& invoice, const std::vector<Payment>& payments) {
    double total = 0.0;
    for (const auto& payment : payments) {
        if (payment.paymentType == "AR" && payment.invoiceId == invoice.id) {
            total += payment.amount;
        }
    }
    return total;
}

double billPaid(const Bill& bill, const std::vector<Payment>& payments) {
    double total = 0.0;
    for (const auto& payment : payments) {
        if (payment.paymentType == "AP" && payment.billId == bill.id) {
            total += payment.amount;
        }
    }
    return total;
}

DashboardSnapshot buildDashboard(const Storage& storage) {
    DashboardSnapshot snapshot;

    for (const auto& invoice : storage.invoices()) {
        const double total = invoiceTotal(invoice, storage.invoiceItems());
        snapshot.invoiceVolume += total;
        snapshot.openAr += std::max(0.0, total - invoicePaid(invoice, storage.payments()));
    }

    for (const auto& bill : storage.bills()) {
        snapshot.billVolume += bill.amount;
        snapshot.openAp += std::max(0.0, bill.amount - billPaid(bill, storage.payments()));
    }

    for (const auto& job : storage.jobs()) {
        if (job.status != "Done" && job.status != "Cancelled") {
            ++snapshot.activeJobs;
        }
    }

    return snapshot;
}
