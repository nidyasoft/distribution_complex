frappe.ui.form.on("Sales Target Assignment", {
    refresh: function(frm) {
        frm.add_custom_button(__("Commission Calculation"), function() {
            frappe.call({
                method: "distribution_complex.custom_scripts.calculate_commission",
                args: {
                    docname: frm.doc.name
                },
                callback: function(r) {
                    if (!r.exc) {  // بررسی عدم وجود خطا
                        frappe.msgprint(__("Commission calculated successfully!"));
                        frm.reload_doc();
                    }
                }
            });
        });
    }
});