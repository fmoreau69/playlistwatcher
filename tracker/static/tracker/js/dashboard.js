let lastNewAppearances = 0;
let lastScanStatus = "";
let lastDiscoverStatus = "";

// ===== Mise à jour des titres selon l'artiste sélectionné =====
document.addEventListener("DOMContentLoaded", function() {
    const artistSelect = document.getElementById("artist-select");
    if (artistSelect) {
        artistSelect.addEventListener("change", function() {
            const artistId = this.value;
            fetch(`/artist/${artistId}/tracks/`)
                .then(resp => resp.json())
                .then(data => {
                    const trackSelect = document.getElementById("track-select");
                    trackSelect.innerHTML = "";
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

// ===== Persistance générique de l'état des accordéons =====
document.addEventListener("DOMContentLoaded", function () {
    const allAccordions = document.querySelectorAll(".accordion");
    allAccordions.forEach(accordion => {
        const collapses = accordion.querySelectorAll(":scope > .accordion-item > .accordion-collapse");
        collapses.forEach(coll => {
            if (!coll.id) return;
            const key = "accordionState:" + coll.id;
            const saved = localStorage.getItem(key);
            const toggles = Array.from(coll.parentElement.querySelectorAll(`[data-bs-target="#${coll.id}"], [href="#${coll.id}"]`));

            if (saved === "open") {
                const prevTransition = coll.style.transition;
                coll.style.transition = "none";
                coll.classList.add("show");
                toggles.forEach(btn => {
                    btn.classList.remove("collapsed");
                    btn.setAttribute("aria-expanded", "true");
                });
                setTimeout(() => { coll.style.transition = prevTransition || ""; }, 20);
            } else if (saved === "closed") {
                coll.classList.remove("show");
                toggles.forEach(btn => {
                    btn.classList.add("collapsed");
                    btn.setAttribute("aria-expanded", "false");
                });
            }

            coll.addEventListener("shown.bs.collapse", () => localStorage.setItem(key, "open"));
            coll.addEventListener("hidden.bs.collapse", () => localStorage.setItem(key, "closed"));
        });
    });
});

// ===== Vérification du client Spotify =====
function checkSpotifyStatus(callback) {
    fetch("/spotify_status/")
        .then(resp => resp.json())
        .then(data => {
            if (!data.ok) {
                showNotification("⚠️ " + (data.message || "Spotify non disponible"));
            } else if (callback) {
                callback();
            }
        })
        .catch(() => {
            showNotification("⚠️ Impossible de vérifier l'état Spotify");
        });
}

// ===== Mise à jour des statuts =====
function updateStatuses() {
    fetch("/scan_status/")
        .then(resp => resp.json())
        .then(data => updateScan(data));

    fetch("/discover_status/")
        .then(resp => resp.json())
        .then(data => updateDiscover(data));
}

// ===== Mise à jour du scan =====
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

// ===== Mise à jour de la découverte =====
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

    // Progression de la découverte
    if (progressBar) {
        const explored = data.extra_json?.explored || 0;
        const maxDisplay = 100;
        const widthPercent = Math.min(explored, maxDisplay);
        progressBar.style.width = widthPercent + "%";
        progressBar.setAttribute("aria-valuenow", widthPercent);
        progressBar.innerText = `${explored} explorées`;
    }

    lastDiscoverStatus = data.status;
}

// ===== Notification générique =====
function showNotification(message) {
    const notification = document.createElement("div");
    notification.className = "alert alert-success alert-dismissible fade show";
    notification.role = "alert";
    notification.innerHTML = message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
    document.body.appendChild(notification);
    setTimeout(() => { notification.remove(); }, 5000);
}

// ===== Boutons Scan avec vérification Spotify =====
document.addEventListener("DOMContentLoaded", () => {
    const scanBtn = document.getElementById("btn-scan");
    if (scanBtn) {
        scanBtn.addEventListener("click", () => {
            checkSpotifyStatus(() => {
                fetch("/run_scan_playlists/")
                    .then(() => showNotification("Scan lancé en arrière-plan ⏳"));
            });
        });
    }
});

// ===== Boutons Discover avec vérification Spotify =====
document.addEventListener("DOMContentLoaded", () => {
    const discoverBtn = document.getElementById("btn-discover");
    if (discoverBtn) {
        discoverBtn.addEventListener("click", () => {
            checkSpotifyStatus(() => {
                fetch("/run_discover_playlists/")
                    .then(() => showNotification("Découverte lancée en arrière-plan ⏳"));
            });
        });
    }
});

// ===== Auto-refresh toutes les 5s =====
setInterval(updateStatuses, 5000);
updateStatuses();
