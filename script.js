let isMuted = false;
let maps = {};
let markers = {};
let countdowns = {};

// 🔴 NEW: Tracks our looping audio alarms so we can stop them later
let activeAlarms = {};

const colors = { police: "#ef4444", medical: "#3b82f6", fire: "#ea580c" };
let logs = JSON.parse(localStorage.getItem('pandoraLogs')) || [];
const sessionImages = {};

setInterval(() => {
    document.getElementById("diag-cpu").innerText = Math.floor(Math.random() * 15 + 30) + "%";
    document.getElementById("diag-net").innerText = Math.floor(Math.random() * 10 + 10) + " ms";
}, 2000);

// --- AUDIO ENGINE ---
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function checkLogin(e) {
    if (e.key === 'Enter') {
        if (e.target.value === 'admin') {

            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            // Silent ping to confirm unlock
            const osc = audioCtx.createOscillator();
            osc.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.01);

            document.getElementById('login-overlay').style.display = 'none';
            initMaps();
            renderLogs();
        } else {
            e.target.value = '';
            e.target.placeholder = 'ACCESS DENIED';
        }
    }
}

function initMaps() {
    ['police', 'medical', 'fire'].forEach(dept => {
        maps[dept] = L.map(`${dept}-map`, { zoomControl: false }).setView([16.4961, 80.4994], 18);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(maps[dept]);
        markers[dept] = L.marker([16.4961, 80.4994]).addTo(maps[dept]);
    });
}

function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(t => {
        t.style.display = 'none';
        t.classList.remove('active');
    });

    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.style.display = 'block';
        targetTab.classList.add('active');
    }

    const activeBtn = document.querySelector(`.nav-btn[onclick*="${tabId}"]`);
    if (activeBtn) activeBtn.classList.add('active');

    if (maps[tabId]) setTimeout(() => maps[tabId].invalidateSize(), 100);
}

function toggleTheme() { document.body.classList.toggle('light-mode'); }
function toggleMute() {
    isMuted = !isMuted;
    document.getElementById('mute-btn').innerText = isMuted ? '🔇 Audio Off' : '🔊 Audio On';
    // If muted, instantly silence all currently ringing alarms
    if (isMuted) {
        Object.keys(activeAlarms).forEach(dept => {
            clearInterval(activeAlarms[dept]);
            delete activeAlarms[dept];
        });
    }
}

// 🔴 THE NEW CONTINUOUS ALARM LOGIC
function playContinuousAlarm(dept) {
    if (isMuted) return;

    // If this department is already ringing, don't start a second overlapping alarm
    if (activeAlarms[dept]) return;

    let type = 'square';
    let freq = 800;

    if (dept === 'medical') { type = 'sine'; freq = 400; }
    if (dept === 'fire') { type = 'sawtooth'; freq = 250; }

    // Function that triggers a single beep
    const soundPulse = () => {
        if (isMuted) return;
        const osc = audioCtx.createOscillator();
        osc.type = type;
        osc.frequency.value = freq;
        osc.connect(audioCtx.destination);
        osc.start();
        setTimeout(() => {
            try { osc.stop(); } catch (e) { }
        }, 600); // Pulse lasts 600ms
    };

    // Play the first pulse immediately
    soundPulse();

    // Loop the pulse every 1 second (1000ms) until acknowledged
    activeAlarms[dept] = setInterval(soundPulse, 1000);
}

// Helper function to stop the alarm
function stopAlarm(dept) {
    if (activeAlarms[dept]) {
        clearInterval(activeAlarms[dept]);
        delete activeAlarms[dept];
    }
}

function startTimer(dept) {
    clearInterval(countdowns[dept]);
    let time = 180;
    countdowns[dept] = setInterval(() => {
        if (time <= 0) { clearInterval(countdowns[dept]); return; }
        time--;
        let m = Math.floor(time / 60).toString().padStart(2, '0');
        let s = (time % 60).toString().padStart(2, '0');
        document.getElementById(`${dept}-timer`).innerText = `${m}:${s}`;
    }, 1000);
}

function triggerLockdown() {
    document.body.style.border = "5px solid red";
    if (!isMuted) playContinuousAlarm('police');
}

// --- WEBSOCKET CONNECTION ---
const ws = new WebSocket("ws://localhost:8765");

ws.onopen = () => {
    const status = document.getElementById("conn-status");
    status.innerHTML = "🟢 SERVER UPLINK ESTABLISHED"; status.style.color = "#0f0";
};
ws.onclose = () => {
    const status = document.getElementById("conn-status");
    status.innerHTML = "🔴 CONNECTION LOST"; status.style.color = "red";
};

