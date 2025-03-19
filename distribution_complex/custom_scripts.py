import frappe
from frappe import _
from frappe.utils import flt, getdate

@frappe.whitelist()
def calculate_commission(docname):
    """محاسبه کمیسیون و کسورات برای Sales Target Assignment"""
    doc = frappe.get_doc("Sales Target Assignment", docname)
    if doc.doctype != "Sales Target Assignment":
        return

    frappe.log_error(f"Document: {doc.as_dict()}", "Commission Calculation Debug")

    # تنظیم بازه زمانی
    period_start = getdate(doc.period_start) if doc.period_start else None
    period_end = getdate(doc.period_end) if doc.period_end else None
    if doc.period_type == "Gregorian Month" and doc.gregorian_month and doc.gregorian_year:
        period_start, period_end = get_gregorian_period(doc.gregorian_month, doc.gregorian_year)
    frappe.log_error(f"Period: {period_start} to {period_end}", "Commission Calculation Debug")

    # محاسبه کمیسیون‌ها و کسورات
    total_commission = 0.0
    total_deduction = 0.0

    # پاک کردن جداول محاسباتی قبلی
    doc.brand_targets_calculations = []
    doc.item_group_targets_calculations = []

    if doc.include_brand_commission and doc.use_brand_target:
        brand_commission = calculate_brand_target(doc, period_start, period_end)
        doc.brand_commission = brand_commission
        total_commission += brand_commission
    else:
        doc.brand_commission = 0.0
        frappe.log_error("Brand commission not included", "Commission Calculation Debug")

    if doc.include_item_group_commission and doc.use_item_group_target:
        item_group_commission = calculate_item_group_target(doc, period_start, period_end)
        doc.item_group_commission = item_group_commission
        total_commission += item_group_commission
    else:
        doc.item_group_commission = 0.0
        frappe.log_error("Item group commission not included", "Commission Calculation Debug")

    if doc.include_supplier_commission and doc.use_supplier_target:
        supplier_commission = calculate_supplier_target(doc, period_start, period_end)
        doc.supplier_commission = supplier_commission
        total_commission += supplier_commission
    else:
        doc.supplier_commission = 0.0

    if doc.include_sales_amount_commission and doc.use_sales_amount_target:
        sales_amount_commission = calculate_sales_amount_target(doc, period_start, period_end)
        doc.sales_amount_commission = sales_amount_commission
        total_commission += sales_amount_commission
    else:
        doc.sales_amount_commission = 0.0

    if doc.include_sales_quantity_commission and doc.use_sales_quantity_target:
        sales_quantity_commission = calculate_sales_quantity_target(doc, period_start, period_end)
        doc.sales_quantity_commission = sales_quantity_commission
        total_commission += sales_quantity_commission
    else:
        doc.sales_quantity_commission = 0.0

    if doc.include_successful_invoices_commission and doc.use_successful_invoices_target:
        successful_invoices_commission = calculate_successful_invoices_target(doc, period_start, period_end)
        doc.successful_invoices_commission = successful_invoices_commission
        total_commission += successful_invoices_commission
    else:
        doc.successful_invoices_commission = 0.0

    if doc.include_deductions and doc.use_deductions:
        total_deduction = calculate_deductions(doc, period_start, period_end)
        doc.total_deductions = total_deduction
    else:
        doc.total_deductions = 0.0

    # محاسبه و محدود کردن کمیسیون نهایی
    final_commission = flt(total_commission - total_deduction, 9)
    MAX_COMMISSION = 999999999999.999999999
    MIN_COMMISSION = -999999999999.999999999
    
    if final_commission > MAX_COMMISSION:
        final_commission = MAX_COMMISSION
        frappe.log_error("Final Commission capped at max", "Commission Calculation Debug")
    elif final_commission < MIN_COMMISSION:
        final_commission = MIN_COMMISSION
        frappe.log_error("Final Commission capped at min", "Commission Calculation Debug")

    frappe.log_error(f"Total Commission: {total_commission}, Total Deduction: {total_deduction}, Final Commission: {final_commission}", "Commission Calculation Debug")

    # به‌روزرسانی سند
    doc.final_commission = final_commission
    doc.db_update()
    frappe.db.commit()
    frappe.msgprint(_("Commission calculated successfully for {0}").format(docname))

def get_gregorian_period(month, year):
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
    }
    month_num = month_map.get(month)
    start_date = frappe.utils.get_first_day(f"{year}-{month_num}-01")
    end_date = frappe.utils.get_last_day(start_date)
    return start_date, end_date

