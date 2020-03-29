
$(document).ready(function() {

    // Button: create-dossier
    $(document).on('click', 'button[control="create-dossier"]', function() {
        let $this = $(this);
        let doc_num = $this.data('doc-num');
        let log_num = $this.data('log-num');

        // Construct URL based on whether the dossier belongs to a document or
        // review. This distinction is only important because they are
        // designated by different kinds of IDs (doc_num and log_num,
        // respectively).
        let url = '/dossier/parliament/' + PARLIAMENT_NUM;
        if (doc_num) {
            url += '/document/' + doc_num;
        }
        else if (log_num) {
            url += '/review/' + log_num;
        }
        else {
            // This makes no sense. Let's just do nothing.
            return;
        }
        url += '/create/';

        $.jsonize({
            message: {
                'transit': 'Creating dossier...',
                'success': 'Dossier created.',
                'failure': 'Dossier creation failed!',
            },
            url: url,
            done: function(data, textStatus) {
                if (data.document_id) {
                    $('div[control="document-container"][data-document-id=' + data.document_id + ']').html(data.html);
                }
                else if (data.review_id) {
                    $('div[control="review-container"][data-review-id=' + data.review_id + ']').html(data.html);
                }
            }
        });
    });

    // Button: delete-dossier
    $(document).on('click', 'button[control="delete-dossier"]', function() {
        let $this = $(this);
        $('input#delete-dossier-doc-num').val($this.data('doc-num'));
        $('input#delete-dossier-log-num').val($this.data('log-num'));
        $('div[control="delete-dossier-dialog"]').modal();
    });

    // Button: delete-dossier-confirmed
    $(document).on('click', 'button[control="delete-dossier-confirmed"]', function() {
        let doc_num = $('input#delete-dossier-doc-num').val();
        let log_num = $('input#delete-dossier-log-num').val();

        // Construct URL based on whether the dossier belongs to a document or
        // review. This distinction is only important because they are
        // designated by different kinds of IDs (doc_num and log_num,
        // respectively).
        let url = '/dossier/parliament/' + PARLIAMENT_NUM;
        if (doc_num) {
            url += '/document/' + doc_num;
        }
        else if (log_num) {
            url += '/review/' + log_num;
        }
        else {
            // This makes no sense. Let's just do nothing.
            return;
        }
        url += '/delete/';

        $.jsonize({
            message: {
                'transit': 'Deleting dossier...',
                'success': 'Dossier deleted.',
                'failure': 'Dossier deletion failed!',
            },
            url: url,
            done: function(data, textStatus) {
                if (data.document_id) {
                    $('div[control="document-container"][data-document-id=' + data.document_id + ']').html(data.html);
                }
                else if (data.review_id) {
                    $('div[control="review-container"][data-review-id=' + data.review_id + ']').html(data.html);
                }
            }
        });
    });
});
