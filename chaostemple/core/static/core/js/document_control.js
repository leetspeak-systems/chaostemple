
$(document).ready(function() {
    $(".attention-state a").click(function() {
        $container = $(this).parent().parent().parent();

        parliament_num = $container.data('parliament-num');
        document_num = $container.data('document-num');
        attentionstate = $(this).data('attentionstate');
        dossier_id = $(this).parent().parent().data('id');

        $.jsonize(
            url = '/json/parliament/' + parliament_num + '/document/' + document_num + '/attentionstate/',
            data = { attentionstate: attentionstate },
            done = function(data, textStatus) {
                $dossier = $('.document-dossier[data-id=' + dossier_id + ']');
                $dossier.find('a').each(function(index) {
                    if ($(this).data('attentionstate') == data.attentionstate) {
                        $(this).addClass('selected');
                    }
                    else {
                        $(this).removeClass('selected');
                    }
                });
            }
        );
    });
});

