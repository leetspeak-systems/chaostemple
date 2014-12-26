
$(document).ready(function() {

    // Buttons: Fieldstates
    $(document).on('click', 'a[control="set-fieldstate"]', function() {
        $this = $(this);
        dossier_id = $this.data('dossier-id');
        fieldname = $this.data('fieldname');
        fieldstate = $this.data('fieldstate');

        $.jsonize({
            url: '/json/dossier/' + dossier_id + '/fieldstate/' + fieldname + '/',
            data: { 'fieldstate': fieldstate },
            done: function(data, textStatus) {
                $('a[control="set-fieldstate"][data-dossier-id=' + dossier_id + '][data-fieldname=' + fieldname + ']').each(function() {
                    $anchor = $(this);
                    $dropdown = $('button[control="dropdown-fieldstate"][data-id=' + dossier_id + '][data-fieldname=' + fieldname + ']');

                    if ($anchor.data('fieldstate') == data[fieldname]) {
                        $anchor.parent().addClass('active');

                        $dropdown.find('.display').text($anchor.text());
                        keepclass = ''; // This is needed in case two fieldstates have the same CSS class
                        for (var key in fieldstate_css[fieldname]) {
                            if (key == data[fieldname]) {
                                keepclass = fieldstate_css[fieldname][key];
                            }
                            $dropdown.removeClass('btn-' + fieldstate_css[fieldname][key]);
                        }
                        if (keepclass) {
                            $dropdown.addClass('btn-' + keepclass);
                        }
                    }
                    else {
                        $anchor.parent().removeClass('active');
                    }
                });
            }
        });
    });

    // Button: delete-dossier
    $(document).on('click', 'button[control="delete-dossier"]', function() {
        dossier_id = $(this).data('id');
        $('input#delete-dossier-id').val(dossier_id); // Store the dossier_id in the modal dialog
        $('div[control="delete-dossier-dialog"]').modal(); // Open the modal dialog
    });

    // Button: delete-dossier-confirmed
    $(document).on('click', 'button[control="delete-dossier-confirmed"]', function() {
        dossier_id = $('input#delete-dossier-id').val();

        $.jsonize({
            url: '/json/dossier/' + dossier_id + '/delete/',
            done: function(data, textStatus) {
                if (data.document_id) {
                    $('div[control="document"][data-id=' + data.document_id + '] .panel-footer').remove();
                }
                else if (data.review_id) {
                    $('div[control="review"][data-id=' + data.review_id + '] .panel-footer').remove();
                }
            }
        });
    });
});

