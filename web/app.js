/* ========================================================= */
/* INTER-VESSEL SECURITY CENTER                               */
/* ========================================================= */

/*
 * Flask API expected:
 *
 * GET  /api/devices
 * GET  /api/logs
 *
 *
 * Device format:
 *
 * {
 *     "id": "VESSEL-01",
 *     "ip": "192.168.1.10",
 *     "status": "ONLINE",
 *     "last_seen": "2026-09-21T14:32:08"
 * }
 *
 *
 * Log format:
 *
 * {
 *     "timestamp": "2026-09-21T14:32:08",
 *     "device": "VESSEL-01",
 *     "severity": "CRITICAL",
 *     "type": "PORT_SCAN",
 *     "message": "Abnormal port scanning detected",
 *     "resolved": false
 * }
 */


/* ========================================================= */
/* DATA                                                        */
/* ========================================================= */

let devices = [];

let logs = [];


/* ========================================================= */
/* SHIP MAP                                                    */
/* ========================================================= */

/*
 * TODO: real sensors are not wired in yet, and the shape of the
 * data they will send back is not decided. Until then, this is
 * a static placeholder so the map has something to show. Replace
 * SHIP_SENSORS with a real fetch() once the sensor payload format
 * is defined - the rendering code below does not need to change,
 * only where this object's values come from.
 *
 * Level values: 1 (green), 2 (orange), 3 (red) - see the map legend.
 */
const SHIP_SENSORS = {
    "pilot-door": 3,
    "reactor-door": 3,
    "armory-door": 3,
    "infirmary-door": 1,
    "server-door": 2,
    "elevator": 1,
    "quarters-a-door": 1,
    "quarters-b-door": 1,
    "quarters-c-door": 1,
    "quarters-d-door": 1,
    "hangar-door": 2,
    "entry-gate": 2,
    "exit-gate": 2
};

const SHIP_SENSOR_LABELS = {
    "pilot-door": "Poste de pilotage — Porte",
    "reactor-door": "Salle des réacteurs — Porte",
    "armory-door": "Armurerie — Porte",
    "infirmary-door": "Infirmerie — Porte",
    "server-door": "Salle des serveurs — Porte",
    "elevator": "Ascenseur",
    "quarters-a-door": "Quartiers A — Porte",
    "quarters-b-door": "Quartiers B — Porte",
    "quarters-c-door": "Quartiers C — Porte",
    "quarters-d-door": "Quartiers D — Porte",
    "hangar-door": "Hangar / garage — Porte",
    "entry-gate": "Entrée — Portail",
    "exit-gate": "Sortie — Portail"
};

// "plan" hides the sensor pills, "sensors" shows them
let currentMapMode = "sensors";

/*
 * Room details shown when clicking a room on the map. Staff names are
 * invented for the demo - replace with a real crew roster if one
 * becomes available.
 */
const SHIP_ROOMS = {
    "pilot": {
        label: "Poste de pilotage",
        purpose: "Commande et navigation du vaisseau. Accès restreint à l'équipe de pont.",
        staff: [
            { name: "Capitaine Elena Voss", role: "Commandant de bord" },
            { name: "Marcus Reyes", role: "Officier de navigation" }
        ],
        sensors: ["pilot-door"]
    },
    "reactor": {
        label: "Salle des réacteurs",
        purpose: "Production et régulation de l'énergie du vaisseau. Zone à haut risque, accès très limité.",
        staff: [
            { name: "Tomás Ferreira", role: "Chef mécanicien" }
        ],
        sensors: ["reactor-door"]
    },
    "armory": {
        label: "Armurerie",
        purpose: "Stockage et entretien de l'équipement de défense du vaisseau.",
        staff: [
            { name: "Sgt. Dana Kowalski", role: "Responsable armement" }
        ],
        sensors: ["armory-door"]
    },
    "infirmary": {
        label: "Infirmerie",
        purpose: "Soins médicaux de l'équipage et gestion des urgences sanitaires.",
        staff: [
            { name: "Dr. Amara N'Diaye", role: "Médecin de bord" }
        ],
        sensors: ["infirmary-door"]
    },
    "server-room": {
        label: "Salle des serveurs et communications",
        purpose: "Infrastructure réseau, communications inter-vaisseaux et stockage des données de bord.",
        staff: [
            { name: "Priya Anand", role: "Ingénieure réseau" }
        ],
        sensors: ["server-door"]
    },
    "quarters-a": {
        label: "Quartiers A",
        purpose: "Logement de l'équipe de pont.",
        staff: [
            { name: "Léa Bertrand", role: "Officier de quart" }
        ],
        sensors: ["quarters-a-door"]
    },
    "quarters-b": {
        label: "Quartiers B",
        purpose: "Logement de l'équipe d'ingénierie.",
        staff: [
            { name: "Omar Haddad", role: "Technicien systèmes" }
        ],
        sensors: ["quarters-b-door"]
    },
    "quarters-c": {
        label: "Quartiers C",
        purpose: "Logement de l'équipe médicale et sécurité.",
        staff: [
            { name: "Ingrid Solberg", role: "Infirmière de bord" }
        ],
        sensors: ["quarters-c-door"]
    },
    "quarters-d": {
        label: "Quartiers D",
        purpose: "Logement de l'équipe logistique.",
        staff: [
            { name: "Kenji Watanabe", role: "Responsable cargaison" }
        ],
        sensors: ["quarters-d-door"]
    },
    "hangar": {
        label: "Hangar / garage",
        purpose: "Stockage et maintenance des véhicules d'exploration. 7 places disponibles.",
        staff: [
            { name: "Jonas Lindqvist", role: "Responsable hangar et véhicules" }
        ],
        sensors: ["hangar-door", "entry-gate", "exit-gate"]
    }
};


