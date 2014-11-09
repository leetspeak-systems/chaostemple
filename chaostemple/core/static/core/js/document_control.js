
$(document).ready(function() {
    $(".attention-state a").click(function() {
        $container = $(this).parent().parent();
        parliament_num = $container.data('parliament-num');
        document_num = $container.data('document-num');
        attentionstate = $(this).data('attentionstate');

        $.jsonize(
            url = '/json/parliament/' + parliament_num + '/document/' + document_num + '/attentionstate/',
            data = { attentionstate: attentionstate },
            done = function(data, textStatus) {
                $dossier = $('.document-dossier[data-parliament-num=' + parliament_num + '][data-document-num=' + document_num + ']');
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

