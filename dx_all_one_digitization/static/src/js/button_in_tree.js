odoo.define('dx_all_one_digitization.upload.bill.mixin', function (require) {
"use strict";

    var core = require('web.core');
    var _t = core._t;

    var qweb = core.qweb;

    var DXUploadBillMixin = {

        start: function () {
            // define a unique uploadId and a callback method
            this.fileUploadID = _.uniqueId('dx_bill_file_upload');
            $(window).on(this.fileUploadID, this._onFileUploaded.bind(this));
            return this._super.apply(this, arguments);
        },

        _onAddAttachment: function (ev) {
            // Auto submit form once we've selected an attachment
            var $input = $(ev.currentTarget).find('input.o_input_file');
            if ($input.val() !== '') {
                var $binaryForm = this.$('.o_vendor_bill_dxupload form.o_form_binary_form');
                $binaryForm.submit();
            }
        },

        _onFileUploaded: function () {
            // Callback once attachment have been created, create a bill with attachment ids
            var self = this;
            var attachments = Array.prototype.slice.call(arguments, 1);
            // Get id from result
            var attachent_ids = attachments.reduce(function(filtered, record) {
                if (record.id) {
                    filtered.push(record.id);
                }
                return filtered;
            }, []);
            return this._rpc({
                model: 'invoice.digitalize',
                method: 'dx_create_invoice_from_attachment',
                args: ["", attachent_ids],
                context: this.initialState.context,
            }).then(function(result) {
                self.do_action(result);
            }).catch(function () {
                // Reset the file input, allowing to select again the same file if needed
                self.$('.o_vendor_bill_dxupload .o_input_file').val('');
            });
        },

        _onUpload: function (event) {
            var self = this;
            // If hidden upload form don't exists, create it
            var $formContainer = this.$('.o_content').find('.o_vendor_bill_dxupload');
            if (!$formContainer.length) {
                $formContainer = $(qweb.render('dx_all_one_digitization.BillsHiddenUploadForm', {widget: this}));
                $formContainer.appendTo(this.$('.o_content'));
            }
            // Trigger the input to select a file
            this.$('.o_vendor_bill_dxupload .o_input_file').click();
        },
    }
    return DXUploadBillMixin;
});


odoo.define('dxaccount.bills.tree', function (require) {
"use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var UploadBillMixin = require('dx_all_one_digitization.upload.bill.mixin');
    var viewRegistry = require('web.view_registry');

    var BillsListController = ListController.extend(UploadBillMixin, {
        buttons_template: 'DXBillsListView.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_button_dxupload_bill': '_onUpload',
            'change .o_vendor_bill_dxupload .o_form_binary_form': '_onAddAttachment',
        }),
    });

    var BillsListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: BillsListController,
        }),
    });

    viewRegistry.add('dxaccount_tree', BillsListView);
});