/* ========================================================= */
/* CONFIGURATION                                               */
/* ========================================================= */

const REFRESH_INTERVAL = 2000;


/* ========================================================= */
/* INITIALIZATION                                              */
/* ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setupEventListeners();

        window.addEventListener("hashchange", applyRoute);

        loadDashboard();

        setInterval(
            loadDashboard,
            REFRESH_INTERVAL
        );

    }
);


/* ========================================================= */
/* EVENT LISTENERS                                             */
/* ========================================================= */

function setupEventListeners() {

    const refreshButton =
        document.getElementById(
            "refresh-button"
        );


    refreshButton.addEventListener(
        "click",
        loadDashboard
    );


    document
        .getElementById("severity-filter")
        .addEventListener(
            "change",
            renderLogs
        );


    document
        .getElementById("device-filter")
        .addEventListener(
            "change",
            renderLogs
        );


    document
        .getElementById("type-filter")
        .addEventListener(
            "change",
            renderLogs
        );

    document
        .getElementById("devices-container")
        .addEventListener("click", event => {
            const row = event.target.closest("tr[data-device-id]");
            if (row) {
                openDeviceDetails(row.dataset.deviceId);
            }
        });

    document
        .getElementById("devices-container")
        .addEventListener("keydown", event => {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            const row = event.target.closest("tr[data-device-id]");
            if (row) {
                event.preventDefault();
                openDeviceDetails(row.dataset.deviceId);
            }
        });

    document
        .getElementById("logs-container")
        .addEventListener("click", event => {
            const row = event.target.closest("tr[data-log-index]");
            if (row) {
                openLogDetails(logs[Number(row.dataset.logIndex)]);
            }
        });

    document
        .getElementById("logs-container")
        .addEventListener("keydown", event => {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            const row = event.target.closest("tr[data-log-index]");
            if (row) {
                event.preventDefault();
                openLogDetails(logs[Number(row.dataset.logIndex)]);
            }
        });

    document
        .getElementById("critical-container")
        .addEventListener("click", event => {
            const incident = event.target.closest("[data-log-index]");
            if (incident) {
                openLogDetails(logs[Number(incident.dataset.logIndex)]);
            }
        });

    document
        .getElementById("critical-container")
        .addEventListener("keydown", event => {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            const incident = event.target.closest("[data-log-index]");
            if (incident) {
                event.preventDefault();
                openLogDetails(logs[Number(incident.dataset.logIndex)]);
            }
        });

    document
        .getElementById("detail-content")
        .addEventListener("click", event => {
            const item = event.target.closest("button[data-log-index]");
            if (item) {
                openLogDetails(logs[Number(item.dataset.logIndex)]);
            }
        });

    document
        .getElementById("detail-close")
        .addEventListener("click", closeDetails);

    document
        .getElementById("detail-backdrop")
        .addEventListener("click", event => {
            if (event.target.id === "detail-backdrop") {
                closeDetails();
            }
        });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeDetails();
        }
    });

    document
        .querySelectorAll(".map-tab")
        .forEach(tab => {
            tab.addEventListener("click", () => {
                currentMapMode = tab.dataset.mode;
                renderMap();
            });
        });

    document
        .querySelectorAll(".map-pill")
        .forEach(pill => {

            pill.addEventListener(
                "click",
                event => {
                    event.stopPropagation();
                    openSensorDetails(pill.dataset.sensor);
                }
            );

            pill.addEventListener("keydown", event => {
                if (event.key !== "Enter" && event.key !== " ") {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                openSensorDetails(pill.dataset.sensor);
            });

        });

    document
        .querySelectorAll(".map-room")
        .forEach(room => {

            room.addEventListener(
                "click",
                () => openRoomDetails(room.dataset.room)
            );

            room.addEventListener("keydown", event => {
                if (event.key !== "Enter" && event.key !== " ") {
                    return;
                }
                event.preventDefault();
                openRoomDetails(room.dataset.room);
            });

        });

    renderMap();

}


