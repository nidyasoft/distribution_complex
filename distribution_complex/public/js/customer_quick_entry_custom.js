frappe.provide("frappe.ui.form");

// بازنویسی کامل کلاس برای نادیده گرفتن اسکریپت اصلی
frappe.ui.form.ContactAddressQuickEntryForm = class ContactAddressQuickEntryForm extends frappe.ui.form.QuickEntryForm {
    constructor(doctype, after_insert, init_callback, doc, force) {
        super(doctype, after_insert, init_callback, doc, force);
        this.skip_redirect_on_error = true;
    }

    render_dialog() {
        this.mandatory = this.mandatory.concat(this.get_variant_fields());
        super.render_dialog();
    }

    insert() {
        /**
         * Using alias fieldnames because the doctype definition define "email_id" and "mobile_no" as readonly fields.
         * Therefor, resulting in the fields being "hidden".
         */
        const map_field_names = {
            email_address: "email_id",
            mobile_number: "mobile_no",
        };

        Object.entries(map_field_names).forEach(([fieldname, new_fieldname]) => {
            this.dialog.doc[new_fieldname] = this.dialog.doc[fieldname];
            delete this.dialog.doc[fieldname];
        });

        return super.insert();
    }

    get_variant_fields() {
        var variant_fields = [
            {
                fieldtype: "Section Break",
                label: __("Primary Contact Details"),
                collapsible: 1,
            },
            {
                label: __("Email Id"),
                fieldname: "email_address",
                fieldtype: "Data",
                options: "Email",
            },
            {
                fieldtype: "Column Break",
            },
            {
                label: __("Mobile Number"),
                fieldname: "mobile_number",
                fieldtype: "Data",
            },
            {
                fieldtype: "Section Break",
                label: __("Primary Address Details"),
                collapsible: 1,
            },
            {
                label: __("Address Line 1"),
                fieldname: "address_line1",
                fieldtype: "Data",
            },
            {
                label: __("Address Line 2"),
                fieldname: "address_line2",
                fieldtype: "Data",
            },
            {
                label: __("ZIP Code"),
                fieldname: "pincode",
                fieldtype: "Data",
            },
            {
                fieldtype: "Column Break",
            },
            {
                label: __("Country"),
                fieldname: "country",
                fieldtype: "Link",
                options: "Country",
                onchange: () => {
                    this.dialog.set_value("state", ""); // خالی کردن Province
                    this.dialog.set_value("city", "");  // خالی کردن City
                    this.dialog.fields_dict.state.refresh();
                }
            },
            {
                label: __("Province"),
                fieldname: "state",
                fieldtype: "Link",
                options: "Province",
                get_query: () => {
                    return {
                        filters: {
                            "country": this.dialog.get_value("country") || ""
                        }
                    };
                },
                onchange: () => {
                    this.dialog.set_value("city", ""); // خالی کردن City
                    this.dialog.fields_dict.city.refresh();
                }
            },
            {
                label: __("City"),
                fieldname: "city",
                fieldtype: "Link",
                options: "City",
                get_query: () => {
                    return {
                        filters: {
                            "province": this.dialog.get_value("state") || ""
                        }
                    };
                }
            },
            {
                label: __("Customer POS Id"),
                fieldname: "customer_pos_id",
                fieldtype: "Data",
                hidden: 1,
            },
        ];

        return variant_fields;
    }
};

// بازنویسی CustomerQuickEntryForm برای استفاده از کلاس سفارشی
frappe.ui.form.CustomerQuickEntryForm = frappe.ui.form.ContactAddressQuickEntryForm;
