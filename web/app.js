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

            fetch("/api/devices"),

            fetch("/api/logs")

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
    vessels: {
        title: "Vessels",
        subtitle: "Inspect connected devices and their recent activity."
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
        vessels: page === "dashboard" || page === "vessels" || page === "status",
        logs: page === "dashboard" || page === "logs" || page === "events",
        settings: page === "settings"
    };

    document.querySelector(".stats-grid").hidden = !visible.stats;
    document.getElementById("alerts").hidden = !visible.alerts;
    document.getElementById("vessels").hidden = !visible.vessels;
    document.getElementById("logs").hidden = !visible.logs;
    document.getElementById("settings-page").hidden = !visible.settings;
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

                    No vessels registered.

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
/* DETAILS                                                     */
/* ========================================================= */

function openDeviceDetails(deviceId) {

    const device = devices.find(item => item.id === deviceId);

    if (!device) {
        return;
    }

    const deviceLogs = logs
        .filter(log => log.device === device.id)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    openDetails(
        "Vessel",
        device.id,
        `
            <div class="detail-summary ${getStatusClass(device.status)}">
                <span class="status-dot ${getStatusClass(device.status)}"></span>
                <strong>${escapeHTML(device.status || "UNKNOWN")}</strong>
                <span>${deviceLogs.filter(log => !log.resolved).length} active event(s)</span>
            </div>
            <dl class="detail-list">
                <div><dt>Device ID</dt><dd>${escapeHTML(device.id)}</dd></div>
                <div><dt>IP address</dt><dd>${escapeHTML(device.ip || "Unknown")}</dd></div>
                <div><dt>Last seen</dt><dd>${escapeHTML(formatTimestamp(device.last_seen))}</dd></div>
                <div><dt>Recorded events</dt><dd>${deviceLogs.length}</dd></div>
            </dl>
            <h3 class="detail-section-title">Recent activity</h3>
            ${renderDetailLogList(deviceLogs.slice(0, 5))}
        `
    );
}


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