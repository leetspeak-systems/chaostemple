
jQuery.fn.extend({
    loadBookmarks: function(args) {
        $menu = $(this);

        $.jsonize({
            url: '/json/bookmark/issue/menu/',
            done: function(data, textStatus) {
                $menuitems = $menu.find('ul[class="dropdown-menu"]');
                if (data.bookmarked_issue_count > 0) {
                    $menu.show();
                    $menuitems.html(data.content);
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
        $anchor = $(this);
        issue_id = $anchor.data('issue-id');

        $.jsonize({
            url: '/json/bookmark/issue/toggle/' + issue_id + '/',
            done: function(data, textStatus) {
                if (data.is_bookmarked) {
                    $anchor.find('span[control="issue-bookmark-icon"]').removeClass('grey');
                }
                else {
                    $anchor.find('span[control="issue-bookmark-icon"]').addClass('grey');
                }

                $('li[control="bookmark-menu"]').loadBookmarks();
            }
        });
    });

});

