from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("healthz/", views.healthz, name="healthz"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("audit/", views.audit_report, name="audit_report"),
    path("payroll/", views.payroll, name="payroll"),
    path("payroll/export/excel/", views.payroll_export_excel, name="payroll_export_excel"),
    path("payroll/export/pdf/", views.payroll_export_pdf, name="payroll_export_pdf"),
    path("payroll/<int:pk>/payslip/", views.payslip_pdf, name="payslip_pdf"),
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),
    path("payments/<int:pk>/receipt/", views.payment_receipt_pdf, name="payment_receipt_pdf"),
    path("documents/bulk-download/", views.bulk_document_download, name="bulk_document_download"),
    path("deployments/export/excel/", views.deployments_export_excel, name="deployments_export_excel"),
    path("deployments/import/excel/", views.deployments_import_excel, name="deployments_import_excel"),
    path("accounting/post/", views.post_accounting_entries, name="post_accounting_entries"),
    path("accounting/general-ledger/", views.general_ledger, name="general_ledger"),
    path("accounting/trial-balance/", views.trial_balance, name="trial_balance"),
    path("accounting/balance-sheet/", views.balance_sheet, name="balance_sheet"),
    path("accounting/income-statement/", views.income_statement, name="income_statement"),
    path("accounting/receivables-aging/", views.receivables_aging, name="receivables_aging"),
    path("accounting/reconciliation/", views.reconciliation_report, name="reconciliation_report"),
    path("accounting/reconciliation/payroll/", views.payroll_reconciliation_report, name="payroll_reconciliation_report"),
    path("accounting/reconciliation/expenses/", views.expense_reconciliation_report, name="expense_reconciliation_report"),
    path("accounting/reconciliation/payments/", views.payment_reconciliation_report, name="payment_reconciliation_report"),
    path("attendances/", views.attendances, name="attendances"),
    path("api/attendance/swipe/", views.attendance_swipe_api, name="attendance_swipe_api"),
    path("attendances/upload-roster/", views.upload_duty_roster, name="upload_duty_roster"),
    path("attendances/roster-template/", views.duty_roster_template, name="duty_roster_template"),
    path("attendances/summary/pdf/", views.attendance_summary_pdf, name="attendance_summary_pdf"),
    path("reports/", views.reports_center, name="reports_center"),
    path("reports/zonal-guard-list/", views.zonal_guard_list, name="zonal_guard_list"),
    path("reports/zone-shift-summary/", views.zone_shift_summary, name="zone_shift_summary"),
    path("reports/attendance/", views.attendance_report, name="attendance_report"),
    path("reports/assets/", views.asset_report, name="asset_report"),
    path("contracts/<int:pk>/invoice-data/", views.contract_invoice_data, name="contract_invoice_data"),
    path("clients/<int:pk>/contract-requirement-data/", views.client_contract_requirement_data, name="client_contract_requirement_data"),
    path("records/<slug:slug>/", views.record_list, name="record_list"),
    path("records/<slug:slug>/pdf/", views.record_list_pdf, name="record_list_pdf"),
    path("records/<slug:slug>/add/", views.record_create, name="record_add"),
    path("records/<slug:slug>/<int:pk>/edit/", views.record_update, name="record_edit"),
    path("records/<slug:slug>/<int:pk>/delete/", views.record_delete, name="record_delete"),
]
