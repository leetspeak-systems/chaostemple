
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

// Generalized function for handling JSON on our site
$.jsonize = function(args) {
    if (args.type == null) {
        args.type = 'GET';
    }
    result = $.ajax({
        url: args.url,
        type: args.type,
        data: args.data,
        dataType: 'json'
    }).done(function(data, textStatus) {
        var keys = Object.keys(data);
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

$(document).ready(function() {
    // Set focus on first text field on page, if it exists
    $("form input[type='text']").focus();

    // Automatically send CSRF token if needed
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        }
    });

    // Make things sortable
    $('.sortable').sortable();
});

// Prevent anchors used as buttons from scrolling to top of page
$(document).on('click', 'a[href="#"]', function(event) {
    event.preventDefault();
});

