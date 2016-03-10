$(document).ready(function() {
    var $user_lookup = $('div[control="user-lookup"]');
    var $search_field = $user_lookup.find('input[control="search-field"]');
    var $user_list = $user_lookup.find('ul[control="user-list"]');
    var $select_user = $user_lookup.find('button[control="select-user"]');

    var previous_lookup_string = '';

    $search_field.keyup(function(eventData) {
        var lookup_string = $(this).val();

        // Prevent non-changing keystrokes from commencing search
        if (lookup_string == previous_lookup_string) {
            return;
        }

        // Unselect possibly previously selected user
        $select_user.val(0);

        // Show/hide entries according to search string
        var count = 0;
        $user_list.find('li').each(function() {
            var $entry = $(this);

            if ($entry.text().search(new RegExp(lookup_string, 'i')) < 0) {
                $entry.hide();
            }
            else {
                $entry.show();
                count++;
            }

            // Select entry if perfect match
            if ($entry.text() == lookup_string.trim()) {
                $entry.find('a[control="user-entry"]').trigger('click');
            }
        });

        // Show/hide "No results" entry when nothing is found
        if (count == 0) {
            $user_list.find('li[control="no-results"]').show();
        }
        else {
            $user_list.find('li[control="no-results"]').hide();
        }

        // Show/hide dropdown
        var is_open = $user_list.parent().hasClass('open');
        if ((lookup_string.length > 0 && !is_open) || (lookup_string.length == 0 && is_open)) {
            $user_list.dropdown('toggle');
        }

        // Enable/disable selection button
        $select_user.attr('disabled', ($select_user.val() == 0 ? 'true' : null));

        // Remember search to check if prcessing is needed after next keystroke
        previous_lookup_string = lookup_string;
    });

    // Process selection of user from dropdown
    $user_list.find('a[control="user-entry"]').click(function() {
        var $user_entry = $(this);

        $select_user.val($user_entry.attr('data-user-id'));
        $search_field.val($user_entry.attr('data-username'));

        $select_user.attr('disabled', null);
    });

    // Some browsers (Firefox at least) retains value on reload, so we check text when page is loaded
    $search_field.trigger('keyup');
});
