
jQuery.fn.extend({
    loadMonitors: function(args) {
        $menu = $(this);

        $.jsonize({
            message: {
                'transit': 'Reloading monitors...',
                'success': 'Monitors reloaded.',
                'failure': 'Reloading monitors failed!',
            },
            url: '/json/monitor/issue/menu/' + PARLIAMENT_NUM,
            done: function(data, textStatus) {
                $menuitems = $menu.find('ul[class="dropdown-menu"]');
                if (data.monitored_issue_count > 0) {
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

    $(document).on('click', 'a[control="expand-proposer"]', function() {
        var $this = $(this);
        var proposer_id = $this.attr('data-id');

        $.jsonize({
            message: {
                'transit': 'Fetching sub-proposers...',
                'success': 'Sub-proposers fetched.',
                'failure': 'Fetching sub-proposers failed!',
            },
            url: '/json/proposer/' + proposer_id + '/subproposers/',
            type: 'POST',
            data: {
                path: location.pathname,
                crumb_string: url_params['from'],
            },
            done: function(data, textStatus) {
                var name = '';
                var url = '';
                var content = '';
                for (i = 0; i < data.subproposers.length; i++) {
                    name = data.subproposers[i].name;
                    url = data.subproposers[i].url;
                    if (i > 0) {
                        content += ', ';
                    }
                    content += '<a href="' + url + '">' + name + '</a>';
                }
                $this.parent().html(content);
            }
        });
    });

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

    $(document).on('click', 'a[control="issue-monitor"]', function() {
        issue_id = $(this).data('issue-id');

        $.jsonize({
            message: {
                'transit': 'Toggling monitor...',
                'success': 'Monitor toggled.',
                'failure': 'Toggling monitor failed!',
            },
            url: '/json/monitor/issue/toggle/' + issue_id + '/',
            done: function(data, textStatus) {
                $icons = $('a[control="issue-monitor"][data-issue-id=' + issue_id + '] span[control="issue-monitor-icon"]');
                if (data.is_monitored) {
                    $icons.removeClass('grey');
                }
                else {
                    $icons.addClass('grey');
                }

                $('li[control="monitor-menu"]').loadMonitors();
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
        if ($header.length) {
            $.each($header[0].attributes, function(i, attr) {
                if (attr.name.substring(0, 5) == 'data-') {
                    $dialog.attr(attr.name, attr.value);
                }
            });
        }

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
            url: '/dossier/issue/' + issue_id + '/delete/',
            data: {
                'session_agenda_item_id': $dialog.attr('data-session-agenda-item-id'),
                'committee_agenda_item_id': $dialog.attr('data-committee-agenda-item-id'),
                'upcoming_session_ids': $dialog.attr('data-upcoming-session-ids'),
                'upcoming_committee_agenda_ids': $dialog.attr('data-upcoming-committee-agenda-ids'),
            },
            done: function(data, textStatus) {
                $('div[control="issue-container"][data-id=' + data.issue_id + ']').html(data.html_content);
                $('li[control="monitor-menu"]').loadMonitors();
            }
        });
    });

    // If there is an issue type selector around... select the first tab.
    $('[control="issue-type-selector"] li:first-child a').trigger('click');

    $(document).on('click', 'button[control="issue-type-toggle"]', function() {
        // Controls.
        var $button = $(this);
        var $marker = $button.find('span.glyphicon-ok');

        // Gathered variables.
        var issue_type = $button.attr('data-issue-type');
        var show = !$marker.hasClass('grey');

        // Find the issues that we wish to either show or hide.
        var $issues = $('[control="issue-container"][data-issue-type="' + issue_type + '"]');

        if (show) {
            $issues.hide();
            $marker.addClass('grey');
        }
        else {
            $issues.show();
            $marker.removeClass('grey');
        }
    });

    // Make all the issue type togglers do their things.
    $('[control="issue-type-toggle"][is-interesting="true"]').trigger('click');

});

