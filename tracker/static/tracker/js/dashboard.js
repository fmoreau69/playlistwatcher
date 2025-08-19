let lastNewAppearances = 0;  // Pour garder en mémoire le compteur précédent
let lastStatus = "";         // Pour savoir quand on passe à "done"

function updateScanStatus() {
    fetch("/scan_status/")
        .then(response => response.json())
        .then(data => {
            let statusHtml = "";
            let scanBtn = document.getElementById("btn-scan");
            let stopBtn = document.getElementById("btn-stop");

            switch (data.status) {
                case "running":
                    statusHtml = '<span class="badge bg-info">Scan en cours...</span>';
                    if (scanBtn) scanBtn.disabled = true;
                    if (stopBtn) stopBtn.disabled = false;
                    break;
                case "stopped":
                    statusHtml = '<span class="badge bg-secondary">Scan interrompu ⏹️</span>';
                    if (scanBtn) scanBtn.disabled = false;
                    if (stopBtn) stopBtn.disabled = true;
                    break;
                case "done":
                    statusHtml = '<span class="badge bg-success">Dernier scan terminé ✅</span>';
                    if (scanBtn) scanBtn.disabled = false;
                    if (stopBtn) stopBtn.disabled = true;

                    // 👉 si on vient de terminer (transition depuis "running" ou autre)
                    if (lastStatus !== "done") {
                        let totalNew = parseInt(data.extra_info || "0");
                        if (totalNew > 0) {
                            showNotification(`✅ Scan terminé : ${totalNew} nouvelle(s) apparition(s) trouvée(s) !`);
                        } else {
                            showNotification(`✅ Scan terminé : aucune nouvelle apparition.`);
                        }
                    }
                    break;
                case "error":
                    statusHtml = '<span class="badge bg-danger">Erreur pendant le scan ❌</span>';
                    if (scanBtn) scanBtn.disabled = false;
                    if (stopBtn) stopBtn.disabled = true;
                    break;
                default:
                    statusHtml = '<span class="badge bg-light text-dark">En attente</span>';
                    if (scanBtn) scanBtn.disabled = false;
                    if (stopBtn) stopBtn.disabled = true;
            }
            document.getElementById("scan-status").innerHTML = statusHtml;

            // Gestion du compteur de nouvelles apparitions pendant le scan
            let newCount = parseInt(data.extra_info || "0");
            if (newCount > lastNewAppearances) {
                let diff = newCount - lastNewAppearances;
                showNotification(`✨ ${diff} nouvelle(s) apparition(s) détectée(s) !`);
                lastNewAppearances = newCount;
            }

            lastStatus = data.status; // mémorise le dernier état
        });
}

// Fonction générique pour afficher une notification
function showNotification(message) {
    let notification = document.createElement("div");
    notification.className = "alert alert-success alert-dismissible fade show";
    notification.role = "alert";
    notification.innerHTML = message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';

    document.body.appendChild(notification);

    // Supprime automatiquement après 5 secondes
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Auto-refresh toutes les 5s
setInterval(updateScanStatus, 5000);

// Appel initial dès le chargement de la page
document.addEventListener("DOMContentLoaded", updateScanStatus);
