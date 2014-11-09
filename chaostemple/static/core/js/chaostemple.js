
// Generalized function for handling JSON on our site
$.jsonize = function(url, data, done, error) {
    result = $.get(
        url,
        data,
        dataType = 'json'
    ).done(function(data, textStatus) {
        data = $.parseJSON(data);
        if (data.ok) {
            done(data, textStatus);
        }
        else {
            alert('Server error: ' + data.error);
            if (error != null) {
                error(data, textStatus);
            }
        }
    });
    return result;
}

// Set focus on first text field on page, if it exists
$(document).ready(function() {
    $("form input[type='text']").focus();
});

