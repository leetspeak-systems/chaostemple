jQuery.fn.extend({
    delayKeyup: function(callback, ms) {
        var timer = 0;
        $(this).keyup(function() {                   
            clearTimeout(timer);
            timer = setTimeout(callback.bind(this), ms);
        });
        return $(this);
    },
});

jQuery.fn.extend({
    tableFilter: function(table_selector) {

        var $this = $(this);

        var $table = $(table_selector);
        var $inputs = $this.find('input');

        var search_function = function() {

            // Compile search string.
            var search_strings = [];
            var issue_types = []

            $inputs.each(function() {
                var $input = $(this);
                var input_type = $input.attr('type');
                var input_checked = $input.prop('checked');

                // The checkboxes need to be OR-ed with each other, but search text AND-ed.
                if (input_type == 'checkbox' && input_checked) {
                    issue_types = issue_types.concat($input.val().toUpperCase());
                }
                else if (input_type == 'text') {
                    search_strings = search_strings.concat($input.val().toUpperCase().split(' '))
                }
            });

            var $rows = $table.find('tr');

            if (this.value == '') {
                $rows.show();
                return;
            }

            $rows.hide();

            $rows.filter(function(i, row) {
                var $this = $(this);
                var issue_types_matched = true;
                var hits = 0;
                if (issue_types.length > 0) {
                    issue_types_matched = false;
                    // We only need to match one of the iteams in variable issue_types.
                    for (var c = 0; c < issue_types.length; c++) {
                        if ($this.find('span[control="issue-type"]').text().toUpperCase() == issue_types[c]) {
                            issue_types_matched = true;
                            break;
                        }
                    }
                }
                for (var c = 0; c < search_strings.length; c++) {
                    if ($this.text().toUpperCase().indexOf(search_strings[c]) > -1) {
                        hits++;
                    }
                }
                return hits == search_strings.length && issue_types_matched;
            }).show();
        };

        $inputs.each(function() {
            var $input = $(this);
            var input_type = $input.attr('type');

            if (input_type == 'text') {
                $(this).delayKeyup(search_function, 250);
            }
            else if (input_type == 'checkbox') {
                $(this).click(search_function);
            }
        });
    },
});
