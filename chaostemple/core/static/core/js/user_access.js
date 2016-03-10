$(document).ready(function() {
    $('input[control="toggle-full-access"]').bootstrapSwitch();

    $(document).on('click', 'button[control="select-user"]', function() {
        var friend_id = $(this).val()

        $.jsonize({
            message: {
                'transit': 'Adding user...',
                'success': 'User added.',
                'failure': 'Failed to add user!',
            },
            url: '/json/user/access/grant/' + friend_id + '/',
            data: {
                'full_access': true,
            },
            done: function(data, textStatus) {
                $('div[control="access-list"]').html(data.html_content);
                $('input[control="toggle-full-access"]').bootstrapSwitch();
            }
        });
    });

    $(document).on('click', 'button[control="revoke-access-user"]', function() {
        var friend_id = $(this).attr('data-friend-id');
        var friend_name = $(this).attr('data-friend-name');

        var $dialog = $('div[control="revoke-access-user-dialog"]');

        $dialog.find('input#revoke-access-user-friend-id').val(friend_id);
        $dialog.find('span[control="revoke-access-user-friend-name"]').html(friend_name);
        $dialog.modal();
    });

    $(document).on('click', 'button[control="revoke-access-user-confirmed"]', function() {
        var friend_id = $('input#revoke-access-user-friend-id').val();

        $.jsonize({
            message: {
                'transit': 'Removing friend from access',
                'success': 'Friend removed from access.',
                'failure': 'Failed to remove friend from access!',
            },
            url: '/json/user/access/revoke/' + friend_id + '/',
            done: function(data, textStatus) {
                $('div[control="access-list"]').html(data.html_content);
                $('input[control="toggle-full-access"]').bootstrapSwitch();
            }
        });
    });

    $('div[control="access-list"]').on('switchChange.bootstrapSwitch', 'input[control="toggle-full-access"]', function(event, state) {

        if (state) {
            msg_transit = 'Giving full access...';
            msg_success = 'Full access given.';
            msg_failure = 'Failed to give full access!';
        }
        else {
            msg_transit = 'Revoking full access...';
            msg_success = 'Full access revoked.';
            msg_failure = 'Failed to revoke full access!';
        }

        var friend_id = $(this).attr('data-friend-id');

        $.jsonize({
            message: {
                'transit': msg_transit,
                'success': msg_success,
                'failure': msg_failure
            },
            url: '/json/user/access/grant/' + friend_id + '/',
            data: {
                'full_access': state
            },
            done: function(data, textStatus) {
                if (state != data.full_access) {
                    alert("An unexpected error occurred!");
                    $('input[control="toggle-full-access"][data-friend-id=' + friend_id + ']').bootstrapSwitch('state', data.full_access, true);
                }
            },
            error: function(data, textStatus) {
                // Revert state to whatever it was before.
                $('input[control="toggle-full-access"][data-friend-id="' + friend_id + '"]').bootstrapSwitch('state', !state, true);
            }
        });
    });
});