/* ========================================================= */
/* LOAD DASHBOARD                                              */
/* ========================================================= */

async function loadDashboard() {

    setLoadingState(true);


    try {

        const [
            devicesResponse,
            logsResponse
        ] = await Promise.all([

            fetch("/api/devices?t=" + Date.now()),

            fetch("/api/logs?t=" + Date.now())

        ]);


        if (
            !devicesResponse.ok ||
            !logsResponse.ok
        ) {

            throw new Error(
                "Unable to retrieve data from Flask."
            );

        }


        devices =
            await devicesResponse.json();


        logs =
            await logsResponse.json();


        renderDashboard();

        setServerStatus(true);


    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );


        setServerStatus(false);

    } finally {

        setLoadingState(false);

    }

}


/* ========================================================= */
/* RENDER DASHBOARD                                            */
/* ========================================================= */

function renderDashboard() {

    renderStatistics();

    renderDevices();

    renderCriticalIncidents();

    updateFilters();

    renderLogs();

        applyRoute();

}


/* ========================================================= */
/* ROUTING                                                     */
/* ========================================================= */

const PAGE_CONFIG = {
    dashboard: {
        title: "Dashboard",
        subtitle: "Overview of the inter-vessel infrastructure."
    },
    devices: {
        title: "Devices",
        subtitle: "Inspect connected devices and their recent activity."
    },
    map: {
        title: "Ship map",
        subtitle: "Security level per sensor, by floor."
    },
    cameras: {
        title: "Cameras",
        subtitle: "Live security camera feed, vessel Aldebaran."
    },
    alerts: {
        title: "Alerts",
        subtitle: "Review unresolved incidents requiring attention."
    },
    logs: {
        title: "Logs",
        subtitle: "Search and inspect security and infrastructure events."
    },
    events: {
        title: "Events",
        subtitle: "Review the complete event stream received by the center."
    },
    status: {
        title: "System status",
        subtitle: "Monitor the center and connected vessel availability."
    },
    settings: {
        title: "Settings",
        subtitle: "Review the current dashboard and response configuration."
    }
};


function applyRoute() {

    const requestedPage = window.location.hash.slice(1).toLowerCase();
    const page = PAGE_CONFIG[requestedPage] ? requestedPage : "dashboard";
    const config = PAGE_CONFIG[page];

    document.getElementById("page-title").textContent = config.title;
    document.getElementById("page-subtitle").textContent = config.subtitle;

    document.querySelectorAll(".nav-item").forEach(item => {
        item.classList.toggle("active", item.getAttribute("href") === `#${page}`);
    });

    const visible = {
        stats: page === "dashboard" || page === "status",
        alerts: page === "dashboard" || page === "alerts",
        devices: page === "dashboard" || page === "devices" || page === "status",
        map: page === "map",
        cameras: page === "cameras",
        logs: page === "dashboard" || page === "logs" || page === "events",
        settings: page === "settings"
    };

    document.querySelector(".stats-grid").hidden = !visible.stats;
    document.getElementById("alerts").hidden = !visible.alerts;
    document.getElementById("devices").hidden = !visible.devices;
    document.getElementById("map-page").hidden = !visible.map;
    document.getElementById("cameras-page").hidden = !visible.cameras;
    document.getElementById("logs").hidden = !visible.logs;
    document.getElementById("settings-page").hidden = !visible.settings;

    if (visible.cameras) {
        loadCamerasFrame();
    }
}


/* ========================================================= */
/* CAMERAS                                                     */
/* ========================================================= */

function loadCamerasFrame() {

    const frame =
        document.getElementById("cameras-frame");

    if (!frame || frame.getAttribute("src")) {
        return;
    }

    frame.src = frame.dataset.src;

}


/* ========================================================= */
/* STATISTICS                                                  */
/* ========================================================= */

function renderStatistics() {

    const total =
        devices.length;


    const online =
        devices.filter(
            device =>
                device.status === "ONLINE"
        ).length;


    const warnings =
        devices.filter(
            device =>
                device.status === "WARNING"
        ).length;


    const critical =
        logs.filter(
            log =>
                log.severity === "CRITICAL" &&
                !log.resolved
        ).length;


    document.getElementById(
        "device-count"
    ).textContent = total;


    document.getElementById(
        "online-count"
    ).textContent = online;


    document.getElementById(
        "warning-count"
    ).textContent = warnings;


    document.getElementById(
        "critical-count"
    ).textContent = critical;


    document.getElementById(
        "sidebar-critical"
    ).textContent = critical;

}


/* ========================================================= */
/* DEVICES                                                     */
/* ========================================================= */

