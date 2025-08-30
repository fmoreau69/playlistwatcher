$(document).ready(function() {
    $('.selectpicker').selectpicker();

    const $btn = $('#refresh-btn');
    const $progress = $('#refresh-progress');
    const $messages = $('#refresh-messages');
    const $currentCountry = $('#current-country');

    // Initialisation de la modal Bootstrap 5
    const progressModalEl = document.getElementById('progressModal');
    const progressModal = new bootstrap.Modal(progressModalEl, {
        backdrop: 'static', // empêche de fermer en cliquant en dehors
        keyboard: false     // empêche d'utiliser Echap
    });

    if ($btn.length && $progress.length && $messages.length) {
        $btn.on('click', function(e) {
            e.preventDefault();
            $messages.empty();
            $currentCountry.text('');
            $progress.css('width', '0%').attr('aria-valuenow', 0);

            const selectedCountries = $('#country').val() || [];

            // Affiche la popup
            progressModal.show();

            $btn.prop('disabled', true);

            // Lancer l'actualisation côté serveur
            $.ajax({
                url: '/radios/refresh/start/',
                method: 'POST',
                data: { countries: selectedCountries },
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                success: function(data) {
                    if (data.task_id) {
                        pollProgress(data.task_id);
                    } else {
                        $messages.append('<div class="alert alert-danger mt-1">Impossible de démarrer l\'actualisation.</div>');
                        $btn.prop('disabled', false);
                        progressModal.hide();
                    }
                },
                error: function() {
                    $messages.append('<div class="alert alert-danger mt-1">Erreur lors du démarrage de l\'actualisation.</div>');
                    $btn.prop('disabled', false);
                    progressModal.hide();
                }
            });
        });
    }

    function pollProgress(taskId) {
        $.ajax({
            url: '/radios/refresh/progress/',
            method: 'GET',
            data: { task_id: taskId },
            success: function(data) {
                // Affiche le pays courant
                if (data.current_country) {
                    $currentCountry.text('Actualisation en cours : ' + data.current_country);
                }

                // Affiche les messages
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        $messages.append('<div class="alert alert-info mt-1">' + msg + '</div>');
                    });
                }

                // Met à jour la barre de progression
                if (data.total) {
                    const percent = Math.min(100, Math.round((data.processed / data.total) * 100));
                    $progress.css('width', percent + '%').attr('aria-valuenow', percent);
                    $progress.text(percent + '%');
                }

                if (data.finished) {
                    $btn.prop('disabled', false);
                    $currentCountry.text('');
                    $messages.append('<div class="alert alert-success mt-2">Actualisation terminée !</div>');
                    $progress.css('width', '100%').attr('aria-valuenow', 100);
                    $progress.text('100%');
                    setTimeout(() => progressModal.hide(), 1000); // ferme la popup après 1s
                } else {
                    // Requête suivante avec un léger délai
                    setTimeout(() => pollProgress(taskId), 1000);
                }
            },
            error: function() {
                $messages.append('<div class="alert alert-danger mt-1">Erreur lors du suivi de la progression.</div>');
                $btn.prop('disabled', false);
                progressModal.hide();
            }
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
