
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

function reloadSortable() {
    // Make things sortable
    $('.sortable').sortable({ handle: '.handle' });
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

    reloadSortable();
});

// Prevent anchors used as buttons from scrolling to top of page
$(document).on('click', 'a[href="#"]', function(event) {
    event.preventDefault();
});

// Prevent dropdowns with checkboxes from closing when a checkbox inside is clicked
$(document).on('click', 'ul.checkboxes li', function(event) {
    event.stopPropagation();
});

// Keep track of URL parameters for easy JavaScript access
var url_params = {};
query_index = location.href.indexOf('?');
if (query_index >= 0) {
    var_values = location.href.substr(query_index + 1).split('&');
    for (i = 0; i < var_values.length; i++) {
        var_value = var_values[i].split('=');
        url_params[var_value[0]] = var_value[1] || null;
        delete var_value;
    }
    delete var_values;
    delete i;
}
delete query_index;

