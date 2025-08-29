$(document).ready(function() {
    $('.selectpicker').selectpicker();

    $('#refresh-btn').on('click', function(e) {
        e.preventDefault();
        refreshRadiosBatch(0);
    });
});

function refreshRadiosBatch(offset) {
    const BATCH_SIZE = 50;
    const $btn = $('#refresh-btn');
    const $progress = $('#refresh-progress');
    const $messages = $('#refresh-messages');

    $btn.prop('disabled', true);
    $progress.show();

    $.ajax({
        url: `/radios/refresh/ajax/?offset=${offset}&limit=${BATCH_SIZE}`,
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken')},
        success: function(data) {
            if (data.messages) {
                data.messages.forEach(msg => {
                    $messages.append('<div class="alert alert-info mt-1">'+msg+'</div>');
                });
            }
            if (data.total) {
                const percent = Math.min(100, Math.round((data.processed / data.total) * 100));
                $progress.css('width', percent + '%').attr('aria-valuenow', percent);
            }

            if (data.remaining > 0) {
                // Lancer le lot suivant
                refreshRadiosBatch(offset + BATCH_SIZE);
            } else {
                $btn.prop('disabled', false);
                $messages.append('<div class="alert alert-success mt-2">Actualisation terminée !</div>');
                $progress.css('width', '100%').attr('aria-valuenow', 100);
            }
        },
        error: function() {
            $messages.append('<div class="alert alert-danger mt-1">Erreur lors de l\'actualisation</div>');
            $btn.prop('disabled', false);
        }
    });
}

// Helper pour récupérer le cookie CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i=0; i<cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