function renderDevices() {

    const container =
        document.getElementById(
            "devices-container"
        );


    container.innerHTML = "";


    if (devices.length === 0) {

        container.innerHTML = `

            <tr>

                <td
                    colspan="4"
                    class="empty-state"
                >

                    No devices registered.

                </td>

            </tr>

        `;

        return;

    }


    devices.forEach(
        device => {

            const row =
                document.createElement("tr");


            const statusClass =
                getStatusClass(
                    device.status
                );


            const lastSeen =
                device.last_seen
                    ? formatTimestamp(
                        device.last_seen
                    )
                    : "—";


            row.innerHTML = `

                <td>

                    <strong>
                        ${escapeHTML(device.id)}
                    </strong>

                </td>


                <td>

                    ${escapeHTML(
                        device.ip || "Unknown"
                    )}

                </td>


                <td>

                    <span class="status-cell">

                        <span
                            class="status-dot ${statusClass}"
                        ></span>

                        ${escapeHTML(
                            device.status || "UNKNOWN"
                        )}

                    </span>

                </td>


                <td>

                    ${escapeHTML(lastSeen)}

                </td>

            `;

            row.dataset.deviceId = device.id;
            row.tabIndex = 0;
            row.setAttribute("role", "button");
            row.setAttribute("aria-label", `View details for ${device.id}`);


            container.appendChild(row);

        }
    );

}


/* ========================================================= */
/* CRITICAL INCIDENTS                                          */
/* ========================================================= */

function renderCriticalIncidents() {

    const container =
        document.getElementById(
            "critical-container"
        );


    const criticalLogs =
        logs.filter(
            log =>
                log.severity === "CRITICAL" &&
                !log.resolved
        );


    container.innerHTML = "";


    document.getElementById(
        "critical-indicator"
    ).textContent =
        `${criticalLogs.length} unresolved`;


    if (
        criticalLogs.length === 0
    ) {

        container.innerHTML = `

            <div class="empty-state">

                ✓ No unresolved critical incidents.

            </div>

        `;

        return;

    }


    criticalLogs
        .sort(
            (a, b) =>
                new Date(b.timestamp) -
                new Date(a.timestamp)
        )
        .forEach(
            log => {

                const incident =
                    document.createElement("div");


                incident.className =
                    "incident interactive-row";
                incident.dataset.logIndex = logs.indexOf(log);
                incident.tabIndex = 0;
                incident.setAttribute("role", "button");
                incident.setAttribute("aria-label", `View incident ${log.type}`);


                incident.innerHTML = `

                    <div class="incident-header">

                        <span class="incident-title">

                            ${escapeHTML(
                                log.device
                            )}

                            —

                            ${escapeHTML(
                                log.type
                            )}

                        </span>


                        <span class="incident-time">

                            ${formatTimestamp(
                                log.timestamp
                            )}

                        </span>

                    </div>


                    <p>

                        ${escapeHTML(
                            log.message
                        )}

                    </p>

                `;


                container.appendChild(
                    incident
                );

            }
        );

}


/* ========================================================= */
/* FILTERS                                                     */
/* ========================================================= */

function updateFilters() {

    updateDeviceFilter();

    updateTypeFilter();

}


function updateDeviceFilter() {

    const select =
        document.getElementById(
            "device-filter"
        );


    const currentValue =
        select.value;


    const deviceNames =
        [
            ...new Set(
                logs
                    .map(log => log.device)
                    .filter(Boolean)
            )
        ].sort();


    select.innerHTML = `

        <option value="ALL">
            All devices
        </option>

    `;


    deviceNames.forEach(
        device => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                device;


            option.textContent =
                device;


            select.appendChild(
                option
            );

        }
    );


    if (
        deviceNames.includes(
            currentValue
        )
    ) {

        select.value =
            currentValue;

    } else {

        select.value =
            "ALL";

    }

}


function updateTypeFilter() {

    const select =
        document.getElementById(
            "type-filter"
        );


    const currentValue =
        select.value;


    const types =
        [
            ...new Set(
                logs
                    .map(log => log.type)
                    .filter(Boolean)
            )
        ].sort();


    select.innerHTML = `

        <option value="ALL">
            All types
        </option>

    `;


    types.forEach(
        type => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                type;


            option.textContent =
                type;


            select.appendChild(
                option
            );

        }
    );


    if (
        types.includes(
            currentValue
        )
    ) {

        select.value =
            currentValue;

    } else {

        select.value =
            "ALL";

    }

}


/* ========================================================= */
/* LOGS                                                        */
/* ========================================================= */

