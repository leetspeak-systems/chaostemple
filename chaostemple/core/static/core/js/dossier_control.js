
$(document).ready(function() {

    // Processing non-standard events is apparently not supported by jQuery,
    // so we'll have to deal with the editor in its native, non-jQuery form.
    let editor = document.querySelector('.prosearea-editor');

    // Other controls.
    let $dossier_status = $('span[control="dossier-status"]');
    let $dossier_save = $('button[control="dossier-save"]');

    // Hook up save-button.
    $dossier_save.on('click', function() {
        editor.view.save();
    });

    // Save changed content.
    editor.addEventListener('save', function(evt) {
        var $this = $(this);
        var dossier_id = $this.attr('data-dossier-id');
        var notes = $this.val();

        $.jsonize({
            message: {
                'transit': 'Saving notes...',
                'success': 'Notes saved.',
                'failure': 'Failed to save notes!',
            },
            type: 'POST',
            url: '/dossier/' + dossier_id + '/set-notes/',
            data: { 'notes': notes },
            done: function(data, textStatus) {
                if (data.ok) {
                    // Notify user of success.
                    $dossier_status.html(MSG_STATUS_SAVED);

                    $dossier_save.attr('disabled', true);
                }
                else {
                    // Notify user that something went wrong.
                    $dossier_status.html(MSG_STATUS_ERROR);

                    $dossier_save.attr('disabled', false);
                }
            },
        });
    });

    // Notify user that content changed and has not yet been saved.
    editor.addEventListener('changed', function(evt) {
        $dossier_status.html(MSG_STATUS_UNSAVED);

        $dossier_save.attr('disabled', false);
    });

});
