// We only want to show the auto-monitor popup once.
var auto_monitor_popup_shown = false;

$(document).ready(function() {

    // Buttons: Fieldstates
    $(document).on('click', 'a[control="set-fieldstate"]', function() {
        $this = $(this);
        dossier_id = $this.data('dossier-id');
        fieldname = $this.data('fieldname');
        fieldstate = $this.data('fieldstate');

        $.jsonize({
            message: {
                'transit': 'Setting fieldstate...',
                'success': 'Fieldstate set.',
                'failure': 'Failed to set fieldstate!',
            },
            url: '/dossier/' + dossier_id + '/fieldstate/' + fieldname + '/',
            data: { 'fieldstate': fieldstate },
            done: function(data, textStatus) {
                // Update the relevant button's color, text and menu selection.
                $('a[control="set-fieldstate"][data-dossier-id=' + dossier_id + '][data-fieldname=' + fieldname + ']').each(function() {
                    $anchor = $(this);
                    $dropdown = $('button[control="dropdown-fieldstate"][data-id=' + dossier_id + '][data-fieldname=' + fieldname + ']');

                    if ($anchor.data('fieldstate') == data[fieldname]) {
                        // Set the correct menu selection to active.
                        $anchor.parent().addClass('active');

                        // Update the button text.
                        $dropdown.find('.display').text($anchor.text());

                        // "keepclass" is needed in case two fieldstates have
                        // the same CSS class.
                        keepclass = '';

                        // Set the button color.
                        for (var key in fieldstate_css[fieldname]) {
                            if (key == data[fieldname]) {
                                keepclass = fieldstate_css[fieldname][key];
                            }
                            $dropdown.removeClass('btn-' + fieldstate_css[fieldname][key]);
                        }
                        if (keepclass) {
                            $dropdown.addClass('btn-' + keepclass);
                        }
                    }
                    else {
                        // Disactivating any menu selection which is not
                        // selected.
                        $anchor.parent().removeClass('active');
                    }
                });

                /* The constant HAS_USEFUL_INFO only tells us what the state
                 * was when the page was loaded. If there was no useful info
                 * when the page was loaded, but the user has started working
                 * on the issue, thereby presumably producing useful info, we
                 * infer that the issue should be auto-monitored.
                 */
                if (SETTING_AUTO_MONITOR && !HAS_USEFUL_INFO && !IS_MONITORED && !auto_monitor_popup_shown) {
                    $('[control="issue-monitor"]').click();

                    // Show notification.
                    var $notification = $('div[control="auto-monitor-notification');
                    $notification.fadeIn('fast');
                    window.setTimeout(function() {
                        $notification.fadeOut('fast');
                    }, 6000);

                    auto_monitor_popup_shown = true;
                }
            }
        });
    });

    // Button: create-dossier
    $(document).on('click', 'button[control="create-dossier"]', function() {
        let $this = $(this);
        let doc_num = $this.data('doc-num');
        let log_num = $this.data('log-num');

        // Construct URL based on whether the dossier belongs to a document or
        // review. This distinction is only important because they are
        // designated by different kinds of IDs (doc_num and log_num,
        // respectively).
        let url = '/dossier/parliament/' + PARLIAMENT_NUM;
        if (doc_num) {
            url += '/document/' + doc_num;
        }
        else if (log_num) {
            url += '/review/' + log_num;
        }
        else {
            // This makes no sense. Let's just do nothing.
            return;
        }
        url += '/create/';

        $.jsonize({
            message: {
                'transit': 'Creating dossier...',
                'success': 'Dossier created.',
                'failure': 'Dossier creation failed!',
            },
            url: url,
            done: function(data, textStatus) {
                if (data.document_id) {
                    $('div[control="document-container"][data-document-id=' + data.document_id + ']').html(data.html);
                }
                else if (data.review_id) {
                    $('div[control="review-container"][data-review-id=' + data.review_id + ']').html(data.html);
                }
            }
        });
    });

    // Button: delete-dossier
    $(document).on('click', 'button[control="delete-dossier"]', function() {
        let $this = $(this);
        $('input#delete-dossier-doc-num').val($this.data('doc-num'));
        $('input#delete-dossier-log-num').val($this.data('log-num'));
        $('div[control="delete-dossier-dialog"]').modal();
    });

    // Button: delete-dossier-confirmed
    $(document).on('click', 'button[control="delete-dossier-confirmed"]', function() {
        let doc_num = $('input#delete-dossier-doc-num').val();
        let log_num = $('input#delete-dossier-log-num').val();

        // Construct URL based on whether the dossier belongs to a document or
        // review. This distinction is only important because they are
        // designated by different kinds of IDs (doc_num and log_num,
        // respectively).
        let url = '/dossier/parliament/' + PARLIAMENT_NUM;
        if (doc_num) {
            url += '/document/' + doc_num;
        }
        else if (log_num) {
            url += '/review/' + log_num;
        }
        else {
            // This makes no sense. Let's just do nothing.
            return;
        }
        url += '/delete/';

        $.jsonize({
            message: {
                'transit': 'Deleting dossier...',
                'success': 'Dossier deleted.',
                'failure': 'Dossier deletion failed!',
            },
            url: url,
            done: function(data, textStatus) {
                if (data.document_id) {
                    $('div[control="document-container"][data-document-id=' + data.document_id + ']').html(data.html);
                }
                else if (data.review_id) {
                    $('div[control="review-container"][data-review-id=' + data.review_id + ']').html(data.html);
                }
            }
        });
    });
});
