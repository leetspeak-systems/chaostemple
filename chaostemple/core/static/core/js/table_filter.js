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

        var $table = $(table_selector);

        $(this).delayKeyup(function() {
            var search_string = this.value.toUpperCase().split(' ');
            var $rows = $table.find('tr');

            if (this.value == '') {
                $rows.show();
                return;
            }

            $rows.hide();

            $rows.filter(function (i, row) {
                var $this = $(this);
                var hits = 0;
                for (var c = 0; c < search_string.length; c++) {
                    if ($this.text().toUpperCase().indexOf(search_string[c]) > -1) {
                        hits++;
                    }
                }
                return hits == search_string.length;
            }).show();
        }, 250);

    },
});
