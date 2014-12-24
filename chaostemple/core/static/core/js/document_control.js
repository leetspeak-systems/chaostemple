
$(document).ready(function() {

    // TODO: Generalize these click-functions into one and designate the field name as a parameter.

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
                            $dropdown.removeClass('btn-' + attention_css[key]);
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
                            $dropdown.removeClass('btn-' + knowledge_css[key]);
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

    // Button: set-supportstate
    $(document).on('click', 'a[control="set-supportstate"]', function() {
        dossier_id = $(this).data('dossier-id');
        supportstate = $(this).data('supportstate');

        $.jsonize({
            url: '/json/dossier/' + dossier_id + '/supportstate/',
            data: { supportstate: supportstate },
            done: function(data, textStatus) {
                $('a[control="set-supportstate"][data-dossier-id=' + dossier_id + ']').each(function() {
                    $anchor = $(this);
                    $dropdown = $('button[control="dropdown-supportstate"][data-id=' + dossier_id + ']');

                    if ($anchor.data('supportstate') == data.supportstate) {
                        $anchor.parent().addClass('active');

                        $dropdown.find('.display').text($anchor.text());
                        keepclass = ''; // This is needed in case two supportstates have the same CSS class
                        for (var key in support_css) {
                            if (key == data.supportstate) {
                                keepclass = support_css[key];
                            }
                            $dropdown.removeClass('btn-' + support_css[key]);
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

    // Button: set-proposalstate
    $(document).on('click', 'a[control="set-proposalstate"]', function() {
        dossier_id = $(this).data('dossier-id');
        proposalstate = $(this).data('proposalstate');

        $.jsonize({
            url: '/json/dossier/' + dossier_id + '/proposalstate/',
            data: { proposalstate: proposalstate },
            done: function(data, textStatus) {
                $('a[control="set-proposalstate"][data-dossier-id=' + dossier_id + ']').each(function() {
                    $anchor = $(this);
                    $dropdown = $('button[control="dropdown-proposalstate"][data-id=' + dossier_id + ']');

                    if ($anchor.data('proposalstate') == data.proposalstate) {
                        $anchor.parent().addClass('active');

                        $dropdown.find('.display').text($anchor.text());
                        keepclass = ''; // This is needed in case two proposalstates have the same CSS class
                        for (var key in proposal_css) {
                            if (key == data.proposalstate) {
                                keepclass = proposal_css[key];
                            }
                            $dropdown.removeClass('btn-' + proposal_css[key]);
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

