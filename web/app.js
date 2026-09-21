const mockData = {

    devices: [
        {
            id: "VESSEL-01",
            ip: "192.168.1.10",
            status: "ONLINE"
        },
        {
            id: "VESSEL-02",
            ip: "192.168.1.20",
            status: "ONLINE"
        },
        {
            id: "VESSEL-03",
            ip: "192.168.1.30",
            status: "ISOLATED"
        },
        {
            id: "VESSEL-04",
            ip: "192.168.1.40",
            status: "WARNING"
        }
    ],

    logs: [
        {
            timestamp: "2026-09-21T14:32:08",
            device: "VESSEL-03",
            ip: "192.168.1.30",
            severity: "CRITICAL",
            type: "PORT_SCAN",
            message: "Abnormal port scanning detected",
            resolved: false
        },

        {
            timestamp: "2026-09-21T14:31:51",
            device: "VESSEL-04",
            ip: "192.168.1.40",
            severity: "WARN",
            type: "HIGH_TRAFFIC",
            message: "Abnormally high network traffic",
            resolved: false
        },

        {
            timestamp: "2026-09-21T14:31:40",
            device: "VESSEL-01",
            ip: "192.168.1.10",
            severity: "INFO",
            type: "HEARTBEAT",
            message: "Heartbeat received",
            resolved: true
        },

        {
            timestamp: "2026-09-21T14:30:15",
            device: "VESSEL-02",
            ip: "192.168.1.20",
            severity: "INFO",
            type: "CONNECTION",
            message: "Connection established",
            resolved: true
        }
    ]
};

let devices = mockData.devices;
let logs = mockData.logs;

document.addEventListener("DOMContentLoaded", () => {

    initializeFilters();

    renderDashboard();

    setupFilterListeners();

});

function renderDashboard() {

    renderStatistics();

    renderDevices();

    renderCriticalIncidents();

    renderLogs();

}

function renderStatistics() {

    const total = devices.length;

    const online = devices.filter(
        device => device.status === "ONLINE"
    ).length;

    const warnings = devices.filter(
        device => device.status === "WARNING"
    ).length;

    const critical = logs.filter(
        log =>
            log.severity === "CRITICAL" &&
            !log.resolved
    ).length;


    document.getElementById("device-count").textContent = total;

    document.getElementById("online-count").textContent = online;

    document.getElementById("warning-count").textContent = warnings;

    document.getElementById("critical-count").textContent = critical;

}

function renderDevices() {

    const container =
        document.getElementById("devices-container");

    container.innerHTML = "";


    devices.forEach(device => {

        const card = document.createElement("div");

        card.className = "device-card";


        const statusClass =
            getStatusClass(device.status);


        card.innerHTML = `

            <div class="device-header">

                <span class="device-name">
                    ${escapeHTML(device.id)}
                </span>

                <span class="status-dot ${statusClass}">
                </span>

            </div>

            <div class="device-ip">
                ${escapeHTML(device.ip)}
            </div>

            <div class="device-status">
                ${escapeHTML(device.status)}
            </div>

        `;


        container.appendChild(card);

    });

}

function renderCriticalIncidents() {

    const container =
        document.getElementById("critical-container");

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


    if (criticalLogs.length === 0) {

        container.innerHTML = `
            <div class="incident">
                No unresolved critical incidents.
            </div>
        `;

        return;
    }


    criticalLogs.forEach(log => {

        const incident =
            document.createElement("div");

        incident.className = "incident";


        incident.innerHTML = `

            <div class="incident-header">

                <span class="incident-title">
                    ${escapeHTML(log.device)}
                    — ${escapeHTML(log.type)}
                </span>

                <span class="incident-time">
                    ${formatTimestamp(log.timestamp)}
                </span>

            </div>

            <p>
                ${escapeHTML(log.message)}
            </p>

        `;


        container.appendChild(incident);

    });

}


/* ========================================================= */
/* Logs                                                        */
/* ========================================================= */

function renderLogs() {

    const container =
        document.getElementById("logs-container");


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


    let filteredLogs = [...logs];


    if (severity !== "ALL") {

        filteredLogs =
            filteredLogs.filter(
                log =>
                    log.severity === severity
            );

    }


    if (device !== "ALL") {

        filteredLogs =
            filteredLogs.filter(
                log =>
                    log.device === device
            );

    }


    if (type !== "ALL") {

        filteredLogs =
            filteredLogs.filter(
                log =>
                    log.type === type
            );

    }


    container.innerHTML = "";


    filteredLogs.forEach(log => {

        const row =
            document.createElement("tr");


        row.innerHTML = `

            <td>
                ${formatTimestamp(log.timestamp)}
            </td>

            <td>
                ${escapeHTML(log.device)}
            </td>

            <td>
                <span class="badge ${getSeverityClass(log.severity)}">
                    ${escapeHTML(log.severity)}
                </span>
            </td>

            <td>
                ${escapeHTML(log.type)}
            </td>

            <td>
                ${escapeHTML(log.message)}
            </td>

            <td>
                ${log.resolved ? "RESOLVED" : "ACTIVE"}
            </td>

        `;


        container.appendChild(row);

    });

}


/* ========================================================= */
/* Filters                                                     */
/* ========================================================= */

function initializeFilters() {

    const deviceFilter =
        document.getElementById(
            "device-filter"
        );

    const typeFilter =
        document.getElementById(
            "type-filter"
        );


    const deviceNames =
        [...new Set(
            logs.map(log => log.device)
        )];


    const types =
        [...new Set(
            logs.map(log => log.type)
        )];


    deviceNames.forEach(device => {

        const option =
            document.createElement("option");

        option.value = device;

        option.textContent = device;

        deviceFilter.appendChild(option);

    });


    types.forEach(type => {

        const option =
            document.createElement("option");

        option.value = type;

        option.textContent = type;

        typeFilter.appendChild(option);

    });

}


function setupFilterListeners() {

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

}


/* ========================================================= */
/* Helpers                                                     */
/* ========================================================= */

function getStatusClass(status) {

    switch (status) {

        case "ONLINE":
            return "online";

        case "WARNING":
            return "warning";

        case "ISOLATED":
            return "critical";

        default:
            return "offline";

    }

}


function getSeverityClass(severity) {

    switch (severity) {

        case "CRITICAL":
            return "critical-badge";

        case "WARN":
            return "warn-badge";

        default:
            return "info-badge";

    }

}


function formatTimestamp(timestamp) {

    const date =
        new Date(timestamp);

    return date.toLocaleString();

}


/*
 * Prevent HTML injection when displaying
 * external device/log data.
 */

function escapeHTML(value) {

    const div =
        document.createElement("div");

    div.textContent = value;

    return div.innerHTML;

}