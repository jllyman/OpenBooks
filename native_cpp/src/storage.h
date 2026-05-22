#pragma once

#include "models.h"

#include <filesystem>
#include <vector>

class Storage {
public:
    explicit Storage(std::filesystem::path dataDirectory);

    void load();
    void save() const;

    std::vector<Customer>& customers();
    std::vector<Job>& jobs();
    std::vector<Invoice>& invoices();
    std::vector<InvoiceItem>& invoiceItems();
    std::vector<Bill>& bills();
    std::vector<Payment>& payments();

    const std::vector<Customer>& customers() const;
    const std::vector<Job>& jobs() const;
    const std::vector<Invoice>& invoices() const;
    const std::vector<InvoiceItem>& invoiceItems() const;
    const std::vector<Bill>& bills() const;
    const std::vector<Payment>& payments() const;

    int nextCustomerId() const;
    int nextJobId() const;
    int nextInvoiceId() const;
    int nextInvoiceItemId() const;
    int nextBillId() const;
    int nextPaymentId() const;

private:
    std::filesystem::path dataDirectory_;
    std::vector<Customer> customers_;
    std::vector<Job> jobs_;
    std::vector<Invoice> invoices_;
    std::vector<InvoiceItem> invoiceItems_;
    std::vector<Bill> bills_;
    std::vector<Payment> payments_;
};

double invoiceTotal(const Invoice& invoice, const std::vector<InvoiceItem>& items);
double invoicePaid(const Invoice& invoice, const std::vector<Payment>& payments);
double billPaid(const Bill& bill, const std::vector<Payment>& payments);
DashboardSnapshot buildDashboard(const Storage& storage);
