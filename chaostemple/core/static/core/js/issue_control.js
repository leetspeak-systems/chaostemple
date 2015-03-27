
jQuery.fn.extend({
    loadBookmarks: function(args) {
        $menu = $(this);

        $.jsonize({
            url: '/json/bookmark/issue/menu/',
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

    $(document).on('click', 'a[control="issue-bookmark"]', function() {
        issue_id = $(this).data('issue-id');

        $.jsonize({
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
        var $dialog = $('div[control="delete-issue-dossiers-dialog"]');

        var display_name = issue_name;
        if (issue_description.length > 0) {
            display_name += ' (' + issue_description + ')';
        }

        $dialog.find('input#delete-issue-dossiers-id').val(issue_id);
        $dialog.find('span[control="delete-issue-dossiers-name"]').html(display_name);
        $dialog.modal();
    });

    $(document).on('click', 'button[control="delete-issue-dossiers-confirmed"]', function() {
        var issue_id = $('input#delete-issue-dossiers-id').val()

        $.jsonize({
            url: '/json/issue/' + issue_id + '/dossiers/delete/',
            done: function(data, textStatus) {
                $('div[control="issue-container"][data-id=' + data.issue_id + ']').html(data.html_content);
            }
        });
    });

});

