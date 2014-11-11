
function showAddButton(document_id, show_button) {
        $btn_container = $('.document[data-document-id=' + document_id + '] .btn-add-dossier-container');
        if (show_button) {
            $btn_container.removeClass('btn-add-dossier-container-hidden');
        }
        else {
            $btn_container.addClass('btn-add-dossier-container-hidden');
        }
}

function configureAddButtons() {
    $('.dossier-container').each(function() {
        document_id = $(this).data('document-id');
        show_button = $(this).find('.dossier[data-user-id=' + USER_ID + ']').length == 0;
        showAddButton(document_id, show_button);
    });
}

function obtainDossier(document_id) {
    $.get('/stub/document/' + document_id + '/dossier/', function(data, textStatus) {
        $data = $(data);
        dossier_id = $data.attr('data-id');
        if ($('.dossier[data-id=' + dossier_id + ']').length == 0) {
            $data.appendTo($('.dossier-container[data-document-id=' + document_id + ']'));
            showAddButton(document_id, false);
        }
    });
}

function deleteDossier(dossier_id) {
    $.jsonize({
        url: '/json/dossier/' + dossier_id + '/delete/',
        done: function(data, textStatus) {
            $dossier = $('.dossier[data-id=' + dossier_id + ']');
            document_id = $dossier.attr('data-document-id');

            $dossier.remove();
            showAddButton(document_id, true);
        }
    });
}

function setAttention(dossier_id, attentionstate) {
    $dossier = $('.dossier[data-id=' + dossier_id + ']');
    $dossier.find('a').each(function(index) {
        if ($(this).data('attentionstate') == attentionstate) {
            $(this).addClass('selected');
        }
        else {
            $(this).removeClass('selected');
        }
    });
}

$(document).ready(function() {
    configureAddButtons();

    $('.documents').on('click', '.attention-state a', function() {
        $container = $(this).parent().parent().parent();

        dossier_id = $(this).parent().parent().data('id');
        attentionstate = $(this).data('attentionstate');

        $.jsonize({
            url: '/json/dossier/' + dossier_id + '/attentionstate/',
            data: { attentionstate: attentionstate },
            done: function(data, textStatus) {
                setAttention(dossier_id, data.attentionstate);
            }
        });
    });

    $(document).on('click', '.btn-add-dossier', function() {
        $container = $(this).parent().parent();

        document_id = $container.data('document-id');

        obtainDossier(document_id);

    });

    $(document).on('click', '.btn-delete-dossier', function() {
        $container = $(this).parent().parent();

        dossier_id = $container.data('id');

        deleteDossier(dossier_id);
    });
});

