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
        });
}

// Auto-refresh toutes les 5s
setInterval(updateScanStatus, 5000);

// Appel initial dès le chargement de la page
document.addEventListener("DOMContentLoaded", updateScanStatus);
