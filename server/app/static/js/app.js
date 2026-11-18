// === MO TA FILE ===
// server/app/static/js/app.js
// CHUC NANG: AJAX /api/web/summary 5 giay, thanh SOS + am bao
(function () {
  "use strict";

  var settings = window.BLINDASSIST || {};
  var storageKey = "blindassist.beepedSos";
  var muteKey = "blindassist.sosMuted";
  var audioContext = null;

  function readStorage(key, fallback) {
    try {
      var raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (error) {
      return fallback;
    }
  }

  function writeStorage(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      return;
    }
  }

  function ensureAudioContext() {
    var AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      return null;
    }
    if (!audioContext) {
      audioContext = new AudioContextClass();
    }
    if (audioContext.state === "suspended") {
      audioContext.resume();
    }
    return audioContext;
  }

  function playSosBeep() {
    if (readStorage(muteKey, false)) {
      return;
    }
    var context = ensureAudioContext();
    if (!context) {
      return;
    }
    var startTime = context.currentTime + 0.05;
    for (var index = 0; index < 3; index += 1) {
      var oscillator = context.createOscillator();
      var gain = context.createGain();
      var toneStart = startTime + index * 0.45;
      oscillator.type = "square";
      oscillator.frequency.setValueAtTime(index % 2 === 0 ? 880 : 660, toneStart);
      gain.gain.setValueAtTime(0.0001, toneStart);
      gain.gain.exponentialRampToValueAtTime(0.25, toneStart + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, toneStart + 0.35);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start(toneStart);
      oscillator.stop(toneStart + 0.38);
    }
  }

  function updateText(elementId, value) {
    var element = document.getElementById(elementId);
    if (element) {
      element.textContent = value;
    }
  }

  function renderSosBanner(newSos) {
    var banner = document.getElementById("sos-banner");
    var navBadge = document.getElementById("nav-sos-badge");
    if (navBadge) {
      navBadge.textContent = newSos.length;
      navBadge.classList.toggle("d-none", newSos.length === 0);
    }
    if (!banner) {
      return;
    }
    if (newSos.length === 0) {
      banner.classList.add("d-none");
      return;
    }
    var latest = newSos[0];
    var who = latest.blind_person ? latest.blind_person : latest.device_name;
    updateText("sos-banner-title", newSos.length === 1
      ? "Có 1 tín hiệu SOS chưa xử lý"
      : "Có " + newSos.length + " tín hiệu SOS chưa xử lý");
    updateText("sos-banner-detail", "Mới nhất: " + who + " (" + latest.device_code + ") lúc " + latest.created_at_text);
    banner.classList.remove("d-none");
  }

  function renderDeviceStatuses(devices) {
    (devices || []).forEach(function (device) {
      document.querySelectorAll('[data-device-status="' + device.id + '"]').forEach(function (element) {
        element.classList.remove("status-online", "status-offline");
        element.classList.add("status-" + device.status);
        element.textContent = device.status_label;
      });
      document.querySelectorAll('[data-device-last-seen="' + device.id + '"]').forEach(function (element) {
        element.textContent = device.last_seen_text;
      });
    });
  }

  var sosPanelRefreshing = false;

  function refreshSosPanel(newSos) {
    var panel = document.getElementById("dashboard-sos-panel");
    if (!panel || sosPanelRefreshing || panel.contains(document.activeElement)) {
      return;
    }
    var latestIds = newSos.slice(0, 10).map(function (item) { return String(item.id); }).join(",");
    if (latestIds === panel.getAttribute("data-sos-ids")) {
      return;
    }
    sosPanelRefreshing = true;
    fetch(window.location.href, { credentials: "same-origin", headers: { "Accept": "text/html" } })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.text();
      })
      .then(function (html) {
        var fresh = new DOMParser().parseFromString(html, "text/html").getElementById("dashboard-sos-panel");
        var current = document.getElementById("dashboard-sos-panel");
        if (fresh && current && !current.contains(document.activeElement)) {
          current.replaceWith(fresh);
        }
      })
      .catch(function () { return null; })
      .then(function () { sosPanelRefreshing = false; });
  }

  function handleSummary(summary) {
    renderDeviceStatuses(summary.devices);
    refreshSosPanel(summary.new_sos);
    updateText("live-online", summary.online_devices);
    updateText("stat-alerts-today", summary.alerts_today);
    updateText("stat-devices-online", summary.online_devices);
    updateText("stat-sos-new", summary.new_sos.length);
    renderSosBanner(summary.new_sos);

    var beeped = readStorage(storageKey, []);
    var currentIds = summary.new_sos.map(function (item) { return item.id; });
    var unseen = currentIds.filter(function (id) { return beeped.indexOf(id) === -1; });
    if (unseen.length > 0) {
      playSosBeep();
      document.title = "(SOS) " + document.title.replace(/^\(SOS\) /, "");
    } else if (currentIds.length === 0) {
      document.title = document.title.replace(/^\(SOS\) /, "");
    }
    writeStorage(storageKey, currentIds.concat(beeped.filter(function (id) {
      return currentIds.indexOf(id) === -1;
    })).slice(0, 200));
  }

  function pollSummary() {
    if (!settings.summaryUrl) {
      return;
    }
    fetch(settings.summaryUrl, { credentials: "same-origin", headers: { "Accept": "application/json" } })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(handleSummary)
      .catch(function () { return null; });
  }

  document.addEventListener("click", function () {
    ensureAudioContext();
  }, { once: true });

  document.addEventListener("DOMContentLoaded", function () {
    var muteButton = document.getElementById("sos-mute-button");
    if (muteButton) {
      var refreshMuteLabel = function () {
        var muted = readStorage(muteKey, false);
        muteButton.innerHTML = muted
          ? '<i class="bi bi-volume-up"></i> Bật âm báo'
          : '<i class="bi bi-volume-mute"></i> Tắt âm báo';
      };
      refreshMuteLabel();
      muteButton.addEventListener("click", function () {
        writeStorage(muteKey, !readStorage(muteKey, false));
        refreshMuteLabel();
      });
    }

    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.getAttribute("data-confirm"))) {
          event.preventDefault();
        }
      });
    });

    pollSummary();
    window.setInterval(pollSummary, (settings.pollSeconds || 5) * 1000);
  });
})();
