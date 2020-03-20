
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
                $menuitems = $menu.find('ul[class="dropdown-menu"]').html(data.html_content);
            }
        });
    },

    // Issues can be filtered in various ways. Examples include by search
    // text, issue type and proposer type. Each filter checks whether
    // individual conditions are fulfilled for each issue in a given issue
    // list, updating their respective "condition-*" fields, and then calls
    // this function on each applicable issue to see whether all the
    // conditions are fulfilled. If so, the issue is shown, but if one of them
    // is explicitly false, then it is not shown.
    applyFilterCondition: function(condition_name, condition_value) {
        var $rows = $(this);

        // Only particular condition names are accepted.
        if (['issue-type', 'proposer-type', 'search-text'].indexOf(condition_name) < 0) {
            return;
        }

        // Apply the given condition. The value is forced to either "true" or
        // "false" in the HTML.
        $rows.attr('condition-' + condition_name, (condition_value ? 'true' : 'false'));

        // Display and hide issues depending on whether all the conditions are met or not.
        $rows.filter('[condition-issue-type="false"],[condition-proposer-type="false"],[condition-search-text="false"]').hide();
        $rows.filter('[condition-issue-type="true"][condition-proposer-type="true"][condition-search-text="true"]').show();
    },

});

$(document).ready(function() {

    document.addEventListener('visibilitychange', function(ev) {
        if (document.visibilityState == 'visible') {
            var elem = $(document.activeElement);

            if (elem.data('reload-on-focus') == undefined) {
                // Nothing to do here.
                return;
            }

            var log_num = elem.data('log-num');
            var doc_num = elem.data('doc-num');

            if (log_num) {
                $.jsonize({
                    message: {
                        'transit': 'Retrieving review...',
                        'success': 'Review retrieved.',
                        'failure': 'Review retrieval failed!',
                    },
                    url: '/json/parliament/' + PARLIAMENT_NUM + '/review/' + log_num + '/',
                    done: function(data, textStatus) {
                        $('div[control="review-container"][data-review-id="' + data.review_id + '"]').html(data.html);
                    },
                });
            }
            else if (doc_num) {
                $.jsonize({
                    message: {
                        'transit': 'Retrieving document...',
                        'success': 'Document retrieved.',
                        'failure': 'Document retrieval failed!',
                    },
                    url: '/json/parliament/' + PARLIAMENT_NUM + '/document/' + doc_num + '/',
                    done: function(data, textStatus) {
                        $('div[control="document-container"][data-document-id="' + data.document_id + '"]').html(data.html);
                    },
                });
            }
        }
    });

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

    $(document).on('click', '[control="issue-monitor"]', function() {
        var $this = $(this);
        var issue_id = $this.attr('data-issue-id');
        var stub_type = $('[control="issue-container"][data-id="' + issue_id + '"]').attr('data-stub-type');
        if (!stub_type) {
            stub_type = '';
        }

        $.jsonize({
            message: {
                'transit': 'Toggling monitor...',
                'success': 'Monitor toggled.',
                'failure': 'Toggling monitor failed!',
            },
            url: '/json/monitor/issue/toggle/' + issue_id + '/?stub_type=' + stub_type,
            done: function(data, textStatus) {
                var issue = $('[control="issue-container"][data-id=' + data.issue_id + ']')
                if (issue.length > 0) {
                    issue.replaceWith(data.html_content);
                }
                else {
                    if (data.is_monitored) {
                        $('[control="issue-monitor-icon"]').removeClass('grey');
                    }
                    else {
                        $('[control="issue-monitor-icon"]').addClass('grey');
                    }
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
                $('div[control="issue-container"][data-id=' + data.issue_id + ']').replaceWith(data.html_content);
                $('li[control="monitor-menu"]').loadMonitors();
            }
        });
    });

    $(document).on('click', 'button[control="issue-type-toggle"]', function() {
        // Controls.
        var $button = $(this);
        var $marker = $button.find('span.glyphicon-ok');

        // Gathered variables.
        var issue_type = $button.attr('data-issue-type');
        var show = $marker.hasClass('grey');

        // Add or remove the "grey" class depending on whether we are going to
        // show (not grey) or hide things (grey).
        if (show) {
            $marker.removeClass('grey');
        }
        else {
            $marker.addClass('grey');
        }

        // Apply filter condition.
        $('[control="issue-container"][data-issue-type="' + issue_type + '"]').applyFilterCondition(
            'issue-type',
            show
        );

    });

    $(document).on('click', 'button[control="proposer-type-toggle"]', function() {
        // Controls.
        var $button = $(this);
        var $marker = $button.find('span.glyphicon-ok');

        // Gathered variables.
        var proposer_type = $button.attr('data-proposer-type');
        var show = $marker.hasClass('grey');

        // Add or remove the "grey" class depending on whether we are going to
        // show (not grey) or hide things (grey).
        if (show) {
            $marker.removeClass('grey');
        }
        else {
            $marker.addClass('grey');
        }

        // Apply filter condition.
        $('[control="issue-container"][data-proposer-type="' + proposer_type + '"]').applyFilterCondition(
            'proposer-type',
            show
        );

    });

    // Make all the togglers do their things.
    $('[control="issue-type-toggle"][is-interesting="true"],[control="proposer-type-toggle"]').trigger('click');

    $(document).on('click', 'button[control="filter-expander"]', function() {
        // Controls.
        var $button = $(this);
        var $span = $button.parent();
        var $issue_filter_extra = $('[control="issue-filter-extra"]');

        // Figure out whether to show or hide.
        var show = !$span.hasClass('dropup');

        // Show or hide accordingly.
        if (show) {
            $span.addClass('dropup');
            $issue_filter_extra.show('fast');
        }
        else {
            $span.removeClass('dropup');
            $issue_filter_extra.hide('fast');
        }
    });

    $(document).on('keyup', 'input[control="issue-search"]', function() {
        var $issue_search = $(this);

        var search_strings = $issue_search.val().toLowerCase().trim().replace(/ +/g, ' ').split(' ');
        for (var i = 0; i < search_strings.length; i++) {
            var search_string = search_strings[i];
            //alert("!" + search_string + "!");
        }

        var $rows = $('[control="issue-container"]');

        // Start by declaring that none of the rows match the search criteria.
        // We'll then figure out which ones do.
        $rows.applyFilterCondition('search-text', false);

        // Run an anonymous function on each row that returns true if the
        // search matches the row. Those rows returning true are filtered out
        // and declared as fulfilling the filter condition of search-text.
        $rows.filter(function(i, row) {
            var $row = $(this);

            // Go through search strings and record how often they match.
            var hits = 0;
            for (var i = 0; i < search_strings.length; i++) {
                var search_string = search_strings[i];

                // An all-numeric search term means a search for issue number.
                // Partial searches by issue number don't make sense, since
                // people only search by issue number if they have the exact
                // number. Therefore, to prevent "6" from matching issues with
                // numbers 6, 26, 64, 261 and 687 (as examples), all-numeric
                // search terms get the special treatment of being matched
                // precisely to the issue number, as opposed to only having to
                // show up somewhere in the row's text.
                if (parseInt(search_string) == search_string) {
                    if ($row.attr('data-issue-num') == search_string) {
                        hits++;
                    }
                }
                else if ($row.text().toLowerCase().indexOf(search_string) > -1) {
                    hits++;
                }
            }

            // If search strings were found in the row as often as the number
            // of search strings were applied, we know that all of the search
            // strings can be found in the row, and so it is marked for
            // inclusion in the search results.
            return hits == search_strings.length;

        }).applyFilterCondition('search-text', true);
    });

    $(document).on('click', 'button[control="download-csv"]', function() {
        var issue_nums = [];
        $('[control="issue-container"]').each(function() {
            var $issue = $(this);
            if ($issue.is(':visible')) {
                issue_nums.push($issue.attr('data-issue-num'));
            }
        });
        var url = '/althingi/parliament/' + PARLIAMENT_NUM + '/issues/csv/?issue_nums=' + issue_nums.join();
        location.href = url;
    });
});