function renderLogs() {

    const container =
        document.getElementById(
            "logs-container"
        );


    const severity =
        document.getElementById(
            "severity-filter"
        ).value;


    const device =
        document.getElementById(
            "device-filter"
        ).value;


    const type =
        document.getElementById(
            "type-filter"
        ).value;


    let filteredLogs =
        [...logs];


    if (
        severity !== "ALL"
    ) {

        filteredLogs =
            filteredLogs.filter(
                log =>
                    log.severity ===
                    severity
            );

    }


    if (
        device !== "ALL"
    ) {

        filteredLogs =
            filteredLogs.filter(
                log =>
                    log.device ===
                    device
            );

    }


    if (
        type !== "ALL"
    ) {

        filteredLogs =
            filteredLogs.filter(
                log =>
                    log.type ===
                    type
            );

    }


    filteredLogs.sort(
        (a, b) =>
            new Date(b.timestamp) -
            new Date(a.timestamp)
    );


    container.innerHTML = "";


    if (
        filteredLogs.length === 0
    ) {

        container.innerHTML = `

            <tr>

                <td
                    colspan="6"
                    class="empty-state"
                >

                    No logs matching the selected filters.

                </td>

            </tr>

        `;

        return;

    }


    filteredLogs.forEach(
        log => {

            const row =
                document.createElement("tr");

            row.className = "interactive-row";
            row.dataset.logIndex = logs.indexOf(log);
            row.tabIndex = 0;
            row.setAttribute("role", "button");
            row.setAttribute("aria-label", `View log ${log.type}`);


            const severityClass =
                getSeverityClass(
                    log.severity
                );


            const status =
                log.resolved
                    ? "RESOLVED"
                    : "ACTIVE";


            row.innerHTML = `

                <td>

                    ${formatTimestamp(
                        log.timestamp
                    )}

                </td>


                <td>

                    <strong>
                        ${escapeHTML(
                            log.device
                        )}
                    </strong>

                </td>


                <td>

                    <span
                        class="badge ${severityClass}"
                    >

                        ${escapeHTML(
                            log.severity
                        )}

                    </span>

                </td>


                <td>

                    ${escapeHTML(
                        log.type
                    )}

                </td>


                <td>

                    ${escapeHTML(
                        log.message
                    )}

                </td>


                <td>

                    <span
                        class="badge ${
                            log.resolved
                                ? "badge-success"
                                : "badge-warning"
                        }"
                    >

                        ${status}

                    </span>

                </td>

            `;


            container.appendChild(
                row
            );

        }
    );

}


/* ========================================================= */
/* SHIP MAP RENDERING                                          */
/* ========================================================= */

function renderMap() {

    document
        .querySelectorAll(".map-tab")
        .forEach(tab => {
            tab.classList.toggle(
                "active",
                tab.dataset.mode === currentMapMode
            );
        });

    const canvas =
        document.querySelector(".map-canvas");

    if (canvas) {
        canvas.classList.toggle(
            "hide-sensors",
            currentMapMode === "plan"
        );
    }

    document
        .querySelectorAll(".map-pill")
        .forEach(pill => {

            const level =
                SHIP_SENSORS[pill.dataset.sensor] || 1;

            pill.classList.remove(
                "map-pill-ok",
                "map-pill-warn",
                "map-pill-critical"
            );

            pill.classList.add(
                getMapPillClass(level)
            );

        });

}


function getMapPillClass(level) {

    switch (Number(level)) {

        case 3:
            return "map-pill-critical";

        case 2:
            return "map-pill-warn";

        default:
            return "map-pill-ok";

    }

}


function getSensorBadgeClass(level) {

    switch (Number(level)) {

        case 3:
            return "badge-danger";

        case 2:
            return "badge-warning";

        default:
            return "badge-success";

    }

}


function getSensorSummaryClass(level) {

    switch (Number(level)) {

        case 3:
            return "critical";

        case 2:
            return "warning";

        default:
            return "online";

    }

}


function openSensorDetails(sensorId) {

    if (!sensorId) {
        return;
    }

    const level =
        SHIP_SENSORS[sensorId] || 1;

    const label =
        SHIP_SENSOR_LABELS[sensorId] || sensorId;

    openDetails(
        "Sensor",
        label,
        `
            <div class="detail-summary ${getSensorSummaryClass(level)}">
                <span class="badge ${getSensorBadgeClass(level)}">Niveau ${level}</span>
                <strong>Ship sensor</strong>
            </div>
            <p class="detail-message">
                Aucun capteur physique n'est encore branché sur ce point.
                Cette valeur est une donnée de démonstration, en attendant
                que le format des données envoyées par les vrais capteurs
                soit défini.
            </p>
        `
    );

}


