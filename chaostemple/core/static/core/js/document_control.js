// We only want to show the auto-monitor popup once.
var auto_monitor_popup_shown = false;

jQuery.fn.extend({
    setMemoCount: function(memo_count) {
        $dossier = $(this);
        $toggle_dossier_memos = $dossier.find('button[control="toggle-dossier-memos"]');
        $memo_count = $toggle_dossier_memos.find('span[control="memo-count"]');

        $memo_count.html(memo_count);
        if (memo_count > 0) {
            $memo_count.removeClass('label-default');
            $memo_count.addClass('label-primary');
            $toggle_dossier_memos.attr('disabled', null);
        }
        else {
            $memo_count.removeClass('label-primary');
            $memo_count.addClass('label-default');
            $toggle_dossier_memos.attr('disabled', '1');
        }
    },
});

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
                    $('a[control="issue-monitor"]').click();

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

    // Button: delete-dossier
    $(document).on('click', 'button[control="delete-dossier"]', function() {
        dossier_id = $(this).data('id');
        $('input#delete-dossier-id').val(dossier_id); // Store the dossier_id in the modal dialog
        $('div[control="delete-dossier-dialog"]').modal(); // Open the modal dialog
    });

    // Button: delete-dossier-confirmed
    $(document).on('click', 'button[control="delete-dossier-confirmed"]', function() {
        dossier_id = $('input#delete-dossier-id').val();

        $.jsonize({
            message: {
                'transit': 'Deleting dossier...',
                'success': 'Dossier deleted.',
                'failure': 'Dossier deletion failed!',
            },
            url: '/dossier/' + dossier_id + '/delete/',
            done: function(data, textStatus) {
                if (data.document_id) {
                    $('div[control="document"][data-id=' + data.document_id + '] .panel-footer[data-dossier-id=' + dossier_id + ']').remove();
                }
                else if (data.review_id) {
                    $('div[control="review"][data-id=' + data.review_id + '] .panel-footer[data-dossier-id=' + dossier_id + ']').remove();
                }
            }
        });
    });

    // Button: toggle-dossier-memos
    $(document).on('click', 'button[control="toggle-dossier-memos"]', function() {
        var dossier_id = $(this).data('id');
        $('div[control="dossier-memos"][data-id=' + dossier_id + '] ul').toggle();
    });

    // Button: edit-memo-button (also receives signal from adding button)
    $(document).on('click', 'button[control="edit-memo-button"]', function() {
        var $this = $(this);
        var memo_id = $this.data('id');
        var dossier_id = $this.data('dossier-id');

        var $dossier_memos = $('div[control="dossier-memos"][data-id=' + dossier_id + '] ul');
        var $memo_list = $('ul[control="memo-list"][data-dossier-id=' + dossier_id + ']');
        var $memo_content_plaintext = $('span[control="memo-content-plaintext"][data-id=' + memo_id + ']');
        var $memo_content = $('span[control="memo-content"][data-id=' + memo_id + ']');
        var $edit_memo_content = $dossier_memos.find('textarea[control="edit-memo-content"][data-id=' + memo_id + ']');
        var $edit_memo_counter = $dossier_memos.find('td[control="edit-memo-counter"][data-id=' + memo_id + ']');
        var $sort_memo = $dossier_memos.find('span[control="sort-memo"][data-id=' + memo_id + ']');

        // Make sure memos are visible.
        $dossier_memos.show();

        // Cancel editing anywhere else in the dossier
        $memo_list.find('span[control="memo-content"]').show();
        $memo_list.find('textarea[control="edit-memo-content"]').hide();
        $memo_list.find('td[control="edit-memo-counter"]').hide();

        var content = $memo_content_plaintext.text();

        $memo_content.hide();
        $sort_memo.hide();
        $edit_memo_content.val(content);
        $edit_memo_content.show();
        $edit_memo_content.focus();
        $edit_memo_content.trigger('input');
        $edit_memo_content[0].setSelectionRange(content.length, content.length);
        $edit_memo_counter.show()

        $edit_memo_content.height($edit_memo_content[0].scrollHeight + 'px');
     });

    $(document).on('input', 'textarea[control="edit-memo-content"]', function(e) {
        var $this = $(this);
        var memo_id = $this.attr('data-id');
        var memo_length = $this.val().length;
        var $edit_memo_counter = $('td[control="edit-memo-counter"][data-id=' + memo_id + ']');

        $edit_memo_counter.find('span[control="edit-memo-counter-value"]').text(memo_length);
    });

    // Automatically adapt the height of the textarea according to needed space.
    $(document).on('keyup', 'textarea[control="edit-memo-content"]', function(e) {
        var $this = $(this);
        $this.height($this[0].scrollHeight + 'px');
    });

    // Text field: edit-memo-content
    $(document).on('keydown', 'textarea[control="edit-memo-content"]', function(e) {
        keycode = e.keyCode || e.which; // Cross-browser key detection (still ugly as hell)

        if (keycode == 13) { // Enter key
            var $this = $(this);
            var memo_id = $this.data('id');
            var dossier_id = $this.data('dossier-id');
            var content = $this.val();

            if (memo_id == 0) {
                $.jsonize({
                    message: {
                        'transit': 'Adding memo...',
                        'success': 'Memo added.',
                        'failure': 'Memo adding failed!',
                    },
                    url: '/dossier/memo/' + dossier_id + '/add/',
                    type: 'POST',
                    data: {
                        content: content,
                    },
                    done: function(data, textStatus) {
                        $('div[control="dossier-memos"][data-id=' + data.dossier_id + ']').html(data.html_content);
                        reloadSortable();

                        $('div[control="dossier"][data-id=' + data.dossier_id + ']').setMemoCount(data.memo_count);
                    },
                });
            }
            else {
                $.jsonize({
                    message: {
                        'transit': 'Updating memo...',
                        'success': 'Memo updated.',
                        'failure': 'Memo updating failed!',
                    },
                    url: '/dossier/memo/' + memo_id + '/edit/',
                    type: 'POST',
                    data: {
                        content: content,
                    },
                    done: function(data, textStatus) {
                        $('div[control="dossier-memos"][data-id=' + data.dossier_id + ']').html(data.html_content);
                        reloadSortable();
                    },
                });
            }
        }
        else if (keycode == 27) { // Escape key
            var $this = $(this);
            var memo_id = $this.data('id');
            var dossier_id = $this.data('dossier-id');

            var $memo_list = $('ul[control="memo-list"][data-dossier-id=' + dossier_id + ']');

            $('textarea[control="edit-memo-content"][data-id=' + memo_id + ']').hide();
            $('td[control="edit-memo-counter"][data-id=' + memo_id + ']').hide();
            $('span[control="memo-content"][data-id=' + memo_id + ']').show();
            $('span[control="sort-memo"][data-id=' + memo_id + ']').show();

            if ($memo_list.find('li[control="memo-line"]').length == 0) {
                $memo_list.hide();
            }
        }
    });

    // Button: delete-memo
    $(document).on('click', 'button[control="delete-memo"]', function() {
        var memo_id = $(this).data('id');
        var memo_content = $('span[control="memo-content"][data-id=' + memo_id + ']').text();
        var $dialog = $('div[control="delete-memo-dialog"]');

        $dialog.find('input#delete-memo-id').val(memo_id);
        $dialog.find('span[control="delete-memo-content"]').html(memo_content);
        $dialog.modal();
    });

    // Button: delete-memo-confirmed
    $(document).on('click', 'button[control="delete-memo-confirmed"]', function() {
        var memo_id = $('input#delete-memo-id').val();

        $.jsonize({
            message: {
                'transit': 'Deleting memo...',
                'success': 'Memo deleted.',
                'failure': 'Memo deletion failed!',
            },
            url: '/dossier/memo/' + memo_id + '/delete/',
            done: function(data, textStatus) {
                $('div[control="dossier-memos"][data-id=' + data.dossier_id + ']').html(data.html_content);
                reloadSortable();

                $('div[control="dossier"][data-id=' + data.dossier_id + ']').setMemoCount(data.memo_count);
            }
        });
    });

    // List: memo-list
    $(document).on('sortupdate', 'ul[control="memo-list"]', function() {
        var $memo_list = $(this);
        var dossier_id = $memo_list.data('dossier-id');
        var iterator = 0;
        var order_map = {};
        $memo_list.find('li[control="memo-line"]').each(function() {
            var memo_id = $(this).data('id');
            order_map[memo_id] = ++iterator;
        });

        $.jsonize({
            message: {
                'transit': 'Re-ordering memos...',
                'success': 'Memos re-ordered.',
                'failure': 'Memo re-ordering failed!',
            },
            url: '/dossier/memo/sort/' + dossier_id + '/',
            type: 'POST',
            data: {
                order_map: JSON.stringify(order_map), // To send it in JSON
            },
            done: function(data, textStatus) {
                $('div[control="dossier-memos"][data-id=' + data.dossier_id + ']').html(data.html_content);
                reloadSortable();
            },
        });

    });
});

