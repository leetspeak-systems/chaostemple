$(document).ready(function() {

    $.jsonizerStatus = function(args, status_code, default_message, row_number) {
        row_number = row_number || null;

        var $container = $('div.jsonizer-container');
        var $jsonizer = $container.find('div.jsonizer');
        var $row = null;

        // Set the mouse cursor
        if (status_code == 'transit') {
            $('body').addClass('wait');
        }
        else {
            $('body').removeClass('wait');
        }

        if (row_number == null) {
            $row = $container.find('#jsonizer-row-prototype').clone().attr('id', null);
        }
        else {
            $row = $container.find('div.jsonizer-row[data-row-number=' + row_number + ']');
        }

        var $light = $row.find('div.jsonizer-light');
        var $message = $row.find('div.jsonizer-message');

        // Check if valid status code sent
        var light_class = 'jsonizer-light ';
        switch (status_code) {
            case 'transit':
            case 'success':
            case 'failure':
                light_class += 'jsonizer-light-' + status_code;
                break;
            default:
                alert('Jsonizer: Invalid status code: ' + status_code);
        }

        // Set light according to status code
        $light.attr('class', light_class);

        // Set message
        switch (typeof(args.message)) {
            case 'undefined':
                $message.html(default_message);
                break;
            case 'object':
                if (args.message[status_code] == null) {
                    $message.html('Jsonizer: Missing status text for "' + status_code + '"');
                }
                else {
                    $message.html(args.message[status_code]);
                }
                break;
            default: // Presumably a string
                $message.html(args.message);
        }

        // Figure out the row number so that we can reference it later
        if (row_number == null) {
            var current_row_count = $jsonizer.find('.jsonizer-row').length;
            row_number = current_row_count + 1;
            $row.attr('data-row-number', row_number);

            // Add the new row
            $jsonizer.append($row);
        }

        $container.show();

        return row_number;
    }

    // Generalized function for handling JSON on our site
    $.jsonize = function(args) {

        if (args.type == null) {
            args.type = 'GET';
        }

        var row_number = $.jsonizerStatus(args, 'transit', 'Transmitting data...');

        result = $.ajax({
            url: args.url,
            type: args.type,
            data: args.data,
            dataType: 'json'
        }).done(function(data, textStatus) {
            var keys = Object.keys(data);
            if (data.ok && args.done) {
                args.done(data, textStatus);
                $.jsonizerStatus(args, 'success', 'Data successfully transmitted', row_number);
            }
            else {
                $.jsonizerStatus(args, 'failure', 'Data transmission failed', row_number);
                alert('Server error: ' + data.error);
                if (args.error != null) {
                    args.error(data, textStatus);
                }
            }
        }).fail(function(data, textStatus) {
            $.jsonizerStatus(args, 'failure', 'Data transmission failed', row_number);
            if (args.error != null) {
                args.error(data, textStatus);
            }
        });
        return result;
    }

    $('button#btn-jsonizer-clear').on('click', function() {
        var $container = $('div.jsonizer-container');
        var $jsonizer = $container.find('div.jsonizer');

        $jsonizer.children().remove();
        $container.hide();
    });
});