function openRoomDetails(roomId) {

    const room =
        SHIP_ROOMS[roomId];

    if (!room) {
        return;
    }

    const staffList =
        room.staff.map(person => `
            <div>
                <dt>${escapeHTML(person.name)}</dt>
                <dd>${escapeHTML(person.role)}</dd>
            </div>
        `).join("");

    const sensorList =
        (room.sensors || []).map(sensorId => {

            const level =
                SHIP_SENSORS[sensorId] || 1;

            const label =
                SHIP_SENSOR_LABELS[sensorId] || sensorId;

            return `
                <div>
                    <dt>${escapeHTML(label)}</dt>
                    <dd><span class="badge ${getSensorBadgeClass(level)}">Niveau ${level}</span></dd>
                </div>
            `;

        }).join("");

    openDetails(
        "Room",
        room.label,
        `
            <p class="detail-message">${escapeHTML(room.purpose)}</p>

            <h3 class="detail-section-title">Personnel</h3>
            <dl class="detail-list">${staffList}</dl>

            ${sensorList ? `
                <h3 class="detail-section-title">Capteurs</h3>
                <dl class="detail-list">${sensorList}</dl>
            ` : ""}
        `
    );

}


/* ========================================================= */
/* DETAILS                                                     */
/* ========================================================= */


function openDeviceDetails(deviceId) {
    const device = devices.find(item => item.id === deviceId);
    if (!device) return;
    
    const deviceLogs = logs
        .filter(log => log.device === device.id)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
    let telHtml = `
        <div><dt>IP Address</dt><dd id="dd-ip">${escapeHTML(device.ip || "Unknown")}</dd></div>
        <div><dt>CPU Usage</dt><dd id="dd-cpu">--%</dd></div>
        <div><dt>Memory</dt><dd id="dd-ram">--%</dd></div>
        <div><dt>Temperature</dt><dd id="dd-temp">--°C</dd></div>
        <div><dt>Wi-Fi Signal</dt><dd id="dd-wifi">-- dBm</dd></div>
    `;

    openDetails(
        "Device",
        device.id,
        `
            <div class="detail-summary ${getStatusClass(device.status)}">
                <span class="status-dot ${getStatusClass(device.status)}"></span>
                <strong>${escapeHTML(device.status || "UNKNOWN")}</strong>
                <span>${deviceLogs.filter(log => !log.resolved).length} active event(s)</span>
            </div>
            
            <h3 class="detail-section-title">Telemetry</h3>
            <dl class="detail-list telemetry-list">
                ${telHtml}
            </dl>
            
            <h3 class="detail-section-title">Device Info</h3>
            <dl class="detail-list">
                <div><dt>Device ID</dt><dd>${escapeHTML(device.id)}</dd></div>
                <div><dt>IP address</dt><dd>${escapeHTML(device.ip || "Unknown")}</dd></div>
                <div><dt>Last seen</dt><dd>${escapeHTML(formatTimestamp(device.last_seen))}</dd></div>
                <div><dt>Recorded events</dt><dd>${deviceLogs.length}</dd></div>
            </dl>
            
            ${device.id === 'SERVER' ? '' : `
            <h3 class="detail-section-title">Remote Override</h3>
            <div style="display:flex; flex-direction:column; gap:10px; margin-bottom: 20px;">
                <button onclick="remoteAction('${device.id}', 'door')" class="modern-btn">Toggle Door Lock</button>
                <button onclick="remoteAction('${device.id}', 'unban')" class="modern-btn" style="background:#fff; color:#111; border:1px solid #ccc;">Unban IP / Restore Firewall</button>
            </div>
            `}
            
            <h3 class="detail-section-title">Recent activity</h3>
            ${renderDetailLogList(deviceLogs.slice(0, 5))}
        `
    );
    
    // Auto-update telemetry in drawer
    window.currentDrawerDevice = device.id;
}

window.remoteAction = function(deviceId, action) {
    if(action === 'door') {
        fetch('/api/command/door/' + deviceId, {
            method: 'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({action: 'TOGGLE'})
        });
        showToast('Commande de porte envoyée à ' + deviceId, 'success');
    } else if(action === 'unban') {
        fetch('/api/devices/' + deviceId + '/restore', {method: 'POST'});
        showToast('Tentative de restauration du pare-feu sur ' + deviceId, 'info');
    }
};



function openLogDetails(log) {

    if (!log) {
        return;
    }

    openDetails(
        "Security log",
        log.type || "Event",
        `
            <div class="detail-summary">
                <span class="badge ${getSeverityClass(log.severity)}">${escapeHTML(log.severity || "INFO")}</span>
                <strong>${escapeHTML(log.resolved ? "Resolved" : "Active")}</strong>
            </div>
            <dl class="detail-list">
                <div><dt>Device</dt><dd>${escapeHTML(log.device || "Unknown")}</dd></div>
                <div><dt>Timestamp</dt><dd>${escapeHTML(formatTimestamp(log.timestamp))}</dd></div>
                <div><dt>IP address</dt><dd>${escapeHTML(log.ip || "Unknown")}</dd></div>
                <div><dt>Event type</dt><dd>${escapeHTML(log.type || "Unknown")}</dd></div>
                <div><dt>Status</dt><dd>${escapeHTML(log.resolved ? "RESOLVED" : "ACTIVE")}</dd></div>
            </dl>
            <h3 class="detail-section-title">Message</h3>
            <p class="detail-message">${escapeHTML(log.message || "No message supplied.")}</p>
        `
    );
}


