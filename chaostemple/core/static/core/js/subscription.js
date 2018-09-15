
/*
 * This file assumes that the list 'subscriptions' exists and is of the
 * following format:
 *
 * subscriptions = [
 *     {
 *         'type': 'committee',
 *         'id': 2,
 *     },
 * ];
 *
 * If such a list does not exist, this file should not be included in the
 * first place.
 */

$(document).ready(function() {

    // Go through the subscriptions to set the initial states of their
    // corresponding buttons accordingly.
    for (i in subscriptions) {
        var type = subscriptions[i]['type'];
        var id = subscriptions[i]['id'];

        var $button = $('button[control="toggle-subscription"]'
            + '[data-type="' + type + '"]'
            + '[data-id="' + id + '"]'
        );

        $button.attr('data-subscribed', 'true');
        $button.find('[control="subscription-icon"]').removeClass('grey');
    }

    $('button[control="toggle-subscription"]').on('click', function() {
        var $button = $(this);

        var type = $button.attr('data-type');
        var id = $button.attr('data-id');

        if ($button.attr('data-subscribed') == 'true') {
            message = {
                'transit': 'Unsubscribing...',
                'success': 'Unsubscribed',
                'failure': 'Unsubscribing failed!',
            };
        }
        else {
            message = {
                'transit': 'Subscribing...',
                'success': 'Subscribed',
                'failure': 'Subscribing failed!',
            };
        }

        $.jsonize({
            message: message,
            url: '/json/subscription/toggle/' + type + '/' + id + '/',
            done: function(data, textStatus) {
                var subscribed = data['subscribed'];
                if (subscribed == null) {
                    console.error('Subscription result was null which should not happen');
                }

                $button.attr('data-subscribed', (subscribed ? 'true' : ''));
                if (subscribed) {
                    $button.find('[control="subscription-icon"]').removeClass('grey');
                }
                else {
                    $button.find('[control="subscription-icon"]').addClass('grey');
                }
            },
        });

    });

});
