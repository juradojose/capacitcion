odoo.define('xmls.to.invoices', function (require) {
"use strict";
var core = require('web.core');
var Model = require('web.Model');
var FieldChar = core.form_widget_registry.get('char');
var _t = require('web.translation')._t;

var attachXmlsWizard = FieldChar.extend({
    template: 'attach_xmls_template',

    start: function(){
        this.$el.parent().parent().find('.o_form_sheet').css('padding', '0');
        this.files = {};
        this.loading = false;
        this.invoice_ids = [];
        var self = this;
        var handler = this.$el.siblings("#dragandrophandler");
        var content = this.$el.siblings("#filescontent");
        var input = this.$el.siblings("#files");
        var footer = this.$el.siblings('#dragfooter');

        // events drag and drop on the div handler
        handler.on('dragenter', function (e){
            e.stopPropagation();
            e.preventDefault();
        });
        handler.on('dragover', function (e){
            e.stopPropagation();
            e.preventDefault();
            $(this).removeClass('dnd_out').addClass('dnd_inside');
        });
        handler.on('drop', function (e){
            e.preventDefault();
            self.handleFileUpload(e.originalEvent.dataTransfer.files);
        });
        // events drag and drop inside the page
        $(document).on('dragenter', function (e) {
            e.stopPropagation();
            e.preventDefault();
            handler.removeClass('dnd_inside dnd_normal').addClass('dnd_out');
            handler.parent().find('.alert-warning.drag-alert').remove();
        });
        $(document).on('dragover', function (e) {
            e.stopPropagation();
            e.preventDefault();
        });
        $(document).on('drop', function (e) {
            e.stopPropagation();
            e.preventDefault();
            handler.removeClass('dnd_out dnd_inside').addClass('dnd_normal');
        });
        // event when the mouse with files leave the web page
        $(document).on('dragleave', function (e) {
            e.stopPropagation();
            e.preventDefault();
            if(!e.originalEvent.clientX && !e.originalEvent.clientY){
                handler.removeClass('dnd_out dnd_inside').addClass('dnd_normal');
            }
        });

        // Opens dialog box to attach files
        handler.click(function(e){
            input.val('');
            input.click();
        });
        input.on('change', function(e){
            if($(this)[0].files.length > 0){
                handler.parent().find('.alert-warning.drag-alert').remove();
                self.handleFileUpload($(this)[0].files);
            };
        });
        // Executes the respective actions for each case in the exceptions after press button save
        footer.parent().on('click', '.drag-alert-button', function(e){
            var type = $(this).attr('tag');
            var alertobj = $(this).parent().parent();
            var filekey = alertobj.attr('tag');
            if(type === 'remove'){
                self.removeWrongAlerts(alertobj, filekey, true);
            }else if(type === 'supplier'){
                self.sendErrorToServer(self.alerts_in_queue.alertHTML[filekey].xml64, filekey, 'create_partner');
            }else if(type === 'tryagain'){
                self.sendErrorToServer(self.alerts_in_queue.alertHTML[filekey].xml64, filekey, 'check_xml');
            }
        });
        // Removes the file with a click over the respective file content in page
        content.on('click', '.xml_cont_hover', function(e){
            delete self.files[$(this).attr('title')];
            $(this).animate({'opacity': '0'}, 500, function(e){
                $(this).remove();
            });
        });

        footer.find('button#save').click(function(e){
            e.preventDefault();
            handler.parent().find('.alert-warning.drag-alert').remove();
            if(Object.keys(self.files).length <= 0){
                self.do_warn(_t('There is no files selected'));
            }else if(Object.keys(self.files).length > 1 && self.getParent().dataset.get_context().eval()['active_ids']){
                self.do_warn(_t('You cannot attach more than one xml to an invoice'));
            }else{
                handler.hide();
                footer.find('button#save').attr('disabled', true);
                content.find('.xml_cont').removeClass('xml_cont_hover');
                self.readFiles(self.files);
            }
        });
        // Shows you the invoices created in a treeview
        footer.find('button#show').click(function(e){
            e.preventDefault();
            if(self.invoice_ids.length > 0){
                var domain = [['id', 'in', self.invoice_ids]];
                return self.do_action({
                    name: _t('Supplier Invoices'),
                    view_type: 'list',
                    view_mode: 'list,form',
                    res_model: 'account.invoice',
                    type: 'ir.actions.act_window',
                    views: [[false, 'list'], [false, 'form']],
                    targe: 'current',
                    domain: domain,
                });
            }
        });
        // Closes the wizard view
        footer.find('button#close').click(function(e){
            e.preventDefault();
            self.do_action({'type': 'ir.actions.act_window_close'});
        });
    },
    handleFileUpload: function(files){
        /* Creates the file element in the DOM and shows alerts wheter the extension
        file is not the correct one or the file is already uploaded */
        var self = this;
        if(!self.loading){
            self.loading = true;
            var files_used = [];
            var wrong_files = [];
            $.each(files, function(i, file){
                if(file.type != 'text/xml'){
                    wrong_files.push(file.name);
                }else if(self.files.hasOwnProperty(file.name)){
                    files_used.push(file.name);
                }else{
                    self.files[file.name] = file;
                    var newelement = $('<div class="xml_cont xml_cont_hover" title="'+file.name+'">\
                        <img class="xml_img" height="100%" align="left" hspace="5"/>\
                        <p>'+file.name+'</p><div class="remove_xml">&times;</div>\
                    </div>').css('opacity', '0');
                    self.$el.siblings("#filescontent").append(newelement);
                    newelement.animate({'opacity': '1'}, 500);
                }
            });
            var alert_message = '';
            if(wrong_files.length > 0){
                alert_message += _t('<strong>Info!</strong> You only can upload XML files.<br>') +
                    wrong_files.join(" <b style='font-size:15px;font-wight:900;'>&#8226;</b> ");
            }
            if(files_used.length > 0){
                if(alert_message !== ''){alert_message += '<br>';};
                alert_message += _t('<strong>Info!</strong> Some files are already loaded.<br>') +
                    files_used.join(" <b style='font-size:15px;font-wight:900;'>&#8226;</b> ");
            }
            if(alert_message !== ''){
                self.$el.siblings("#dragandrophandler").after('<div class="alert alert-warning drag-alert">\
                    <a href="#" class="close" data-dismiss="alert" aria-label="close">&times;</a>' + alert_message + '\
                </div>');
            }
            self.loading = false;
        }else{
            self.do_warn(_t('There are files uploading'));
        }
    },
    readFiles: function(files){
        /* Convert the file object uploaded to a base64 string */
        var self = this;
        var readfiles = {};
        $.each(files, function(key, file){
            var fr = new FileReader();
            fr.onload = function(){
                readfiles[key] = fr.result;
                if(Object.keys(files).length === Object.keys(readfiles).length){
                    self.sendFileToServer(readfiles);
                }
            };
            fr.readAsDataURL(file);
        });
    },
    sendFileToServer: function(files){
        /* Sends each base64 file string to the back-end server to create the invoices */
        var self = this;
        var wrongfiles = {};
        var countfiles = 0;
        $.each(files, function(key, xml64){
            (new Model("wizard.load.xml")).call('check_xml', {
                'xml64': xml64, 'key': key, 'context': self.getParent().dataset.get_context()}).then(function (data) {
                if(!data[key]){
                    wrongfiles[key] = data;
                }else{
                    self.invoice_ids.push(data.invoice_id);
                    self.createdCorrectly(key);
                }
                countfiles += 1;
                if(Object.keys(files).length === countfiles && Object.keys(wrongfiles).length > 0){
                    self.handleFileWrong(wrongfiles);
                }
                if(Object.keys(files).length === countfiles && Object.keys(wrongfiles).length === 0){
                    self.correctFinalRegistry();
                }
            });
        });
    },
    createdCorrectly: function(key){
        /* Colors the files content in the DOM when the invoice is created with that XML */
        var self = this;
        var alert = self.$el.siblings("#filescontent").find('div[title="'+key+'"]');
        alert.addClass('xml_correct');
        alert.find('div.remove_xml').html('&#10004;');
    },
    handleFileWrong: function(wrongfiles){
        /* Saves the exceptions occurred in the invoices creation */
        this.alerts_in_queue = {'alertHTML': {}, total: Object.keys(wrongfiles).length};
        var self = this;
        $.each(wrongfiles, function(key, file){
            var alert_parts = self.prepareWrongAlert(key, file);

            var alertelement = $('<div tag="'+ key +'" class="alert alert-'+ alert_parts.alerttype +' drag-alert">\
                ' + alert_parts.errors + '<div>' + alert_parts.buttons + _t('<span>Wrong File: <span class="index-alert"></span>') + '/' + self.alerts_in_queue.total + ' \
                <b style="font-size:15px;font-wight:900;">&#8226;</b> ' + key + '</span></div></div>');
            self.alerts_in_queue.alertHTML[key] = {'alert': alertelement, 'xml64': file['xml64']};
            if(Object.keys(wrongfiles).length === Object.keys(self.alerts_in_queue.alertHTML).length){
                self.nextWrongAlert();
            }
        });
    },
    prepareWrongAlert(key, data){
        /* Prepares the buttons and message the invoice alert exception will contain */
        var self = this;
        var errors = '';
        var buttons = '';
        var able_buttons = [];
        var alerttype;
        if('error' in data){
            [errors, able_buttons] = self.wrongMsgServer(data, errors, able_buttons);
            alerttype = 'danger';
        }else{
            [errors, able_buttons] = self.wrongMsgXml(data, errors, able_buttons);
            alerttype = 'info';
        }
        if(able_buttons.includes('remove')){
            buttons += _t('<button class="drag-alert-button" tag="remove">Remove XML</button>');
        }else if(able_buttons.includes('supplier') && !able_buttons.includes('remove')){
            buttons += _t('<button class="drag-alert-button" tag="remove">Remove XML</button>');
            if(data.allow_create_supplier === true){
                buttons += _t('<button class="drag-alert-button" tag="supplier">Create Supplier</button>');
            }
        }else if(able_buttons.includes('tryagain')){
            buttons += _t('<button class="drag-alert-button" tag="remove">Remove XML</button>') +
                _t('<button class="drag-alert-button" tag="tryagain">Try again</button>');
        }
        return {'errors': errors, 'buttons': buttons, 'alerttype': alerttype};
    },
    wrongMsgServer: function(data, errors, able_buttons){
        /* Prepares the message to the server error */
        var typemsg = {'CheckXML': _t('Error checking XML data.'), 'CreatePartner': _t('Error creating supplier.'), 'CreateInvoice': _t('Error creating invoice.')}
        errors += '<div><span level="2">'+ data.error[0] +'</span> <span level="1">'+ data.error[1] +'</span>.<br>'+ typemsg[data.where] +'</div>';
        able_buttons.push('tryagain');
        return [errors, able_buttons];
    },
    wrongMsgXml: function(file, errors, able_buttons){
        /* Prepares the message to the xml errors */
        $.each(file, function(ikey, val){
            if(ikey === 'supplier'){
                errors += _t('<div><span level="1">The XML Supplier</span> was not found: <span level="2">') + val + '</span>.</div>';
                able_buttons.push('supplier');
            }else if(ikey === 'rfc'){
                errors += _t('<div><span level="1">The XML Receptor RFC</span> does not match with <span level="1">your Company RFC</span>: ') +
                    _t('XML Receptor RFC: <span level="2">') + val[0] + _t(', </span> Your Company RFC: <span level="2">') + val[1] + '</span></div>';
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'currency'){
                errors += _t('<div><span level="1">The XML Currency</span> <span level="2">') + val + _t('</span> was not found or is disabled.</div>');
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'taxes'){
                errors += _t('<div><span level="1">Some taxes</span> do not exist for purchases: <span level="2">') + val.join(', ') + '</span>.</div>';
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'signed'){
                errors += _t('<div><span level="1">UUID</span> not found in the XML.</div>');
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'cancel'){
                errors += _t('<div><span level="1">The XML state</span> is CANCELED in the SAT system.</div>');
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'discount'){
                errors += _t('<div><span level="1">Unable to generate invoices with discounts from an XML with version 3.2.</span>You can create the invoice manually and then attach the xml.</div>');
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'folio'){
                errors += _t('<div><span level="1">The XML Folio</span> does not match with <span level="1">Supplier Invoice Number</span>: ') +
                    _t('XML Folio: <span level="2">') + val[0] + _t(', </span> Supplier invoice number: <span level="2">') + val[1] + '</span></div>';
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'rfc_supplier'){
                errors += _t('<div><span level="1">The XML Emitter RFC</span> does not match with <span level="1">Customer RFC</span>: ') +
                    _t('XML Emitter RFC: <span level="2">') + val[0] + _t(', </span> Customer RFC: <span level="2">') + val[1] + '</span></div>';
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'amount'){
                errors += _t('<div><span level="1">The XML amount total</span> does not match with <span level="1">Invoice total</span>: ') +
                    _t('XML amount total: <span level="2">') + val[0] + _t(', </span> Invoice Total: <span level="2">') + val[1] + '</span></div>';
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'uuid_duplicate'){
                errors += _t('<div><span level="1">The XML UUID</span> belong to other invoice. <span level="1">Partner: </span>') + val[0] + _t('<span level="1"> Reference: </span>') + val[1] +'</div>';
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'reference'){
                errors += _t('<div><span level="1">The invoice reference</span> belong to other invoice of same partner. <span level="1">Partner: </span>') + val[0] + _t('<span level="1"> Reference: </span>') + val[1] +'</div>';
                if(!able_buttons.includes('remove')){able_buttons.push('remove');};
            }else if(ikey === 'nothing'){
                errors += _t('<div><strong>Info!</strong> XML data could not be read correctly.</div>');
                able_buttons.push('remove');
            }
        })
        return [errors, able_buttons];
    },
    sendErrorToServer: function(xml64, key, function_def){
        /* Sends again the base64 file string to the server to tries to create the invoice, or
        sends the partner data to create him if does not exist */
        var self = this;
        (new Model("wizard.load.xml")).call(function_def, {'xml64': xml64, 'key': key, 'context': self.getParent().dataset.get_context()}).then(function (data) {
            var alertobj = self.$el.siblings("#dragandrophandler").parent().find('div[tag="'+key+'"].alert.drag-alert');
            if(data[key]){
                self.invoice_ids.push(data.invoice_id);
                self.createdCorrectly(key);
                self.removeWrongAlerts(alertobj, key, false);
            }else{
                var alert_parts = self.prepareWrongAlert(key, data);
                var footer = alertobj.find('div:last-child').find('span:not(.index-alert)');
                alertobj.removeClass('alert-danger alert-info').addClass('alert-'+alert_parts.alerttype);
                alertobj.html(alert_parts.errors + '<div>' + alert_parts.buttons + '</div>');
                alertobj.find('div:last-child').append(footer);
            }
        });
    },
    removeWrongAlerts: function(alertobj, filekey, removefile){
        /* Removes the current error alert to continue with the others */
        var self = this;
        alertobj.slideUp(500, function(){
            delete self.alerts_in_queue.alertHTML[filekey];
            if(removefile){
                delete self.files[filekey];
                self.$el.siblings("#filescontent").find('div[title="'+filekey+'"]').animate({'opacity': '0'}, 500, function(e){
                    $.when($(this).remove()).done(function(){
                        self.continueAlert(alertobj);
                    });
                });
            }else{
                self.continueAlert(alertobj);
            }
        });
    },
    continueAlert: function(object){
        /* After the error alert is removed, execute the next actions
        (Next error alert, Restarts to attach more files, or Shows the final success alert) */
        var self = this;
        $.when(object.remove()).done(function(){
            if(Object.keys(self.alerts_in_queue.alertHTML).length > 0){
                self.nextWrongAlert();
            }else{
                if(Object.keys(self.files).length === 0){
                    self.restart();
                }else{
                    self.correctFinalRegistry();
                }
            }
        });
    },
    nextWrongAlert: function(){
        /* Shows the next error alert */
        var self = this;
        var keys = Object.keys(self.alerts_in_queue.alertHTML);
        var alert = self.alerts_in_queue.alertHTML[keys[0]].alert.hide();
        alert.find('div:last-child').find('.index-alert').html(self.alerts_in_queue.total - (keys.length - 1));
        self.$el.siblings("#dragandrophandler").after(alert);
        alert.slideDown(500);
    },
    restart: function(){
        /* Restarts all the variables and restores all the DOM element to attach more new files */
        this.files = {};
        this.invoice_ids = [];
        this.loading = false;
        this.alerts_in_queue = {};
        this.$el.siblings("#dragandrophandler").show();
        this.$el.siblings("#filescontent").html('');
        this.$el.siblings("#files").val('');
        this.$el.siblings('#dragfooter').find('button#save').attr('disabled', false);
        this.$el.siblings('#dragandrophandler').parent().find('div.alert').remove();
        this.$el.siblings('#dragfooter').find('button#show').hide();
    },
    correctFinalRegistry: function(){
        /* Shows the final success alert and the button to see the invoices created */
        var self = this;
        var msg = _t('Your invoices were created correctly')
        if(self.getParent().dataset.get_context().eval()['active_ids']){
            msg = _t('The XML is attached correctly')
        }
        var alert = $('<div class="alert alert-success drag-alert"><strong>' + _t('Congratulations') + '!</strong> ' +
            msg + '.</div>').hide();
        self.$el.siblings("#dragandrophandler").after(alert);
        alert.slideDown(500, function(){
            if(!self.getParent().dataset.get_context().eval()['active_ids']){
                self.$el.siblings('#dragfooter').find('button#show').show();
            }
        });
    },
});

core.form_widget_registry.add('action_invoice_document_supplier', attachXmlsWizard);
});


odoo.define('web.form_widgets_hide_buttons', function (require) {
    "use strict";

    var WebFormWidgets = require('web.form_widgets');

    var WidgetButtonHide = WebFormWidgets.WidgetButton.include({
        start: function() {
            /* Hides the default footer when the page starts */
            this._super();
            if(this.$el.attr('class').split(" ").includes('btn-cancel-close-xmls')){
                this.$el.parent().parent().parent().remove();
            }
        },
    });
});