ws.onmessage = e => {
    const data = JSON.parse(e.data);

    const tabMap = {
        active_threat: "police",
        deliberate_sos: "police",
        medical_collapse: "medical",
        hazard_fire: "fire"
    };
    const target = tabMap[data.alert_type];
    if (!target) return;

    const logId = Date.now().toString();

    switchTab(target);

    let alertPrefix = "";
    if (data.alert_type === "deliberate_sos") alertPrefix = "X-BLOCK SOS // ";
    document.getElementById(`${target}-bldg`).innerText = alertPrefix + `${data.building} - ${data.room}`;
    document.getElementById(`${target}-conf`).innerText = data.confidence;

    document.getElementById(`${target}-img`).src = "data:image/jpeg;base64," + data.image;

    const latlng = new L.LatLng(data.lat, data.lng);
    markers[target].setLatLng(latlng);
    maps[target].flyTo(latlng, 18);

    const alertBox = document.getElementById(`${target}-alert`);
    alertBox.style.display = "block";
    alertBox.style.opacity = "1";

    // 🔴 Trigger the new continuous looping alarm
    playContinuousAlarm(target);
    startTimer(target);

    const timeStr = new Date().toLocaleTimeString();
    sessionImages[logId] = data.image;
    logs.unshift({ id: logId, time: timeStr, type: data.alert_type.toUpperCase(), loc: data.room, dept: target });

    if (logs.length > 50) logs.pop();
    localStorage.setItem('pandoraLogs', JSON.stringify(logs));
    renderLogs();
};

function renderLogs() {
    const container = document.getElementById("log-container");
    container.innerHTML = '<div style="margin-bottom:15px; font-weight:800; font-family:\'Inter\',sans-serif; color: #fff; padding-left:5px;">INCIDENT HISTORY</div>';

    logs.forEach(log => {
        const div = document.createElement("div");
        div.style.padding = "10px";
        div.style.marginBottom = "8px";
        div.style.background = "#111";
        div.style.borderLeft = `4px solid ${colors[log.dept]}`;
        div.style.cursor = "pointer";
        div.style.fontSize = "13px";
        div.onclick = () => viewLog(log.id);
        div.innerHTML = `<b style="color:#aaa;">${log.time}</b><br><span style="color:${colors[log.dept]}; font-weight:bold;">${log.type}</span><br><span style="font-family:'Fira Code'; color:#777;">${log.loc}</span>`;
        container.appendChild(div);
    });
}

function viewLog(id) {
    const log = logs.find(l => l.id === id);
    if (!log) return;

    document.getElementById('modal-title').innerText = log.type.replace('_', ' ');
    document.getElementById('modal-title').style.color = colors[log.dept];
    document.getElementById('modal-info').innerHTML = `<b>TIMESTAMP:</b> ${log.time} &nbsp;&nbsp;|&nbsp;&nbsp; <b>LOCATION:</b> ${log.loc}`;

    const imgElem = document.getElementById('modal-img');
    const noImgElem = document.getElementById('modal-no-img');

    if (sessionImages[id]) {
        imgElem.src = "data:image/jpeg;base64," + sessionImages[id];
        imgElem.style.display = "block";
        noImgElem.style.display = "none";
    } else {
        imgElem.style.display = "none";
        noImgElem.style.display = "block";
    }

    document.getElementById('log-modal').style.display = 'flex';
}

function acknowledge(dept) {
    clearInterval(countdowns[dept]);

    // 🔴 KILL THE SIREN ON ACKNOWLEDGE
    stopAlarm(dept);

    document.getElementById(`${dept}-timer`).innerText = "ACK'D";
    document.getElementById(`${dept}-alert`).style.opacity = "0.5";
}

function resolve(dept) {
    clearInterval(countdowns[dept]);

    // 🔴 KILL THE SIREN ON RESOLVE
    stopAlarm(dept);

    document.getElementById(`${dept}-alert`).style.display = "none";
    document.getElementById(`${dept}-img`).src = "";
}

function exportCSV() {
    let csv = "data:text/csv;charset=utf-8,Time,Threat_Type,Location\n";
    logs.forEach(e => csv += `${e.time},${e.type},${e.loc}\n`);
    const link = document.createElement("a");
    link.setAttribute("href", encodeURI(csv));
    link.setAttribute("download", "Pandora_1_Shift_Report.csv");
    document.body.appendChild(link); link.click();
}

// --- CAMERA HOT-SWAP COMMANDS ---
function toggleCamInput() {
    const isIP = document.querySelector('input[name="camType"]:checked').value === 'ip';
    document.getElementById('ip-cam-url').style.display = isIP ? 'block' : 'none';
}

function sendCameraCommand() {
    if (ws.readyState !== WebSocket.OPEN) {
        return alert("Cannot send command: Server Offline.");
    }

    const camType = document.querySelector('input[name="camType"]:checked').value;
    let payload = { command: "CHANGE_CAMERA", type: camType };

    if (camType === 'ip') {
        const url = document.getElementById('ip-cam-url').value;
        if (!url) return alert("Please enter a valid IP Camera URL.");
        payload.url = url;
    }

    // Send the command to the Python Node
    ws.send(JSON.stringify(payload));

    // UI Feedback
    document.getElementById("conn-status").innerHTML = "⏳ RE-ROUTING SENSOR...";
    document.getElementById("conn-status").style.color = "yellow";

    // Reset back to normal after 2 seconds
    setTimeout(() => {
        document.getElementById("conn-status").innerHTML = "🟢 SERVER UPLINK ESTABLISHED";
        document.getElementById("conn-status").style.color = "#0f0";
    }, 2000);
}