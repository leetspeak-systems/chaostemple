$(document).ready(function() {

    $(document).on('click', 'button[control="revoke-access-user"]', function() {
        var $this = $(this);
        var friend_id = $this.attr('data-friend-id');
        var friend_name = $this.attr('data-friend-name');

        var $dialog = $('div[control="revoke-access-user-dialog"]');
        $dialog.find('input#revoke-access-user-friend-id').val(friend_id);
        $dialog.find('span[control="revoke-access-user-friend-name"]').html(friend_name);
        $dialog.modal();
    });

    $(document).on('click', 'button[control="revoke-access-user-confirmed"]', function() {
        var friend_id = $('input#revoke-access-user-friend-id').val();

        $.jsonize({
            message: {
                'transit': 'Removing friend from access...',
                'success': 'Friend removed from access.',
                'failure': 'Failed to remove friend from access!',
            },
            url: '/json/user/access/revoke/' + friend_id + '/',
            done: function(data, textStatus) {
                $('div[control="access-list"]').html(data.html_content);
                $('input[type="checkbox"]').bootstrapSwitch();
            }
        });
    });

    $(document).on('click', 'button[control="revoke-access-issue"]', function() {
        var friend_id = $(this).attr('data-friend-id');
        var friend_name = $(this).attr('data-friend-name');
        var issue_id = $(this).attr('data-issue-id');
        var issue_name = $(this).attr('data-issue-name');

        var $dialog = $('div[control="revoke-access-issue-dialog"]');
        $dialog.find('input#revoke-access-issue-friend-id').val(friend_id);
        $dialog.find('span[control="revoke-access-issue-friend-name"]').html(friend_name);
        $dialog.find('input#revoke-access-issue-id').val(issue_id);
        $dialog.find('span[control="revoke-access-issue-name"]').html(issue_name);
        $dialog.modal();
    });

    $(document).on('click', 'button[control="revoke-access-issue-confirmed"]', function() {
        var friend_id = $('input#revoke-access-issue-friend-id').val();
        var issue_id = $('input#revoke-access-issue-id').val();

        $.jsonize({
            message: {
                'transit': 'Revoking access to issue...',
                'success': 'Access to issue revoked',
                'failure': 'Failed to revoke access to issue!',
            },
            url: '/json/user/access/revoke/' + friend_id + '/issue/' + issue_id + '/',
            done: function(data, textStatus) {
                $('div[control="access-list"]').html(data.html_content);
                $('input[type="checkbox"]').bootstrapSwitch();
            }
        });
    });

    $(document).on('click', 'button[control="grant-access-issue"]', function() {
        var $this = $(this);
        var friend_id = $this.attr('data-friend-id');
        var full_access = true;

        if (friend_id) {
            full_access = $('input[control="toggle-full-access"][data-friend-id=' + friend_id + ']').bootstrapSwitch('state');
        }

        var $dialog = $('div[control="grant-access-issue-dialog"]');
        $dialog.find('select[control="grant-access-friend-id"]').val(friend_id).select2();
        $dialog.find('input[control="grant-access-full-access"]').bootstrapSwitch('state', full_access);
        $dialog.modal();
    });

    $(document).on('click', 'button[control="grant-access-issue-confirmed"]', function() {
        var friend_id = $('select[control="grant-access-friend-id"]').val();
        var issue_id = $('select[control="grant-access-issue-id"]').val();
        var full_access = $('input[control="grant-access-full-access"]').is(':checked');

        if (!friend_id) {
            return;
        }

        if (issue_id) {
            url = '/json/user/access/grant/' + friend_id + '/issue/' + issue_id;
        }
        else {
            url = '/json/user/access/grant/' + friend_id + '/';
        }

        $.jsonize({
            message: {
                'transit': 'Granting access...',
                'success': 'Access granted.',
                'failure': 'Failred to grant access.'
            },
            url: url,
            data: {
                'full_access': full_access,
            },
            done: function(data, textStatus) {
                $('div[control="access-list"]').html(data.html_content);
                $('input[type="checkbox"]').bootstrapSwitch();
                $('select[control="grant-access-issue-id"]').select2('val', '');
            }
        });
    });

    $(document).on('switchChange.bootstrapSwitch', 'input[control="grant-access-full-access"]', function(event, state) {
        var $parliament_id = $('select[control="grant-access-parliament-id"]');
        var $issue_id = $('select[control="grant-access-issue-id"]');

        $parliament_id.prop('disabled', state);
        $issue_id.prop('disabled', state);
    });

    $(document).on('change', 'select[control="grant-access-parliament-id"]', function() {
        var $this = $(this);
        var parliament_id = $this.val();
        var $grant_access_issue = $('select[control="grant-access-issue-id"]');

        $grant_access_issue.select2('val', '');

        $.jsonize({
            message: {
                'transit': 'Fetching issue list...',
                'success': 'Issue list fetched.',
                'failure': 'Failed to fetch issue list!'
            },
            url: '/json/issue/list/' + parliament_id + '/',
            done: function(data, textStatus) {
                var issue_list = data.issue_list;

                $grant_access_issue.empty();
                for (var i = 0; i < issue_list.length; i++) {
                    var issue = issue_list[i];
                    $grant_access_issue.append($('<option>', { value: issue.id, text: issue.name }));
                }
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
