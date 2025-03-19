import frappe
from frappe import _
from frappe.utils import flt, getdate

@frappe.whitelist()
def calculate_commission(docname):
    """محاسبه کمیسیون و کسورات برای Sales Target Assignment"""
    doc = frappe.get_doc("Sales Target Assignment", docname)
    if doc.doctype != "Sales Target Assignment":
        return

    # تنظیم بازه زمانی
    period_start = getdate(doc.period_start) if doc.period_start else None
    period_end = getdate(doc.period_end) if doc.period_end else None
    if doc.period_type == "Gregorian Month" and doc.gregorian_month and doc.gregorian_year:
        period_start, period_end = get_gregorian_period(doc.gregorian_month, doc.gregorian_year)

    # محاسبه کمیسیون‌ها و کسورات
    total_commission = 0.0
    total_deduction = 0.0

    if doc.include_brand_commission and doc.use_brand_target:
        total_commission += calculate_brand_target(doc, period_start, period_end)
    if doc.include_item_group_commission and doc.use_item_group_target:
        total_commission += calculate_item_group_target(doc, period_start, period_end)
    if doc.include_supplier_commission and doc.use_supplier_target:
        total_commission += calculate_supplier_target(doc, period_start, period_end)
    if doc.include_sales_amount_commission and doc.use_sales_amount_target:
        total_commission += calculate_sales_amount_target(doc, period_start, period_end)
    if doc.include_sales_quantity_commission and doc.use_sales_quantity_target:
        total_commission += calculate_sales_quantity_target(doc, period_start, period_end)
    if doc.include_successful_invoices_commission and doc.use_successful_invoices_target:
        total_commission += calculate_successful_invoices_target(doc, period_start, period_end)
    if doc.include_deductions and doc.use_deductions:
        total_deduction += calculate_deductions(doc, period_start, period_end)

    # به‌روزرسانی کمیسیون نهایی
    doc.final_commission = flt(total_commission - total_deduction, 2)
    doc.save()
    frappe.msgprint(_("Commission calculated successfully!"))

def get_gregorian_period(month, year):
    """محاسبه بازه زمانی برای ماه گرگوری"""
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
    }
    month_num = month_map.get(month)
    start_date = frappe.utils.get_first_day(f"{year}-{month_num}-01")
    end_date = frappe.utils.get_last_day(start_date)
    return start_date, end_date

def get_sales_invoices(sales_person, start_date, end_date):
    """استخراج فاکتورهای فروش"""
    filters = {
        "sales_person": sales_person,
        "docstatus": 1,
        "posting_date": ["between", [start_date, end_date]]
    }
    return frappe.get_all("Sales Invoice", filters=filters, fields=["name", "grand_total", "posting_date", "status"])

