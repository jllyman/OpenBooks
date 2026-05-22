#pragma once

#include <string>
#include <vector>

struct Customer {
    int id {};
    std::string name;
    std::string email;
    std::string phone;
    std::string notes;
};

struct Job {
    int id {};
    int customerId {};
    std::string name;
    std::string description;
    std::string status;
    std::string dueDate;
    double estimatedAmount {};
    double actualCost {};
};

struct Invoice {
    int id {};
    int customerId {};
    int jobId {};
    std::string invoiceNumber;
    std::string issueDate;
    std::string dueDate;
    std::string status;
    std::string notes;
};

struct InvoiceItem {
    int id {};
    int invoiceId {};
    std::string description;
    double quantity {};
    double unitPrice {};
};

struct Bill {
    int id {};
    std::string vendorName;
    std::string reference;
    std::string category;
    double amount {};
    std::string dueDate;
    std::string status;
    std::string notes;
};

struct Payment {
    int id {};
    std::string paymentType;
    int invoiceId {};
    int billId {};
    std::string paymentDate;
    double amount {};
    std::string method;
    std::string notes;
};

struct DashboardSnapshot {
    double openAr {};
    double openAp {};
    double invoiceVolume {};
    double billVolume {};
    int activeJobs {};
};
