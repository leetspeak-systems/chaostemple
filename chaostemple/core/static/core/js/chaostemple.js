
// Generalized function for handling JSON on our site
$.jsonize = function(args) {
    result = $.get(
        args.url,
        args.data,
        dataType = 'json'
    ).done(function(data, textStatus) {
        var data = $.parseJSON(data);
        if (data.ok && args.done) {
            args.done(data, textStatus);
        }
        else {
            alert('Server error: ' + data.error);
            if (args.error != null) {
                args.error(data, textStatus);
            }
        }
    });
    return result;
}

// Set focus on first text field on page, if it exists
$(document).ready(function() {
    $("form input[type='text']").focus();
});

$(document).on('click', 'a[href="#"]', function(event) {
    event.preventDefault();
});

