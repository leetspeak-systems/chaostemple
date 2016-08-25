
jQuery.fn.extend({
    loadBookmarks: function(args) {
        $menu = $(this);

        $.jsonize({
            message: {
                'transit': 'Reloading bookmarks...',
                'success': 'Bookmarks reloaded.',
                'failure': 'Reloading bookmarks failed!',
            },
            url: '/json/bookmark/issue/menu/' + PARLIAMENT_NUM,
            done: function(data, textStatus) {
                $menuitems = $menu.find('ul[class="dropdown-menu"]');
                if (data.bookmarked_issue_count > 0) {
                    $menu.show();
                    $menuitems.html(data.html_content);
                }
                else {
                    $menu.hide();
                    $menuitems.html('');
                }
            }
        });
    },
});

$(document).ready(function() {

    $(document).on('click', 'a[control="toggle-user-dossier-statistics"]', function() {
        var $this = $(this);
        var user_id = $this.attr('data-user-id');
        var issue_id = $this.attr('data-issue-id');

        var $container = $('[control="issue-container"][data-id=' + issue_id + '] div[control="statistic-container"]');
        var $stats = $('div[control="issue-dossier-statistic"][data-issue-id=' + issue_id + ']');
        var $buttons = $('a[control="toggle-user-dossier-statistics"][data-issue-id=' + issue_id + ']');

        if ($this.hasClass('active')) {
            $container.hide();
            $stats.filter('[data-user-id=' + user_id + ']').hide();
            $buttons.filter('[data-user-id=' + user_id + ']').removeClass('active');
        }
        else {
            $container.show();

            $stats.filter('[data-user-id=' + user_id + ']').show();
            $stats.filter('[data-user-id!=' + user_id + ']').hide();

            $buttons.filter('[data-user-id=' + user_id + ']').addClass('active');
            $buttons.filter('[data-user-id!=' + user_id + ']').removeClass('active');
        }
    });

    $(document).on('click', 'a[control="issue-bookmark"]', function() {
        issue_id = $(this).data('issue-id');

        $.jsonize({
            message: {
                'transit': 'Toggling bookmark...',
                'success': 'Bookmark toggled.',
                'failure': 'Toggling bookmark failed!',
            },
            url: '/json/bookmark/issue/toggle/' + issue_id + '/',
            done: function(data, textStatus) {
                $icons = $('a[control="issue-bookmark"][data-issue-id=' + issue_id + '] span[control="issue-bookmark-icon"]');
                if (data.is_bookmarked) {
                    $icons.removeClass('grey');
                }
                else {
                    $icons.addClass('grey');
                }

                $('li[control="bookmark-menu"]').loadBookmarks();
            }
        });
    });

    $(document).on('click', 'button[control="delete-issue-dossiers"]', function() {
        var issue_id = $(this).data('id');
        var issue_name = $('span[control="issue-name"][data-id=' + issue_id + ']').text()
        var issue_description = $('span[control="issue-description"][data-id=' + issue_id + ']').text()
        var $header = $('div[control="issue-header"][data-id=' +  issue_id + ']');
        var $dialog = $('div[control="delete-issue-dossiers-dialog"]');

        // Copy header attributes to dialog
        $.each($header[0].attributes, function(i, attr) {
            if (attr.name.substring(0, 5) == 'data-') {
                $dialog.attr(attr.name, attr.value);
            }
        });

        var display_name = issue_name;
        if (issue_description.length > 0) {
            display_name += ' (' + issue_description + ')';
        }

        $dialog.find('input#delete-issue-dossiers-id').val(issue_id);
        $dialog.find('span[control="delete-issue-dossiers-name"]').html(display_name);
        $dialog.modal();
    });

    $(document).on('click', 'button[control="delete-issue-dossiers-confirmed"]', function() {
        var $dialog = $('div[control="delete-issue-dossiers-dialog"]');
        var issue_id = $dialog.find('input#delete-issue-dossiers-id').val()

        $.jsonize({
            message: {
                'transit': 'Deleting issue\'s dossiers...',
                'success': 'Issue\'s dossiers deleted.',
                'failure': 'Issue\'s dossier deletion failed!',
            },
            url: '/json/issue/' + issue_id + '/dossiers/delete/',
            data: {
                'session_agenda_item_id': $dialog.attr('data-session-agenda-item-id'),
                'committee_agenda_item_id': $dialog.attr('data-committee-agenda-item-id'),
                'upcoming_session_ids': $dialog.attr('data-upcoming-session-ids'),
                'upcoming_committee_agenda_ids': $dialog.attr('data-upcoming-committee-agenda-ids'),
            },
            done: function(data, textStatus) {
                $('div[control="issue-container"][data-id=' + data.issue_id + ']').html(data.html_content);
                $('li[control="bookmark-menu"]').loadBookmarks();
            }
        });
    });

});