def calculate_brand_target(doc, start_date, end_date):
    total_commission = 0.0
    targets = doc.get("brand_targets", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for target in targets:
        calculated_value = sum(
            flt(inv.grand_total) for inv in invoices
            if frappe.db.exists("Sales Invoice Item", {"parent": inv.name, "brand": target.brand})
        )
        coefficient = flt(calculated_value / target.target_value, 2) if target.target_value else 0.0
        row_commission = flt(calculated_value * coefficient, 2)
        total_commission += row_commission
    return total_commission

def calculate_item_group_target(doc, start_date, end_date):
    total_commission = 0.0
    targets = doc.get("item_group_targets", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for target in targets:
        calculated_value = sum(
            flt(inv.grand_total) for inv in invoices
            if frappe.db.exists("Sales Invoice Item", {"parent": inv.name, "item_group": target.item_group})
        )
        coefficient = flt(calculated_value / target.target_value, 2) if target.target_value else 0.0
        row_commission = flt(calculated_value * coefficient, 2)
        total_commission += row_commission
    return total_commission

def calculate_supplier_target(doc, start_date, end_date):
    total_commission = 0.0
    targets = doc.get("supplier_targets", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for target in targets:
        calculated_value = sum(
            flt(inv.grand_total) for inv in invoices
            if frappe.db.get_value("Sales Invoice", inv.name, "supplier") == target.supplier
        )
        coefficient = flt(calculated_value / target.target_value, 2) if target.target_value else 0.0
        row_commission = flt(calculated_value * coefficient, 2)
        total_commission += row_commission
    return total_commission

def calculate_sales_amount_target(doc, start_date, end_date):
    total_commission = 0.0
    targets = doc.get("sales_amount_targets", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for target in targets:
        calculated_value = sum(flt(inv.grand_total) for inv in invoices)
        coefficient = flt(calculated_value / target.target_value, 2) if target.target_value else 0.0
        row_commission = flt(calculated_value * coefficient, 2)
        total_commission += row_commission
    return total_commission

def calculate_sales_quantity_target(doc, start_date, end_date):
    total_commission = 0.0
    targets = doc.get("sales_quantity_targets", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for target in targets:
        calculated_value = sum(
            flt(frappe.db.get_value("Sales Invoice Item", {"parent": inv.name}, "qty") or 0)
            for inv in invoices
        )
        coefficient = flt(calculated_value / target.target_value, 2) if target.target_value else 0.0
        row_commission = flt(calculated_value * coefficient, 2)
        total_commission += row_commission
    return total_commission

def calculate_successful_invoices_target(doc, start_date, end_date):
    total_commission = 0.0
    targets = doc.get("successful_invoices_targets", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for target in targets:
        calculated_value = len([inv for inv in invoices if inv.status == "Paid"])
        coefficient = flt(calculated_value / target.target_value, 2) if target.target_value else 0.0
        row_commission = flt(calculated_value * coefficient, 2)
        total_commission += row_commission
    return total_commission

def calculate_deductions(doc, start_date, end_date):
    total_deduction = 0.0
    deductions = doc.get("deductions", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for deduction in deductions:
        calculated_value = sum(flt(inv.grand_total) for inv in invoices if inv.status != "Paid")
        coefficient = flt(calculated_value / deduction.deduction_value, 2) if deduction.deduction_value else 0.0
        row_deduction = flt(deduction.deduction_amount * (1 - coefficient), 2) if coefficient < 1 else 0.0
        total_deduction += row_deduction
    return total_deduction

def calculate_commission_after_save(doc, method):
    """محاسبه کمیسیون پس از ذخیره سند"""
    if doc.doctype != "Sales Target Assignment":
        return

    # تنظیم بازه زمانی
    period_start = getdate(doc.period_start) if doc.period_start else None
    period_end = getdate(doc.period_end) if doc.period_end else None
    if doc.period_type == "Gregorian Month" and doc.gregorian_month and doc.gregorian_year:
        period_start, period_end = get_gregorian_period(doc.gregorian_month, doc.gregorian_year)

    # محاسبه کمیسیون‌ها و کسورات
    total_commission = 0.0
    total_deduction = 0.0

    if doc.include_brand_commission and doc.use_brand_target:
        total_commission += calculate_brand_target(doc, period_start, period_end)
    if doc.include_item_group_commission and doc.use_item_group_target:
        total_commission += calculate_item_group_target(doc, period_start, period_end)
    if doc.include_supplier_commission and doc.use_supplier_target:
        total_commission += calculate_supplier_target(doc, period_start, period_end)
    if doc.include_sales_amount_commission and doc.use_sales_amount_target:
        total_commission += calculate_sales_amount_target(doc, period_start, period_end)
    if doc.include_sales_quantity_commission and doc.use_sales_quantity_target:
        total_commission += calculate_sales_quantity_target(doc, period_start, period_end)
    if doc.include_successful_invoices_commission and doc.use_successful_invoices_target:
        total_commission += calculate_successful_invoices_target(doc, period_start, period_end)
    if doc.include_deductions and doc.use_deductions:
        total_deduction += calculate_deductions(doc, period_start, period_end)

    # به‌روزرسانی کمیسیون نهایی
    doc.final_commission = flt(total_commission - total_deduction, 2)
    doc.save()