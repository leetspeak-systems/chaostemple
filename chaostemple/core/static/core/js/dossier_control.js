// We only want to show the auto-monitor popup once.
var auto_monitor_popup_shown = false;

$(document).ready(function() {

    // Processing non-standard events is apparently not supported by jQuery,
    // so we'll have to deal with the editor in its native, non-jQuery form.
    let editor = document.querySelector('.prosearea-editor');

    // Other controls.
    let $dossier_status = $('span[control="dossier-status"]');
    let $dossier_save = $('button[control="dossier-save"]');

    // Hook up save-button.
    $dossier_save.on('click', function() {
        editor.view.save();
    });

    // Save changed content.
    editor.addEventListener('save', function(evt) {
        var $this = $(this);
        var dossier_id = $this.attr('data-dossier-id');
        var notes = $this.val();

        $.jsonize({
            message: {
                'transit': 'Saving notes...',
                'success': 'Notes saved.',
                'failure': 'Failed to save notes!',
            },
            type: 'POST',
            url: '/dossier/' + dossier_id + '/set-notes/',
            data: { 'notes': notes },
            done: function(data, textStatus) {
                if (data.ok) {
                    // Notify user of success.
                    $dossier_status.html(MSG_STATUS_SAVED);

                    $dossier_save.attr('disabled', true);
                }
                else {
                    // Notify user that something went wrong.
                    $dossier_status.html(MSG_STATUS_ERROR);

                    $dossier_save.attr('disabled', false);
                }
            },
        });
    });

    // Notify user that content changed and has not yet been saved.
    editor.addEventListener('changed', function(evt) {
        $dossier_status.html(MSG_STATUS_UNSAVED);

        $dossier_save.attr('disabled', false);
    });

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

                    // Set a monitor to the issue.
                    $.jsonize({
                        message: {
                            'transit': 'Setting monitor...',
                            'success': 'Monitor set.',
                            'failure': 'Setting monitor failed!',
                        },
                        url: '/json/monitor/issue/toggle/' + ISSUE_ID + '/',
                        done: function() {
                            // Everything is fine.
                        }
                    });

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
});
