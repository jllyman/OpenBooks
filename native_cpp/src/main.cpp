#include "storage.h"

#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>

namespace {
std::string prompt(const std::string& label) {
    std::cout << label;
    std::string value;
    std::getline(std::cin, value);
    return value;
}

int promptInt(const std::string& label) {
    while (true) {
        const auto value = prompt(label);
        try {
            return value.empty() ? 0 : std::stoi(value);
        } catch (...) {
            std::cout << "Enter a whole number.\n";
        }
    }
}

double promptDouble(const std::string& label) {
    while (true) {
        const auto value = prompt(label);
        try {
            return value.empty() ? 0.0 : std::stod(value);
        } catch (...) {
            std::cout << "Enter a numeric amount.\n";
        }
    }
}

std::string customerName(const Storage& storage, int customerId) {
    for (const auto& customer : storage.customers()) {
        if (customer.id == customerId) {
            return customer.name;
        }
    }
    return "Unknown";
}

std::string invoiceReference(const Storage& storage, int invoiceId) {
    for (const auto& invoice : storage.invoices()) {
        if (invoice.id == invoiceId) {
            return invoice.invoiceNumber;
        }
    }
    return "Unknown";
}

std::string billReference(const Storage& storage, int billId) {
    for (const auto& bill : storage.bills()) {
        if (bill.id == billId) {
            return bill.vendorName;
        }
    }
    return "Unknown";
}

void showDashboard(const Storage& storage) {
    const auto snapshot = buildDashboard(storage);
    std::cout << "\nOpenBooks dashboard\n";
    std::cout << "-------------------\n";
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "Open AR: $" << snapshot.openAr << "\n";
    std::cout << "Open AP: $" << snapshot.openAp << "\n";
    std::cout << "Invoice volume: $" << snapshot.invoiceVolume << "\n";
    std::cout << "Bill volume: $" << snapshot.billVolume << "\n";
    std::cout << "Active jobs: " << snapshot.activeJobs << "\n\n";
}

void listCustomers(const Storage& storage) {
    std::cout << "\nCustomers\n";
    std::cout << "---------\n";
    for (const auto& customer : storage.customers()) {
        std::cout << customer.id << " | " << customer.name << " | " << customer.email << " | " << customer.phone << "\n";
    }
    if (storage.customers().empty()) {
        std::cout << "No customers yet.\n";
    }
    std::cout << "\n";
}

void addCustomer(Storage& storage) {
    Customer customer;
    customer.id = storage.nextCustomerId();
    customer.name = prompt("Customer name: ");
    customer.email = prompt("Email: ");
    customer.phone = prompt("Phone: ");
    customer.notes = prompt("Notes: ");
    storage.customers().push_back(customer);
    storage.save();
    std::cout << "Customer saved.\n\n";
}

void listJobs(const Storage& storage) {
    std::cout << "\nJobs\n";
    std::cout << "----\n";
    for (const auto& job : storage.jobs()) {
        std::cout << job.id << " | " << job.name << " | " << customerName(storage, job.customerId)
                  << " | " << job.status << " | Due " << job.dueDate << "\n";
    }
    if (storage.jobs().empty()) {
        std::cout << "No jobs yet.\n";
    }
    std::cout << "\n";
}

void addJob(Storage& storage) {
    if (storage.customers().empty()) {
        std::cout << "Add a customer first.\n\n";
        return;
    }

    listCustomers(storage);

    Job job;
    job.id = storage.nextJobId();
    job.customerId = promptInt("Customer ID: ");
    job.name = prompt("Job name: ");
    job.description = prompt("Description: ");
    job.status = prompt("Status (Planned/Quoted/In Progress/Waiting/Done/Cancelled): ");
    job.dueDate = prompt("Due date (YYYY-MM-DD): ");
    job.estimatedAmount = promptDouble("Estimated amount: ");
    job.actualCost = promptDouble("Actual cost: ");
    storage.jobs().push_back(job);
    storage.save();
    std::cout << "Job saved.\n\n";
}

void listInvoices(const Storage& storage) {
    std::cout << "\nInvoices\n";
    std::cout << "--------\n";
    std::cout << std::fixed << std::setprecision(2);
    for (const auto& invoice : storage.invoices()) {
        const double total = invoiceTotal(invoice, storage.invoiceItems());
        const double open = total - invoicePaid(invoice, storage.payments());
        std::cout << invoice.id << " | " << invoice.invoiceNumber << " | " << customerName(storage, invoice.customerId)
                  << " | Total $" << total << " | Open $" << open << " | " << invoice.status << "\n";
    }
    if (storage.invoices().empty()) {
        std::cout << "No invoices yet.\n";
    }
    std::cout << "\n";
}

void addInvoice(Storage& storage) {
    if (storage.customers().empty()) {
        std::cout << "Add a customer first.\n\n";
        return;
    }

    listCustomers(storage);
    listJobs(storage);

    Invoice invoice;
    invoice.id = storage.nextInvoiceId();
    invoice.customerId = promptInt("Customer ID: ");
    invoice.jobId = promptInt("Linked job ID (0 for none): ");
    invoice.invoiceNumber = prompt("Invoice number: ");
    invoice.issueDate = prompt("Issue date (YYYY-MM-DD): ");
    invoice.dueDate = prompt("Due date (YYYY-MM-DD): ");
    invoice.status = prompt("Status: ");
    invoice.notes = prompt("Notes: ");
    storage.invoices().push_back(invoice);

    int nextItemId = storage.nextInvoiceItemId();
    while (true) {
        const auto description = prompt("Line item description (blank to finish): ");
        if (description.empty()) {
            break;
        }

        InvoiceItem item;
        item.id = nextItemId++;
        item.invoiceId = invoice.id;
        item.description = description;
        item.quantity = promptDouble("Quantity: ");
        item.unitPrice = promptDouble("Unit price: ");
        storage.invoiceItems().push_back(item);
    }

    storage.save();
    std::cout << "Invoice saved.\n\n";
}

void listBills(const Storage& storage) {
    std::cout << "\nBills\n";
    std::cout << "-----\n";
    std::cout << std::fixed << std::setprecision(2);
    for (const auto& bill : storage.bills()) {
        const double open = bill.amount - billPaid(bill, storage.payments());
        std::cout << bill.id << " | " << bill.vendorName << " | Amount $" << bill.amount
                  << " | Open $" << open << " | Due " << bill.dueDate << "\n";
    }
    if (storage.bills().empty()) {
        std::cout << "No bills yet.\n";
    }
    std::cout << "\n";
}

void addBill(Storage& storage) {
    Bill bill;
    bill.id = storage.nextBillId();
    bill.vendorName = prompt("Vendor name: ");
    bill.reference = prompt("Reference: ");
    bill.category = prompt("Category: ");
    bill.amount = promptDouble("Amount: ");
    bill.dueDate = prompt("Due date (YYYY-MM-DD): ");
    bill.status = prompt("Status: ");
    bill.notes = prompt("Notes: ");
    storage.bills().push_back(bill);
    storage.save();
    std::cout << "Bill saved.\n\n";
}

void listPayments(const Storage& storage) {
    std::cout << "\nPayments\n";
    std::cout << "--------\n";
    std::cout << std::fixed << std::setprecision(2);
    for (const auto& payment : storage.payments()) {
        std::string reference = "Unlinked";
        if (payment.paymentType == "AR" && payment.invoiceId != 0) {
            reference = invoiceReference(storage, payment.invoiceId);
        } else if (payment.paymentType == "AP" && payment.billId != 0) {
            reference = billReference(storage, payment.billId);
        }
        std::cout << payment.id << " | " << payment.paymentDate << " | " << payment.paymentType
                  << " | $" << payment.amount << " | " << reference << "\n";
    }
    if (storage.payments().empty()) {
        std::cout << "No payments yet.\n";
    }
    std::cout << "\n";
}

void addPayment(Storage& storage) {
    Payment payment;
    payment.id = storage.nextPaymentId();
    payment.paymentType = prompt("Payment type (AR/AP): ");
    if (payment.paymentType == "AR") {
        listInvoices(storage);
        payment.invoiceId = promptInt("Invoice ID: ");
        payment.billId = 0;
    } else {
        listBills(storage);
        payment.billId = promptInt("Bill ID: ");
        payment.invoiceId = 0;
    }
    payment.paymentDate = prompt("Payment date (YYYY-MM-DD): ");
    payment.amount = promptDouble("Amount: ");
    payment.method = prompt("Method: ");
    payment.notes = prompt("Notes: ");
    storage.payments().push_back(payment);
    storage.save();
    std::cout << "Payment saved.\n\n";
}

void showMenu() {
    std::cout << "OpenBooks Native C++\n";
    std::cout << "1. Dashboard\n";
    std::cout << "2. List customers\n";
    std::cout << "3. Add customer\n";
    std::cout << "4. List jobs\n";
    std::cout << "5. Add job\n";
    std::cout << "6. List invoices\n";
    std::cout << "7. Add invoice\n";
    std::cout << "8. List bills\n";
    std::cout << "9. Add bill\n";
    std::cout << "10. List payments\n";
    std::cout << "11. Add payment\n";
    std::cout << "0. Save and exit\n";
}

std::filesystem::path resolveDataPath() {
    const auto cwd = std::filesystem::current_path();
    const auto localData = cwd / "data";
    if (std::filesystem::exists(localData)) {
        return localData;
    }

    const auto parentData = cwd.parent_path() / "data";
    if (std::filesystem::exists(parentData)) {
        return parentData;
    }

    const auto grandParentData = cwd.parent_path().parent_path() / "data";
    if (std::filesystem::exists(grandParentData)) {
        return grandParentData;
    }

    return localData;
}
}

int main() {
    try {
        const std::filesystem::path dataPath = resolveDataPath();
        Storage storage(dataPath);
        storage.load();

        while (true) {
            showMenu();
            const int choice = promptInt("Choose an option: ");
            std::cout << "\n";

            switch (choice) {
            case 1:
                showDashboard(storage);
                break;
            case 2:
                listCustomers(storage);
                break;
            case 3:
                addCustomer(storage);
                break;
            case 4:
                listJobs(storage);
                break;
            case 5:
                addJob(storage);
                break;
            case 6:
                listInvoices(storage);
                break;
            case 7:
                addInvoice(storage);
                break;
            case 8:
                listBills(storage);
                break;
            case 9:
                addBill(storage);
                break;
            case 10:
                listPayments(storage);
                break;
            case 11:
                addPayment(storage);
                break;
            case 0:
                storage.save();
                std::cout << "Data saved. Goodbye.\n";
                return 0;
            default:
                std::cout << "Unknown option.\n\n";
                break;
            }
        }
    } catch (const std::exception& ex) {
        std::cerr << "Fatal error: " << ex.what() << "\n";
        return 1;
    }
}