function renderDetailLogList(items) {

    if (!items.length) {
        return `<p class="detail-empty">No recorded activity.</p>`;
    }

    return `
        <div class="detail-log-list">
            ${items.map(log => `
                <button class="detail-log-item" type="button" data-log-index="${logs.indexOf(log)}">
                    <span>
                        <strong>${escapeHTML(log.type || "Event")}</strong>
                        <small>${escapeHTML(formatTimestamp(log.timestamp))}</small>
                    </span>
                    <span class="badge ${getSeverityClass(log.severity)}">${escapeHTML(log.severity || "INFO")}</span>
                </button>
            `).join("")}
        </div>
    `;
}


function openDetails(kicker, title, content) {

    document.getElementById("detail-kicker").textContent = kicker;
    document.getElementById("detail-title").textContent = title;
    document.getElementById("detail-content").innerHTML = content;

    const backdrop = document.getElementById("detail-backdrop");
    backdrop.hidden = false;
    document.body.classList.add("drawer-open");
    document.getElementById("detail-close").focus();
}


function closeDetails() {

    const backdrop = document.getElementById("detail-backdrop");

    if (backdrop.hidden) {
        return;
    }

    backdrop.hidden = true;
    document.body.classList.remove("drawer-open");
}


/* ========================================================= */
/* STATUS HELPERS                                              */
/* ========================================================= */

function getStatusClass(status) {

    switch (
        String(status).toUpperCase()
    ) {

        case "ONLINE":
            return "online";


        case "WARNING":
        case "WARN":
            return "warning";


        case "ISOLATED":
        case "CRITICAL":
            return "critical";


        default:
            return "offline";

    }

}


function getSeverityClass(severity) {

    switch (
        String(severity).toUpperCase()
    ) {

        case "CRITICAL":
            return "badge-danger";


        case "WARN":
        case "WARNING":
            return "badge-warning";


        case "INFO":
            return "badge-info";


        default:
            return "badge-info";

    }

}


/* ========================================================= */
/* DATE                                                        */
/* ========================================================= */

function formatTimestamp(timestamp) {

    if (!timestamp) {

        return "—";

    }


    const date =
        new Date(timestamp);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return timestamp;

    }


    return date.toLocaleString(
        undefined,
        {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        }
    );

}


/* ========================================================= */
/* SERVER CONNECTION STATUS                                    */
/* ========================================================= */

function setServerStatus(connected) {

    const dot =
        document.getElementById(
            "server-status-dot"
        );


    const text =
        document.getElementById(
            "server-status-text"
        );


    const connectionDot =
        document.getElementById(
            "connection-dot"
        );


    const connectionText =
        document.getElementById(
            "connection-text"
        );


    if (connected) {

        dot.className =
            "status-dot online";


        text.textContent =
            "System Online";


        connectionDot.className =
            "status-dot online";


        connectionText.textContent =
            "Connected";

    } else {

        dot.className =
            "status-dot critical";


        text.textContent =
            "Server Offline";


        connectionDot.className =
            "status-dot critical";


        connectionText.textContent =
            "Connection failed";

    }

}


/* ========================================================= */
/* LOADING STATE                                               */
/* ========================================================= */

function setLoadingState(loading) {

    const button =
        document.getElementById(
            "refresh-button"
        );


    if (loading) {

        button.classList.add(
            "loading"
        );


        button.disabled =
            true;


        button.innerHTML = `
            <span>↻</span>
            Refreshing...
        `;

    } else {

        button.classList.remove(
            "loading"
        );


        button.disabled =
            false;


        button.innerHTML = `
            <span>↻</span>
            Refresh
        `;

    }

}


/* ========================================================= */
/* SECURITY                                                     */
/* ========================================================= */

/*
 * Device and log data comes from the network.
 *
 * Never insert external values directly into innerHTML
 * without escaping them first.
 */

function escapeHTML(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        String(value);


    return div.innerHTML;

}

// ==========================================
// VERCEL/LINEAR MODERN UI INJECTION
// ==========================================


