$(document).ready(function() {

    $(document).on('click', 'button[control="revoke-access"]', function() {
        // Gather data.
        var friend_group_id = $(this).attr('data-friend-group-id');
        var friend_group_name = $(this).attr('data-friend-group-name');
        var friend_id = $(this).attr('data-friend-id');
        var friend_name = $(this).attr('data-friend-name');
        var issue_id = $(this).attr('data-issue-id');
        var issue_name = $(this).attr('data-issue-name');

        // Gather controls.
        var $dialog = $('div[control="revoke-access-dialog"]');

        // Set variables that need to be passed on.
        $dialog.find('input#friend-group-id').val(friend_group_id);
        $dialog.find('input#friend-id').val(friend_id);
        $dialog.find('input#issue-id').val(issue_id);

        // Configure display fields.
        $dialog.find('span[control="friend-group-name"]').html(friend_group_name || '');
        $dialog.find('span[control="friend-name"]').html(friend_name || '');
        $dialog.find('span[control="issue-name"]').html(issue_name || '');

        // Show user or group portion, depending on which one we want.
        if (friend_group_id) {
            $dialog.find('p[control="group-display"]').show();
            $dialog.find('p[control="user-display"]').hide();
        }
        else if (friend_id) {
            $dialog.find('p[control="group-display"]').hide();
            $dialog.find('p[control="user-display"]').show();
        }

        // Show or hide issue portion, depending on whether revoking access to issue or altogether.
        if (issue_id) {
            $dialog.find('p[control="issue-display"]').show();
        }
        else {
            $dialog.find('p[control="issue-display"]').hide();
        }

        // Display the dialog.
        $dialog.modal();
    });

    $(document).on('click', 'button[control="revoke-access-confirmed"]', function() {
        var friend_group_id = $('input#friend-group-id').val();
        var friend_id = $('input#friend-id').val();
        var issue_id = $('input#issue-id').val();

        url = '/json/access/revoke/';

        // Select URL according to whether we're adding a group or an individual user.
        if (friend_group_id) {
            url += 'group/' + friend_group_id + '/';
        }
        else if (friend_id) {
            url += 'user/' + friend_id + '/';
        }

        // Append the issue ID if only adding access to one issue.
        if (issue_id) {
            url += 'issue/' + issue_id + '/';
        }

        $.jsonize({
            message: {
                'transit': 'Revoking access...',
                'success': 'Access revoked',
                'failure': 'Failed to revoke access!',
            },
            url: url,
            done: function(data, textStatus) {
                $('div[control="access-list"]').html(data.html_content);
                $('input[type="checkbox"]').bootstrapSwitch();
            }
        });
    });

    $(document).on('change', 'span[control="friend-selection"] select', function() {
        var $this = $(this);

        if ($this.val() == '') {
            return;
        }

        var $radio_group = $('input[type="radio"][value="group"]');
        var $radio_user = $('input[type="radio"][value="user"]');
        var $dropdown_group = $('select[control="friend-group-id"]');
        var $dropdown_user = $('select[control="friend-id"]');

        var control_name = $this.attr('control');

        if (control_name == 'friend-group-id') {
            $radio_user.prop('checked', false);
            $radio_group.prop('checked', true);
            $dropdown_user.val('').trigger('change');
        }
        else if (control_name == 'friend-id') {
            $radio_group.prop('checked', false);
            $radio_user.prop('checked', true);
            $dropdown_group.val('').trigger('change');
        }
    });

    $(document).on('click', 'button[control="grant-access"]', function() {
        // Gather data.
        var $this = $(this);
        var friend_group_id = $this.attr('data-friend-group-id');
        var friend_id = $this.attr('data-friend-id');
        var full_access = true;
        if (friend_group_id) {
            full_access = $(
                'input[control="toggle-full-access"][data-friend-group-id=' + friend_group_id + ']'
            ).bootstrapSwitch('state');
        }
        else if (friend_id) {
            full_access = $(
                'input[control="toggle-full-access"][data-friend-id=' + friend_id + ']'
            ).bootstrapSwitch('state');
        }

        // Gather controls.
        var $dialog = $('div[control="grant-access-dialog"]');
        var $radio_group = $dialog.find('input[type="radio"][value="group"]');
        var $radio_user = $dialog.find('input[type="radio"][value="user"]');
        var $friend_group_id = $dialog.find('select[control="friend-group-id"]');
        var $friend_id = $dialog.find('select[control="friend-id"]');

        // Configure display and input controls.
        if (friend_group_id) {
            $radio_user.prop('checked', false);
            $radio_group.prop('checked', true);
            $friend_group_id.val(friend_group_id).select2();
            $friend_id.val('').select2();
        }
        else if (friend_id) {
            $radio_group.prop('checked', false);
            $radio_user.prop('checked', true);
            $friend_group_id.val('').select2();
            $friend_id.val(friend_id).select2();
        }
        else {
            $radio_group.prop('checked', false);
            $radio_user.prop('checked', false);
            $friend_group_id.val('').select2();
            $friend_id.val('').select2();
        }
        $dialog.find('input[control="full-access"]').bootstrapSwitch('state', full_access);

        // Show the dialog.
        $dialog.modal();
    });

    $(document).on('click', 'button[control="grant-access-confirmed"]', function() {
        var friend_group_id = $('select[control="friend-group-id"]').val();
        var friend_id = $('select[control="friend-id"]').val();
        var issue_id = $('select[control="issue-id"]').val();
        var full_access = $('input[control="full-access"]').is(':checked');

        if (!friend_id && !friend_group_id) {
            return;
        }

        url = '/json/access/grant/';

        if (friend_group_id) {
            url += 'group/' + friend_group_id + '/';
        }
        else if (friend_id) {
            url += 'user/' + friend_id + '/';
        }

        // Append the issue ID if only adding access to one issue.
        if (issue_id) {
            url += 'issue/' + issue_id + '/';
        }

        $.jsonize({
            message: {
                'transit': 'Granting access...',
                'success': 'Access granted.',
                'failure': 'Failed to grant access.'
            },
            url: url,
            data: {
                'full_access': full_access,
            },
            done: function(data, textStatus) {
                $('div[control="access-list"]').html(data.html_content);
                $('input[type="checkbox"]').bootstrapSwitch();
                $('select[control="issue-id"]').select2('val', '');
            }
        });
    });

    $(document).on('switchChange.bootstrapSwitch', 'input[control="full-access"]', function(event, state) {
        var $parliament_id = $('select[control="parliament-id"]');
        var $issue_id = $('select[control="issue-id"]');

        $parliament_id.prop('disabled', state);
        $issue_id.prop('disabled', state);
    });

    $(document).on('change', 'select[control="parliament-num"]', function() {
        var $this = $(this);
        var parliament_num = $this.val();
        var $grant_access_issue = $('select[control="issue-id"]');

        $grant_access_issue.select2('val', '');

        $.jsonize({
            message: {
                'transit': 'Fetching issue list...',
                'success': 'Issue list fetched.',
                'failure': 'Failed to fetch issue list!'
            },
            url: '/json/issue/list/' + parliament_num + '/',
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

        var friend_group_id = $(this).attr('data-friend-group-id');
        var friend_id = $(this).attr('data-friend-id');

        var url = '/json/access/grant/';
        if (friend_group_id) {
            url += 'group/' + friend_group_id + '/';
        }
        else if (friend_id) {
            url += 'user/' + friend_id + '/';
        }

        $.jsonize({
            message: {
                'transit': msg_transit,
                'success': msg_success,
                'failure': msg_failure
            },
            url: url,
            data: {
                'full_access': state
            },
            done: function(data, textStatus) {
                if (state != data.full_access) {
                    alert("An unexpected error occurred!");
                }
            },
            error: function(data, textStatus) {
                // Revert state to whatever it was before.
                $(this).bootstrapSwitch('state', !state, true);
            }
        });
    });

    $(document).on('click', 'button[control="request-membership"]', function() {
        var group_id = $('select[control="membership-request-group-id"]').val();

        $.jsonize({
            message: {
                'transit': 'Requesting group membership...',
                'success': 'Group membership requested.',
                'failure': 'Failed to request group membership!'
            },
            url: '/json/access/request/membership/' + group_id + '/',
            done: function(data, textStatus) {
                $('div[control="membership-requests"]').html(data.html_content);
                $('select[control="membership-request-group-id"]').select2();
            }
        });
    });

    $(document).on('click', 'button[control="withdraw-membership-request"]', function() {
        var group_id = $(this).attr('data-group-id');

        $.jsonize({
            message: {
                'transit': 'Withdrawing membership request...',
                'success': 'Membership request withdrawn.',
                'failure': 'Failed to withdraw membership request!'
            },
            url: '/json/access/withdraw/membership-request/' + group_id + '/',
            done: function(data, textStatus) {
                $('div[control="membership-requests"]').html(data.html_content);
                $('select[control="membership-request-group-id"]').select2();
            }
        });
    });

    $(document).on('click', 'button[control="process-membership-request"]', function() {
        var $this = $(this);
        var membership_request_id = $this.attr('data-membership-request-id');
        var mr_status = $this.attr('data-status');

        $.jsonize({
            type: 'POST',
            message: {
                'transit': 'Processing membership request...',
                'success': 'Membership request processed.',
                'failure': 'Failed to process membership request!'
            },
            url: '/json/access/process/membership-request/',
            data: {
                'membership_request_id': membership_request_id,
                'status': mr_status
            },
            done: function(data, textStatus) {
                $('div[control="incoming-membership-requests"]').html(data.html_content);
            }
        });
    });
});
