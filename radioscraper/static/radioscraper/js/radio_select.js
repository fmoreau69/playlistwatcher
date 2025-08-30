$(document).ready(function() {
    $('.selectpicker').selectpicker();

    const $btn = $('#refresh-btn');
    const $progress = $('#refresh-progress');
    const $messages = $('#refresh-messages');
    const $currentCountry = $('#current-country');

    if ($btn.length && $progress.length && $messages.length) {
        $btn.on('click', function(e) {
            e.preventDefault();
            $messages.empty();
            $currentCountry.text('');
            $progress.css('width', '0%').attr('aria-valuenow', 0).show();

            const selectedCountries = $('#country').val() || [];
            refreshRadiosBatch(0, selectedCountries, 0);
        });
    }

    function refreshRadiosBatch(offset, countries, countryIndex) {
        const BATCH_SIZE = 50;
        const country = countries[countryIndex] || null;

        $btn.prop('disabled', true);

        $.ajax({
            url: '/radios/refresh/ajax/',
            method: 'POST',
            data: {
                offset: offset,
                limit: BATCH_SIZE,
                country: country,
                country_index: countryIndex
            },
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            success: function(data) {
                // Afficher le pays courant
                if (data.current_country) {
                    $currentCountry.text('Actualisation en cours : ' + data.current_country);
                }

                // Afficher les messages (optionnel : on peut supprimer si trop verbeux)
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        $messages.append('<div class="alert alert-info mt-1">' + msg + '</div>');
                    });
                }

                // Mise à jour de la barre de progression globale du batch courant
                if (data.total) {
                    const percent = Math.min(100, Math.round((data.processed / data.total) * 100));
                    $progress.css('width', percent + '%').attr('aria-valuenow', percent);
                    $progress.text(percent + '%');
                }

                // Passer au batch suivant ou au pays suivant
                if (data.remaining > 0) {
                    refreshRadiosBatch(data.next_offset, countries, countryIndex);
                } else if (data.next_country_index < countries.length) {
                    refreshRadiosBatch(0, countries, data.next_country_index);
                } else {
                    // Terminé
                    $btn.prop('disabled', false);
                    $currentCountry.text('');
                    $messages.append('<div class="alert alert-success mt-2">Actualisation terminée !</div>');
                    $progress.css('width', '100%').attr('aria-valuenow', 100);
                    $progress.text('100%');
                }
            },
            error: function() {
                $messages.append('<div class="alert alert-danger mt-1">Erreur lors de l\'actualisation</div>');
                $btn.prop('disabled', false);
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