const showToast = (msg, type='info') => {
    const container = document.getElementById('toast-container');
    if(!container) return;
    const toast = document.createElement('div');
    toast.style.background = type === 'error' ? 'var(--danger-color)' : (type === 'success' ? '#10b981' : '#111827');
    toast.style.color = '#fff';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '8px';
    toast.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
    toast.style.fontFamily = 'var(--font-sans)';
    toast.style.fontSize = '14px';
    toast.style.fontWeight = '500';
    toast.style.transform = 'translateY(100%)';
    toast.style.opacity = '0';
    toast.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
    toast.innerText = msg;
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => { toast.style.transform = 'translateY(0)'; toast.style.opacity = '1'; }, 10);
    // Animate out
    setTimeout(() => {
        toast.style.transform = 'translateY(20px)'; toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
};

const initModernUI = () => {
    // 1. Inject Telemetry & Top Buttons into topbar
    const topbar = document.querySelector('.topbar');
    if(topbar && !document.getElementById('telemetry-container')) {
        const topHtml = `
            <div id="telemetry-container" class="telemetry-container" style="margin-left: auto;">
                <div class="tel-badge">
                    <span class="tel-label">CPU</span>
                    <span id="tel-cpu" class="tel-val">--%</span>
                </div>
                <div class="tel-badge">
                    <span class="tel-label">RAM</span>
                    <span id="tel-ram" class="tel-val">--%</span>
                </div>
                <div class="tel-badge">
                    <span class="tel-label">TEMP</span>
                    <span id="tel-temp" class="tel-val">--°C</span>
                </div>
                <div class="tel-badge">
                    <span class="tel-label">WIFI</span>
                    <span id="tel-wifi" class="tel-val">-- dBm</span>
                </div>
                <div style="width: 1px; height: 30px; background: var(--border-color); margin: 0 10px;"></div>
                <button id="btn-scan" class="modern-btn" style="margin-right: 10px;">Security Scan</button>
                <button id="btn-lockdown" class="modern-btn danger">Red Alert</button>
            </div>
        `;
        // Insert right after the brand
        const brand = topbar.querySelector('.brand');
        if(brand) brand.insertAdjacentHTML('afterend', topHtml);
        else topbar.insertAdjacentHTML('beforeend', topHtml);
        
        document.getElementById('btn-scan').addEventListener('click', () => {
            fetch('/api/command/scan', {method: 'POST'});
            showToast('Scan de sécurité en cours...', 'info');
        });
        document.getElementById('btn-lockdown').addEventListener('click', () => {
            fetch('/api/command/lockdown', {method: 'POST'});
            showToast('🚨 ALARME ROUGE DÉCLENCHÉE !', 'error');
        });
    }

    
    // 2. Telemetry Loop
    setInterval(async () => {
        try {
            const res = await fetch('/api/telemetry');
            const data = await res.json();
            const devices = Object.keys(data);
            if(devices.length > 0) {
                const tel = data[devices[0]];
                const cpu = document.getElementById('tel-cpu');
                if(cpu) {
                    cpu.innerText = tel.cpu_usage + '%';
                    document.getElementById('tel-ram').innerText = tel.ram_usage + '%';
                    document.getElementById('tel-temp').innerText = tel.temp.toFixed(1) + '°C';
                    document.getElementById('tel-wifi').innerText = tel.wifi_signal + ' dBm';
                }
            }
            
            // If drawer is open on a specific device
            if(window.currentDrawerDevice && data[window.currentDrawerDevice]) {
                const dTel = data[window.currentDrawerDevice];
                const dCpu = document.getElementById('dd-cpu');
                if(dCpu) {
                    dCpu.innerText = dTel.cpu_usage + '%';
                    document.getElementById('dd-ram').innerText = dTel.ram_usage + '%';
                    document.getElementById('dd-temp').innerText = dTel.temp.toFixed(1) + '°C';
                    document.getElementById('dd-wifi').innerText = dTel.wifi_signal + ' dBm';
                }
            }
        } catch (e) {}
    }, 2000);


    // 3. Inject buttons into detail drawer dynamically when opened
    document.addEventListener('click', (e) => {
        const room = e.target.closest('.map-room');
        if(room) {
            setTimeout(() => {
                const content = document.getElementById('detail-content');
                if(content && !document.getElementById('modern-action-drawer')) {
                    content.insertAdjacentHTML('beforeend', `
                        <div id="modern-action-drawer" class="action-drawer">
                            <div class="action-drawer-title">Remote Override</div>
                            <button id="btn-door" class="modern-btn" style="width: 100%; margin-bottom: 10px;">Toggle Door Lock</button>
                            <button id="btn-unban" class="modern-btn" style="width: 100%; background: #fff; color: #111; border: 1px solid #ccc;">Unban IP / Restore Firewall</button>
                        </div>
                    `);
                    document.getElementById('btn-door').addEventListener('click', () => {
                        fetch('/api/command/door/sas-reacteur-01', {
                            method: 'POST',
                            headers:{'Content-Type':'application/json'},
                            body: JSON.stringify({action: 'TOGGLE'})
                        });
                        showToast('Commande de porte envoyée.', 'success');
                    });
                    document.getElementById('btn-unban').addEventListener('click', () => {
                        fetch('/api/devices/sas-reacteur-01/restore', {method: 'POST'});
                        showToast('Tentative de restauration du firewall...', 'success');
                    });
                }
            }, 100); // Wait for original JS to populate drawer
        }
    });
};

setTimeout(initModernUI, 1000);


