
$(document).ready(function() {

    // Button: set-attentionstate
    $(document).on('click', 'a[control="set-attentionstate"]', function() {
        dossier_id = $(this).data('dossier-id');
        attentionstate = $(this).data('attentionstate');

        $.jsonize({
            url: '/json/dossier/' + dossier_id + '/attentionstate/',
            data: { attentionstate: attentionstate },
            done: function(data, textStatus) {
                $('a[control="set-attentionstate"][data-dossier-id=' + dossier_id + ']').each(function() {
                    $anchor = $(this);
                    $dropdown = $('button[control="dropdown-attentionstate"][data-id=' + dossier_id + ']');

                    if ($anchor.data('attentionstate') == data.attentionstate) {
                        $anchor.parent().addClass('active');

                        $dropdown.find('.display').text($anchor.text());
                        keepclass = ''; // This is needed in case two attentionstates have the same CSS class
                        for (var key in attention_css) {
                            if (key == data.attentionstate) {
                                keepclass = attention_css[key];
                            }
                            $dropdown.removeClass(attention_css[key]);
                        }
                        if (keepclass) {
                            $dropdown.addClass(keepclass);
                        }
                    }
                    else {
                        $anchor.parent().removeClass('active');
                    }
                });
            }
        });
    });

    // Button: set-knowledgestate
    $(document).on('click', 'a[control="set-knowledgestate"]', function() {
        dossier_id = $(this).data('dossier-id');
        knowledgestate = $(this).data('knowledgestate');

        $.jsonize({
            url: '/json/dossier/' + dossier_id + '/knowledgestate/',
            data: { knowledgestate: knowledgestate },
            done: function(data, textStatus) {
                $('a[control="set-knowledgestate"][data-dossier-id=' + dossier_id + ']').each(function() {
                    $anchor = $(this);
                    $dropdown = $('button[control="dropdown-knowledgestate"][data-id=' + dossier_id + ']');

                    if ($anchor.data('knowledgestate') == data.knowledgestate) {
                        $anchor.parent().addClass('active');

                        $dropdown.find('.display').text($anchor.text());
                        keepclass = ''; // This is needed in case two knowledgestates have the same CSS class
                        for (var key in knowledge_css) {
                            if (key == data.knowledgestate) {
                                keepclass = knowledge_css[key];
                            }
                            $dropdown.removeClass(knowledge_css[key]);
                        }
                        if (keepclass) {
                            $dropdown.addClass(keepclass);
                        }
                    }
                    else {
                        $anchor.parent().removeClass('active');
                    }
                });
            }
        });
    });

    // Button: add-dossier
    $(document).on('click', 'button[control="add-dossier"]', function() {
        document_id = $(this).data('document-id');

        $.get('/stub/document/' + document_id + '/dossier/', function(data, textStatus) {
            $data = $(data);
            dossier_id = $data.attr('data-id');
            if ($('div[control="dossier"][data-id=' + dossier_id + ']').length == 0) {
                $add_dossier = $('div[control="document"][data-id=' + document_id + '] button[control="add-dossier"]');
                $add_dossier.before($data);
                $add_dossier.hide();
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
                $('div[control="dossier"][data-id=' + dossier_id + ']').remove();
                $('div[control="document"][data-id=' + data.document_id + '] button[control="add-dossier"]').show();
            }
        });
    });
});