def get_sales_invoices(sales_person, start_date, end_date):
    filters = {
        "sales_person": sales_person,
        "docstatus": 1,
        "posting_date": ["between", [start_date, end_date]]
    }
    invoices = frappe.get_all("Sales Invoice", filters=filters, fields=["name", "grand_total", "posting_date", "status"])
    frappe.log_error(f"Invoices found: {len(invoices)} for {sales_person}", "Commission Calculation Debug")
    return invoices

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
        # استفاده از reward_value به جای ضرب ساده
        row_commission = flt(target.reward_value * coefficient, 9) if coefficient >= flt(target.min_achievement / 100, 2) else 0.0
        total_commission += row_commission
        # اضافه کردن به جدول محاسبات
        doc.append("brand_targets_calculations", {
            "brand": target.brand,
            "target_value": target.target_value,
            "actual_value": calculated_value,
            "commission": row_commission
        })
        frappe.log_error(f"Brand {target.brand}: calculated_value={calculated_value}, coefficient={coefficient}, row_commission={row_commission}", "Commission Calculation Debug")
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
        # استفاده از reward_value
        row_commission = flt(target.reward_value * coefficient, 9) if coefficient >= flt(target.min_achievement / 100, 2) else 0.0
        total_commission += row_commission
        # اضافه کردن به جدول محاسبات
        doc.append("item_group_targets_calculations", {
            "item_group": target.item_group,
            "target_value": target.target_value,
            "actual_value": calculated_value,
            "commission": row_commission
        })
        frappe.log_error(f"Item Group {target.item_group}: calculated_value={calculated_value}, coefficient={coefficient}, row_commission={row_commission}", "Commission Calculation Debug")
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
        row_commission = flt(calculated_value * coefficient, 9)
        total_commission += min(row_commission, 1000000.0)
        frappe.log_error(f"Supplier {target.supplier}: calculated_value={calculated_value}, coefficient={coefficient}, row_commission={row_commission}", "Commission Calculation Debug")
    return total_commission

def calculate_sales_amount_target(doc, start_date, end_date):
    total_commission = 0.0
    targets = doc.get("sales_amount_targets", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for target in targets:
        calculated_value = sum(flt(inv.grand_total) for inv in invoices)
        coefficient = flt(calculated_value / target.target_value, 2) if target.target_value else 0.0
        row_commission = flt(calculated_value * coefficient, 9)
        total_commission += min(row_commission, 1000000.0)
        frappe.log_error(f"Sales Amount: calculated_value={calculated_value}, coefficient={coefficient}, row_commission={row_commission}", "Commission Calculation Debug")
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
        row_commission = flt(calculated_value * coefficient, 9)
        total_commission += min(row_commission, 1000000.0)
        frappe.log_error(f"Sales Quantity: calculated_value={calculated_value}, coefficient={coefficient}, row_commission={row_commission}", "Commission Calculation Debug")
    return total_commission

def calculate_successful_invoices_target(doc, start_date, end_date):
    total_commission = 0.0
    targets = doc.get("successful_invoices_targets", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for target in targets:
        calculated_value = len([inv for inv in invoices if inv.status == "Paid"])
        coefficient = flt(calculated_value / target.target_value, 2) if target.target_value else 0.0
        row_commission = flt(calculated_value * coefficient, 9)
        total_commission += min(row_commission, 1000000.0)
        frappe.log_error(f"Successful Invoices: calculated_value={calculated_value}, coefficient={coefficient}, row_commission={row_commission}", "Commission Calculation Debug")
    return total_commission

def calculate_deductions(doc, start_date, end_date):
    total_deduction = 0.0
    deductions = doc.get("deductions", [])
    invoices = get_sales_invoices(doc.sales_person, start_date, end_date)
    for deduction in deductions:
        calculated_value = sum(flt(inv.grand_total) for inv in invoices if inv.status != "Paid")
        coefficient = flt(calculated_value / deduction.deduction_value, 2) if deduction.deduction_value else 0.0
        row_deduction = flt(deduction.deduction_amount * (1 - coefficient), 9) if coefficient < 1 else 0.0
        total_deduction += min(row_deduction, 1000000.0)
        frappe.log_error(f"Deduction: calculated_value={calculated_value}, coefficient={coefficient}, row_deduction={row_deduction}", "Commission Calculation Debug")
    return total_deduction