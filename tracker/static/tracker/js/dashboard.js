let lastNewAppearances = 0;
let lastScanStatus = "";
let lastDiscoverStatus = "";

// Mise à jour des titres selon l'artiste sélectionné
document.addEventListener("DOMContentLoaded", function() {
    const artistSelect = document.getElementById("artist-select");
    if (artistSelect) {
        artistSelect.addEventListener("change", function() {
            const artistId = this.value;
            fetch(`/artist/${artistId}/tracks/`)  // route Django qui renvoie les tracks en JSON
                .then(resp => resp.json())
                .then(data => {
                    const trackSelect = document.getElementById("track-select");
                    trackSelect.innerHTML = "";  // vide l'ancien contenu
                    data.forEach(track => {
                        const option = document.createElement("option");
                        option.value = track.id;
                        option.textContent = track.name;
                        trackSelect.appendChild(option);
                    });
                });
        });
    }
});

// Mise à jour de l'état de l'accordéon "Controls"
document.addEventListener("DOMContentLoaded", function() {
    const controlsBtn = document.querySelector('[data-bs-target="#collapseControls"]');
    const controlsCollapse = document.getElementById("collapseControls");

    if (controlsBtn && controlsCollapse) {
        // Récupérer l'état enregistré
        const savedState = localStorage.getItem("controlsExpanded");
        if (savedState === "true") {
            controlsCollapse.classList.add("show");
            controlsBtn.setAttribute("aria-expanded", "true");
        } else {
            controlsCollapse.classList.remove("show");
            controlsBtn.setAttribute("aria-expanded", "false");
        }

        // Écouter les changements d'ouverture/fermeture
        controlsCollapse.addEventListener("shown.bs.collapse", () => {
            localStorage.setItem("controlsExpanded", "true");
        });
        controlsCollapse.addEventListener("hidden.bs.collapse", () => {
            localStorage.setItem("controlsExpanded", "false");
        });
    }
});

// Met à jour le statut du scan et de la découverte
function updateStatuses() {
    fetch("/scan_status/")
        .then(resp => resp.json())
        .then(data => updateScan(data));

    fetch("/discover_status/")
        .then(resp => resp.json())
        .then(data => updateDiscover(data));
}

// Mise à jour du scan
function updateScan(data) {
    let statusHtml = "";
    const scanBtn = document.getElementById("btn-scan");
    const stopBtn = document.getElementById("btn-stop");
    const progressBar = document.getElementById("scan-progress");

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
            if (lastScanStatus !== "done") {
                showNotification(`✅ Scan terminé : ${data.extra_json?.created || 0} nouvelle(s) apparition(s) !`);
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

    // Notification pour nouvelles apparitions
    const newCount = data.extra_json?.created || 0;
    if (newCount > lastNewAppearances) {
        const diff = newCount - lastNewAppearances;
        showNotification(`✨ ${diff} nouvelle(s) apparition(s) détectée(s) !`);
        lastNewAppearances = newCount;
    }

    // Progression du scan
    if (progressBar && data.extra_json?.total && data.extra_json?.current) {
        const percent = Math.floor((data.extra_json.current / data.extra_json.total) * 100);
        progressBar.style.width = percent + "%";
        progressBar.setAttribute("aria-valuenow", percent);
        progressBar.innerText = percent + "%";
    }

    lastScanStatus = data.status;
}

// Mise à jour de la découverte
function updateDiscover(data) {
    let statusHtml = "";
    const discoverBtn = document.getElementById("btn-discover");
    const stopBtn = document.getElementById("btn-stop-discover");
    const progressBar = document.getElementById("discover-progress");

    switch (data.status) {
        case "running":
            statusHtml = '<span class="badge bg-info">Découverte en cours...</span>';
            if (discoverBtn) discoverBtn.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
            break;
        case "stopped":
            statusHtml = '<span class="badge bg-secondary">Découverte interrompue ⏹️</span>';
            if (discoverBtn) discoverBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
            break;
        case "done":
            statusHtml = '<span class="badge bg-success">Dernière découverte terminée ✅</span>';
            if (discoverBtn) discoverBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
            if (lastDiscoverStatus !== "done") {
                showNotification(`✅ Découverte terminée : ${data.extra_info}`);
            }
            break;
        case "error":
            statusHtml = '<span class="badge bg-danger">Erreur pendant la découverte ❌</span>';
            if (discoverBtn) discoverBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
            break;
        default:
            statusHtml = '<span class="badge bg-light text-dark">En attente</span>';
            if (discoverBtn) discoverBtn.disabled = false;
            if (stopBtn) stopBtn.disabled = true;
    }

    document.getElementById("discover-status").innerHTML = statusHtml;

    // Progression de la découverte (affichage du compteur exploré)
    if (progressBar) {
        const explored = data.extra_json?.explored || 0;
        const maxDisplay = 100; // largeur max arbitraire pour la progress bar
        const widthPercent = Math.min(explored, maxDisplay);
        progressBar.style.width = widthPercent + "%";
        progressBar.setAttribute("aria-valuenow", widthPercent);
        progressBar.innerText = `${explored} explorées`;
    }

    lastDiscoverStatus = data.status;
}

// Notification générique
function showNotification(message) {
    const notification = document.createElement("div");
    notification.className = "alert alert-success alert-dismissible fade show";
    notification.role = "alert";
    notification.innerHTML = message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
    document.body.appendChild(notification);
    setTimeout(() => { notification.remove(); }, 5000);
}

// Auto-refresh toutes les 5s
setInterval(updateStatuses, 5000);
updateStatuses();
