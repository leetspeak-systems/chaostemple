
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

});

