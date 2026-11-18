// === MO TA FILE ===
// server/app/static/js/blind_mode.js
// CHUC NANG: Camera trinh duyet, gui khung JPEG, ve box, Web Speech tieng Viet
(function () {
  "use strict";

  var options = JSON.parse(document.getElementById("bm-options").textContent);
  var policy = options.policy || {};
  var STORAGE_KEY = "blindassist.thiet-bi";
  var MUTE_KEY = "blindassist.thiet-bi.tat-tieng";
  var CAMERA_KEY = "blindassist.thiet-bi.camera";
  var MIN_FRAME_INTERVAL_MS = 100;
  var CAPTURE_LONG_SIDE = 640;
  var JPEG_QUALITY = 0.7;
  var REQUEST_TIMEOUT_MS = 8000;
  var DETECT_TIMEOUT_MS = 20000;
  var ALERT_FADE_MS = 4000;
  var RECONNECT_MS = 5000;
  var LEVEL_COLORS = { DANGER: "#ff3b30", WARNING: "#ffd60a", SAFE: "#3ddc84" };
  var POSITION_TEXT = { LEFT: "bên trái", CENTER: "phía trước", RIGHT: "bên phải" };

  var elements = {
    connection: document.getElementById("bm-connection"),
    secureWarning: document.getElementById("bm-secure-warning"),
    setup: document.getElementById("bm-setup"),
    setupForm: document.getElementById("bm-setup-form"),
    setupCode: document.getElementById("bm-device-code"),
    setupKey: document.getElementById("bm-device-key"),
    setupError: document.getElementById("bm-setup-error"),
    setupSubmit: document.getElementById("bm-setup-submit"),
    app: document.getElementById("bm-app"),
    alert: document.getElementById("bm-alert"),
    stage: document.getElementById("bm-stage"),
    video: document.getElementById("bm-video"),
    overlay: document.getElementById("bm-overlay"),
    stageEmpty: document.getElementById("bm-stage-empty"),
    nearest: document.getElementById("bm-nearest"),
    toggle: document.getElementById("bm-toggle"),
    toggleText: document.getElementById("bm-toggle-text"),
    sos: document.getElementById("bm-sos"),
    mute: document.getElementById("bm-mute"),
    muteText: document.getElementById("bm-mute-text"),
    logout: document.getElementById("bm-logout"),
    camera: document.getElementById("bm-camera"),
    deviceName: document.getElementById("bm-device-name"),
    person: document.getElementById("bm-person"),
    fps: document.getElementById("bm-fps"),
    latency: document.getElementById("bm-latency"),
    engine: document.getElementById("bm-engine"),
    alertCount: document.getElementById("bm-alert-count"),
    voiceNote: document.getElementById("bm-voice-note")
  };

  var state = {
    credentials: null,
    device: null,
    config: null,
    connected: false,
    heartbeatTimer: null,
    reconnectTimer: null,
    sessionId: null,
    running: false,
    starting: false,
    stopping: false,
    loopBusy: false,
    stream: null,
    captureCanvas: document.createElement("canvas"),
    lastDetection: null,
    alertFadeTimer: null,
    sosLastPress: -Infinity,
    sosRetryTimer: null,
    sosSending: false,
    metrics: null
  };

  function newMetrics() {
    return {
      startedAt: performance.now(),
      frames: 0,
      alerts: 0,
      alertsSaved: 0,
      roundTrips: [],
      serverProcess: [],
      inference: [],
      recentFrameTimes: [],
      errors: 0,
      messages: []
    };
  }

  state.metrics = newMetrics();

  function readStorage(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function writeStorage(key, value) {
    try {
      if (value === null) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, value);
      }
    } catch (error) {
      return;
    }
  }

  function loadCredentials() {
    var raw = readStorage(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    try {
      var parsed = JSON.parse(raw);
      if (parsed && parsed.device_code && parsed.api_key) {
        return parsed;
      }
    } catch (error) {
      return null;
    }
    return null;
  }

  function sleep(ms) {
    return new Promise(function (resolve) {
      window.setTimeout(resolve, ms);
    });
  }

  function formatNumber(value, digits) {
    return Number(value).toFixed(digits).replace(".", ",");
  }

  function average(values) {
    if (!values.length) {
      return 0;
    }
    var total = 0;
    for (var index = 0; index < values.length; index += 1) {
      total += values[index];
    }
    return total / values.length;
  }

  function percentile(values, ratio) {
    if (!values.length) {
      return 0;
    }
    var sorted = values.slice().sort(function (a, b) { return a - b; });
    var index = Math.min(sorted.length - 1, Math.floor(ratio * (sorted.length - 1) + 0.5));
    return sorted[index];
  }

  function Speaker() {
    this.supported = "speechSynthesis" in window && typeof window.SpeechSynthesisUtterance === "function";
    this.voice = null;
    this.voicesKnown = false;
    this.muted = false;
    this.speaking = null;
    this.pending = null;
    this.rateWpm = 165;
    this.rateDangerWpm = 200;
    this.volume = 1;
    this.baseRateWpm = policy.base_rate_wpm || 165;
    this.onVoiceStatus = null;
    var speaker = this;
    if (this.supported) {
      this.pickVoice();
      if (typeof window.speechSynthesis.addEventListener === "function") {
        window.speechSynthesis.addEventListener("voiceschanged", function () { speaker.pickVoice(); });
      }
      window.setTimeout(function () { speaker.reportVoice(true); }, 1500);
    }
  }

  Speaker.prototype.pickVoice = function () {
    var voices = window.speechSynthesis.getVoices() || [];
    if (!voices.length) {
      return;
    }
    var vietnamese = voices.filter(function (voice) { return /^vi([-_]|$)/i.test(voice.lang || ""); });
    var preferred = vietnamese.filter(function (voice) { return voice.localService; });
    this.voice = preferred[0] || vietnamese[0] || null;
    this.voicesKnown = true;
    this.reportVoice(false);
  };

  Speaker.prototype.reportVoice = function (final) {
    if (typeof this.onVoiceStatus !== "function") {
      return;
    }
    if (!this.supported) {
      this.onVoiceStatus("unsupported");
    } else if (this.voice) {
      this.onVoiceStatus("vietnamese", this.voice);
    } else if (this.voicesKnown || final) {
      this.onVoiceStatus("default");
    }
  };

  Speaker.prototype.configure = function (config) {
    if (!config) {
      return;
    }
    if (config.tts_rate) {
      this.rateWpm = Number(config.tts_rate);
    }
    if (config.tts_rate_danger) {
      this.rateDangerWpm = Number(config.tts_rate_danger);
    }
    if (typeof config.tts_volume === "number") {
      this.volume = Math.max(0, Math.min(1, config.tts_volume));
    }
  };

  Speaker.prototype.webRate = function (wpm) {
    return Math.max(0.5, Math.min(2.0, wpm / this.baseRateWpm));
  };

  Speaker.prototype.say = function (text, settings) {
    settings = settings || {};
    var item = {
      text: text,
      priority: settings.priority === undefined ? 1 : settings.priority,
      distance: settings.distance === undefined ? null : settings.distance,
      interrupt: Boolean(settings.interrupt),
      rateWpm: settings.rateWpm || (settings.priority >= 2 ? this.rateDangerWpm : this.rateWpm),
      volume: settings.volume === undefined ? this.volume : settings.volume,
      createdAt: performance.now(),
      startedAt: null,
      timer: null
    };
    if (!this.supported || this.muted || !text) {
      return false;
    }
    if (this.pending && this.pending.priority > item.priority) {
      return false;
    }
    this.pending = item;
    var speaking = this.speaking;
    if (!speaking) {
      this.next();
      return true;
    }
    var spokeLongEnough = speaking.startedAt === null ||
      (performance.now() - speaking.startedAt) / 1000 >= (policy.interrupt_min_speak_s || 1.2);
    var closer = item.distance !== null && speaking.distance !== null &&
      item.distance <= speaking.distance - (policy.interrupt_closer_step_m || 0.5);
    var shouldInterrupt = item.priority > speaking.priority ||
      (spokeLongEnough && (closer || (item.interrupt && item.priority >= speaking.priority)));
    if (shouldInterrupt) {
      this.cancelCurrent();
    }
    return true;
  };

  Speaker.prototype.next = function () {
    if (this.speaking || !this.pending) {
      return;
    }
    var item = this.pending;
    this.pending = null;
    var maxAge = (policy.max_message_age_s || 1.5) * 1000;
    if (item.priority < 3 && performance.now() - item.createdAt > maxAge + 1000) {
      this.next();
      return;
    }
    var speaker = this;
    var utterance = new window.SpeechSynthesisUtterance(item.text);
    utterance.lang = this.voice ? this.voice.lang : "vi-VN";
    if (this.voice) {
      utterance.voice = this.voice;
    }
    utterance.rate = this.webRate(item.rateWpm);
    utterance.volume = item.volume;
    var finish = function () {
      if (speaker.speaking !== item) {
        return;
      }
      window.clearTimeout(item.timer);
      speaker.speaking = null;
      speaker.next();
    };
    utterance.onend = finish;
    utterance.onerror = finish;
    item.startedAt = performance.now();
    item.timer = window.setTimeout(finish, 2500 + item.text.length * 110 / utterance.rate);
    this.speaking = item;
    try {
      window.speechSynthesis.resume();
      window.speechSynthesis.speak(utterance);
    } catch (error) {
      finish();
    }
  };

  Speaker.prototype.cancelCurrent = function () {
    var item = this.speaking;
    this.speaking = null;
    if (item) {
      window.clearTimeout(item.timer);
    }
    try {
      window.speechSynthesis.cancel();
    } catch (error) {
      return;
    }
    var speaker = this;
    window.setTimeout(function () { speaker.next(); }, 60);
  };

  Speaker.prototype.stopAll = function () {
    this.pending = null;
    if (this.speaking) {
      this.cancelCurrent();
    }
  };

  Speaker.prototype.setMuted = function (muted) {
    this.muted = muted;
    if (muted) {
      this.stopAll();
    }
  };

  var speaker = new Speaker();

  speaker.onVoiceStatus = function (status, voice) {
    if (status === "unsupported") {
      showVoiceNote("Trình duyệt này không hỗ trợ đọc giọng nói. Cảnh báo chỉ hiển thị bằng chữ.");
    } else if (status === "default") {
      showVoiceNote("Máy chưa có giọng đọc tiếng Việt. Hệ thống vẫn đọc bằng giọng mặc định; nên cài thêm giọng tiếng Việt trong phần cài đặt ngôn ngữ của máy.");
    } else if (status === "vietnamese") {
      elements.voiceNote.hidden = true;
      elements.voiceNote.dataset.voice = voice.name;
    }
  };

  function showVoiceNote(text) {
    elements.voiceNote.textContent = text;
    elements.voiceNote.hidden = false;
  }

  function setConnection(kind, text) {
    elements.connection.className = "bm-pill bm-pill-" + kind;
    elements.connection.textContent = text;
  }

  function showAlert(text, kind) {
    window.clearTimeout(state.alertFadeTimer);
    elements.alert.className = "bm-alert bm-alert-" + kind;
    elements.alert.textContent = text;
    if (kind === "warning" || kind === "danger") {
      state.alertFadeTimer = window.setTimeout(function () {
        elements.alert.classList.add("bm-alert-faded");
      }, ALERT_FADE_MS);
    }
  }

  function apiError(message, status) {
    var error = new Error(message);
    error.status = status;
    return error;
  }

  function api(path, settings) {
    settings = settings || {};
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timeout = settings.timeout || REQUEST_TIMEOUT_MS;
    var timer = controller ? window.setTimeout(function () { controller.abort(); }, timeout) : null;
    var headers = { "X-Device-Key": (settings.credentials || state.credentials || {}).api_key || "" };
    var body = settings.body;
    if (settings.json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(settings.json);
    }
    if (settings.contentType) {
      headers["Content-Type"] = settings.contentType;
    }
    return window.fetch(options.api_base + path, {
      method: settings.method || "GET",
      headers: headers,
      body: body,
      cache: "no-store",
      credentials: "same-origin",
      keepalive: Boolean(settings.keepalive),
      signal: controller ? controller.signal : undefined
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (!response.ok) {
          throw apiError(data.error || ("Máy chủ trả lỗi " + response.status), response.status);
        }
        return data;
      });
    }, function (error) {
      if (error && error.name === "AbortError") {
        throw apiError("Hết thời gian chờ máy chủ", 0);
      }
      throw apiError("Không kết nối được máy chủ", 0);
    }).finally(function () {
      if (timer) {
        window.clearTimeout(timer);
      }
    });
  }

  function showSetup(message) {
    elements.app.hidden = true;
    elements.setup.hidden = false;
    elements.setupError.textContent = message || "";
    if (state.credentials) {
      elements.setupCode.value = state.credentials.device_code || "";
    }
    setConnection("off", "Chưa kết nối");
    window.setTimeout(function () { elements.setupCode.focus(); }, 0);
  }

  function showApp() {
    elements.setup.hidden = true;
    elements.app.hidden = false;
  }

  function applyHello(data) {
    state.device = data.device || null;
    state.config = data.config || null;
    speaker.configure(state.config);
    elements.deviceName.textContent = state.device ? state.device.device_code + " · " + state.device.name : "—";
    elements.person.textContent = data.blind_person ? data.blind_person.full_name : "Chưa gán";
  }

  function connect(credentials, fromForm) {
    window.clearTimeout(state.reconnectTimer);
    return api("/hello", {
      method: "POST",
      credentials: credentials,
      json: {
        device_code: credentials.device_code,
        app_version: options.app_version,
        model_name: options.model_name
      }
    }).then(function (data) {
      state.credentials = credentials;
      writeStorage(STORAGE_KEY, JSON.stringify(credentials));
      state.connected = true;
      applyHello(data);
      showApp();
      setConnection("on", "Đã kết nối");
      startHeartbeat();
      return true;
    }, function (error) {
      state.connected = false;
      if (error.status === 401) {
        if (!fromForm) {
          writeStorage(STORAGE_KEY, null);
        }
        state.credentials = fromForm ? state.credentials : null;
        showSetup("Mã thiết bị hoặc khóa thiết bị không đúng. Vui lòng kiểm tra lại.");
        speaker.say("Mã thiết bị hoặc khóa thiết bị không đúng.", { priority: 2 });
        return false;
      }
      if (fromForm) {
        elements.setupError.textContent = error.message + ". Đang thử lại...";
      } else {
        state.credentials = credentials;
        showApp();
      }
      setConnection("error", "Mất kết nối");
      state.reconnectTimer = window.setTimeout(function () { connect(credentials, fromForm); }, RECONNECT_MS);
      return false;
    });
  }

  function startHeartbeat() {
    window.clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = window.setInterval(heartbeat, (policy.heartbeat_s || 10) * 1000);
  }

  function heartbeat() {
    if (!state.credentials) {
      return;
    }
    api("/heartbeat", { method: "POST", json: {} }).then(function (data) {
      if (!state.connected) {
        state.connected = true;
        setConnection("on", state.running ? "Đang nhận diện" : "Đã kết nối");
      }
      if (state.config && data.config_updated_at && data.config_updated_at !== state.config.updated_at) {
        return api("/config").then(function (config) {
          state.config = config;
          speaker.configure(config);
        });
      }
      return null;
    }).catch(function (error) {
      if (error.status === 401) {
        handleUnauthorized();
        return;
      }
      state.connected = false;
      setConnection("error", "Mất kết nối");
    });
  }

  function handleUnauthorized() {
    stopRunning("Khóa thiết bị không còn hợp lệ.", false);
    window.clearInterval(state.heartbeatTimer);
    writeStorage(STORAGE_KEY, null);
    state.credentials = null;
    showSetup("Khóa thiết bị không còn hợp lệ (có thể đã được cấp lại). Vui lòng nhập lại.");
  }

  function describeCameraError(error) {
    var name = error && error.name;
    if (name === "NotAllowedError" || name === "SecurityError") {
      return "Bạn chưa cho phép dùng camera. Hãy cho phép camera trong trình duyệt rồi bấm Bắt đầu lại.";
    }
    if (name === "NotFoundError" || name === "OverconstrainedError") {
      return "Không tìm thấy camera trên thiết bị này.";
    }
    if (name === "NotReadableError") {
      return "Camera đang được ứng dụng khác sử dụng.";
    }
    return "Không mở được camera.";
  }

  function cameraConstraints() {
    var deviceId = elements.camera.value;
    var video = { width: { ideal: 1280 }, height: { ideal: 720 } };
    if (deviceId) {
      video.deviceId = { exact: deviceId };
    } else {
      video.facingMode = { ideal: "environment" };
    }
    return { video: video, audio: false };
  }

  function openCamera() {
    return navigator.mediaDevices.getUserMedia(cameraConstraints()).catch(function (error) {
      if (elements.camera.value && error && error.name === "OverconstrainedError") {
        elements.camera.value = "";
        return navigator.mediaDevices.getUserMedia(cameraConstraints());
      }
      throw error;
    });
  }

  function stopStream() {
    if (state.stream) {
      state.stream.getTracks().forEach(function (track) { track.stop(); });
    }
    state.stream = null;
    elements.video.srcObject = null;
    elements.stageEmpty.hidden = false;
    clearOverlay();
  }

  function attachStream(stream) {
    state.stream = stream;
    elements.video.srcObject = stream;
    elements.stageEmpty.hidden = true;
    return elements.video.play().catch(function () { return null; }).then(function () {
      fitStage();
      return listCameras();
    });
  }

  function listCameras() {
    if (!navigator.mediaDevices.enumerateDevices) {
      return Promise.resolve();
    }
    return navigator.mediaDevices.enumerateDevices().then(function (devices) {
      var cameras = devices.filter(function (device) { return device.kind === "videoinput"; });
      var activeTrack = state.stream ? state.stream.getVideoTracks()[0] : null;
      var activeId = activeTrack && activeTrack.getSettings ? activeTrack.getSettings().deviceId : "";
      var selected = elements.camera.value || readStorage(CAMERA_KEY) || "";
      elements.camera.innerHTML = "";
      var defaultOption = document.createElement("option");
      defaultOption.value = "";
      defaultOption.textContent = "Camera sau (mặc định)";
      elements.camera.appendChild(defaultOption);
      cameras.forEach(function (camera, index) {
        var option = document.createElement("option");
        option.value = camera.deviceId;
        option.textContent = camera.label || ("Camera " + (index + 1));
        elements.camera.appendChild(option);
      });
      var known = cameras.some(function (camera) { return camera.deviceId === selected; });
      elements.camera.value = known ? selected : "";
      elements.camera.dataset.active = activeId || "";
      elements.camera.parentElement.hidden = cameras.length < 2;
    }).catch(function () { return null; });
  }

  function fitStage() {
    var width = elements.video.videoWidth;
    var height = elements.video.videoHeight;
    if (width && height) {
      elements.stage.style.aspectRatio = width + " / " + height;
    }
  }

  function updateToggle() {
    var running = state.running || state.starting;
    elements.toggle.className = "bm-btn " + (running ? "bm-btn-stop" : "bm-btn-start");
    elements.toggle.setAttribute("aria-pressed", running ? "true" : "false");
    elements.toggle.setAttribute("aria-label", running
      ? "Dừng nhận diện vật cản. Phím tắt: phím cách"
      : "Bắt đầu nhận diện vật cản. Phím tắt: phím cách");
    elements.toggleText.textContent = running ? "DỪNG" : "BẮT ĐẦU";
    var icon = elements.toggle.querySelector("i");
    icon.className = "bi " + (running ? "bi-stop-circle-fill" : "bi-play-circle-fill");
    elements.toggle.disabled = state.stopping;
  }

  function openSession() {
    return api("/sessions", { method: "POST", json: { model_name: options.model_name + " (web)" } }).then(function (data) {
      state.sessionId = data.session_id;
      return data.session_id;
    });
  }

  function start() {
    if (state.running || state.starting || state.stopping || !state.credentials) {
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      var message = "Trình duyệt chặn camera vì trang không dùng HTTPS. Hãy mở bằng địa chỉ https.";
      showAlert(message, "info");
      speaker.say(message, { priority: 2, interrupt: true });
      return;
    }
    state.starting = true;
    updateToggle();
    showAlert("Đang mở camera...", "info");
    openCamera().then(function (stream) {
      return attachStream(stream);
    }).then(function () {
      return openSession();
    }).then(function () {
      state.starting = false;
      state.running = true;
      state.metrics = newMetrics();
      state.lastDetection = null;
      updateToggle();
      setConnection("on", "Đang nhận diện");
      var message = "Đã bắt đầu nhận diện. Hãy hướng camera về phía trước.";
      showAlert(message, "info");
      speaker.say(message, { priority: 1, interrupt: true });
      frameLoop();
    }).catch(function (error) {
      state.starting = false;
      stopStream();
      updateToggle();
      var message = error && error.status !== undefined
        ? "Không mở được phiên sử dụng: " + error.message
        : describeCameraError(error);
      if (error && error.status === 401) {
        handleUnauthorized();
        return;
      }
      showAlert(message, "info");
      speaker.say(message, { priority: 2, interrupt: true });
    });
  }

  function sessionStats() {
    var metrics = state.metrics;
    var elapsed = (performance.now() - metrics.startedAt) / 1000;
    return {
      frames: metrics.frames,
      avg_fps: elapsed > 0 ? Math.round(metrics.frames / elapsed * 100) / 100 : 0,
      avg_latency_ms: Math.round(average(metrics.roundTrips) * 10) / 10
    };
  }

  function closeSession(keepalive) {
    var sessionId = state.sessionId;
    state.sessionId = null;
    if (!sessionId) {
      return Promise.resolve();
    }
    return api("/sessions/" + sessionId, {
      method: "PUT",
      json: sessionStats(),
      keepalive: keepalive
    }).catch(function () { return null; });
  }

  function stopRunning(message, announce) {
    if (!state.running && !state.starting) {
      return Promise.resolve();
    }
    state.running = false;
    state.stopping = true;
    updateToggle();
    stopStream();
    return closeSession(false).then(function () {
      state.stopping = false;
      updateToggle();
      if (state.connected) {
        setConnection("on", "Đã kết nối");
      }
      elements.nearest.textContent = "Đã dừng nhận diện.";
      showAlert(message || "Đã dừng nhận diện.", "info");
      if (announce !== false) {
        speaker.stopAll();
        speaker.say(message || "Đã dừng nhận diện.", { priority: 2, interrupt: true });
      }
    });
  }

  function toggle() {
    if (state.running) {
      stopRunning();
    } else {
      start();
    }
  }

  function captureFrame() {
    var video = elements.video;
    var width = video.videoWidth;
    var height = video.videoHeight;
    if (!width || !height || video.readyState < 2) {
      return Promise.resolve(null);
    }
    var scale = Math.min(1, CAPTURE_LONG_SIDE / Math.max(width, height));
    var canvas = state.captureCanvas;
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    var context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return new Promise(function (resolve) {
      canvas.toBlob(function (blob) { resolve(blob); }, "image/jpeg", JPEG_QUALITY);
    });
  }

  function frameLoop() {
    if (state.loopBusy) {
      return;
    }
    state.loopBusy = true;
    var slowNoticeTimer = null;
    var step = function () {
      if (!state.running) {
        state.loopBusy = false;
        return;
      }
      var started = performance.now();
      captureFrame().then(function (blob) {
        if (!blob || !state.running) {
          return sleep(100);
        }
        if (state.metrics.frames === 0) {
          slowNoticeTimer = window.setTimeout(function () {
            if (state.metrics.frames === 0 && state.running) {
              showAlert("Máy chủ đang khởi động mô hình nhận diện, vui lòng chờ...", "info");
            }
          }, 1500);
        }
        return api("/detect?session_id=" + encodeURIComponent(state.sessionId), {
          method: "POST",
          body: blob,
          contentType: "image/jpeg",
          timeout: DETECT_TIMEOUT_MS
        }).then(function (data) {
          window.clearTimeout(slowNoticeTimer);
          if (!state.running) {
            return null;
          }
          handleDetection(data, performance.now() - started);
          var wait = MIN_FRAME_INTERVAL_MS - (performance.now() - started);
          return wait > 0 ? sleep(wait) : null;
        }, function (error) {
          window.clearTimeout(slowNoticeTimer);
          if (!state.running) {
            return null;
          }
          state.metrics.errors += 1;
          if (error.status === 401) {
            handleUnauthorized();
            return null;
          }
          if (error.status === 404 || error.status === 409) {
            return openSession().catch(function () { return sleep(1000); });
          }
          state.connected = false;
          setConnection("error", "Mất kết nối");
          if (state.metrics.errors === 1 || state.metrics.errors % 10 === 0) {
            showAlert("Mất kết nối máy chủ, đang thử lại...", "info");
            speaker.say("Mất kết nối máy chủ, đang thử lại.", { priority: 2 });
          }
          return sleep(1000);
        });
      }).then(step, function () {
        sleep(500).then(step);
      });
    };
    step();
  }

  function handleDetection(data, roundTripMs) {
    var metrics = state.metrics;
    var now = performance.now();
    metrics.frames += 1;
    metrics.roundTrips.push(roundTripMs);
    if (data.timing) {
      metrics.serverProcess.push(data.timing.process_ms);
      metrics.inference.push(data.timing.infer_ms);
    }
    metrics.recentFrameTimes.push(now);
    while (metrics.recentFrameTimes.length && now - metrics.recentFrameTimes[0] > 3000) {
      metrics.recentFrameTimes.shift();
    }
    if (!state.connected) {
      state.connected = true;
    }
    setConnection("on", "Đang nhận diện");
    state.lastDetection = data;
    drawDetections(data);
    updateNearest(data);
    updateStats(data);
    if (data.alert) {
      metrics.alerts += 1;
      if (data.alert_saved) {
        metrics.alertsSaved += 1;
      }
      metrics.messages.push(data.alert.message);
      elements.alertCount.textContent = String(metrics.alerts);
      showAlert(data.alert.message, data.alert.level === "DANGER" ? "danger" : "warning");
      speaker.say(data.alert.message, {
        priority: data.alert.priority,
        distance: data.alert.distance_m,
        interrupt: data.alert.interrupt,
        rateWpm: data.alert.rate_wpm,
        volume: data.alert.volume
      });
    }
  }

  function updateNearest(data) {
    var nearest = data.nearest;
    if (!nearest) {
      elements.nearest.textContent = data.objects && data.objects.length
        ? "Có " + data.objects.length + " vật thể, không có vật cản ở phía trước."
        : "Không phát hiện vật cản.";
      return;
    }
    elements.nearest.textContent = "Gần nhất: " + nearest.class_name_vi + " " +
      (POSITION_TEXT[nearest.position] || "") + ", " + formatNumber(nearest.distance_m, 1) + " mét.";
  }

  function updateStats(data) {
    var metrics = state.metrics;
    var times = metrics.recentFrameTimes;
    if (times.length > 1) {
      var span = (times[times.length - 1] - times[0]) / 1000;
      if (span > 0) {
        elements.fps.textContent = formatNumber((times.length - 1) / span, 1);
      }
    }
    var recent = metrics.roundTrips.slice(-20);
    elements.latency.textContent = Math.round(average(recent)) + " ms";
    if (data.inference_device) {
      elements.engine.textContent = data.inference_device === "cpu" ? "CPU" : "GPU (" + data.inference_device + ")";
    }
  }

  function clearOverlay() {
    var context = elements.overlay.getContext("2d");
    context.clearRect(0, 0, elements.overlay.width, elements.overlay.height);
  }

  function contentRect() {
    var stageWidth = elements.overlay.clientWidth;
    var stageHeight = elements.overlay.clientHeight;
    var videoWidth = elements.video.videoWidth || stageWidth;
    var videoHeight = elements.video.videoHeight || stageHeight;
    var scale = Math.min(stageWidth / videoWidth, stageHeight / videoHeight);
    var width = videoWidth * scale;
    var height = videoHeight * scale;
    return { x: (stageWidth - width) / 2, y: (stageHeight - height) / 2, width: width, height: height };
  }

  function drawDetections(data) {
    var canvas = elements.overlay;
    var ratio = window.devicePixelRatio || 1;
    var cssWidth = canvas.clientWidth;
    var cssHeight = canvas.clientHeight;
    if (canvas.width !== Math.round(cssWidth * ratio) || canvas.height !== Math.round(cssHeight * ratio)) {
      canvas.width = Math.round(cssWidth * ratio);
      canvas.height = Math.round(cssHeight * ratio);
    }
    fitStage();
    var context = canvas.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, cssWidth, cssHeight);
    var rect = contentRect();
    var zone = policy.center_zone || 0.6;
    context.strokeStyle = "rgba(0, 229, 255, 0.55)";
    context.lineWidth = 2;
    context.setLineDash([8, 8]);
    [(1 - zone) / 2, (1 + zone) / 2].forEach(function (fraction) {
      var x = rect.x + rect.width * fraction;
      context.beginPath();
      context.moveTo(x, rect.y);
      context.lineTo(x, rect.y + rect.height);
      context.stroke();
    });
    context.setLineDash([]);
    var fontSize = Math.max(14, Math.round(rect.width / 32));
    context.font = "700 " + fontSize + "px Segoe UI, Roboto, Arial, sans-serif";
    context.textBaseline = "top";
    var objects = (data.objects || []).slice().sort(function (a, b) {
      return (b.held ? 1 : 0) - (a.held ? 1 : 0);
    });
    objects.forEach(function (obj) {
      var x1 = rect.x + obj.box[0] * rect.width;
      var y1 = rect.y + obj.box[1] * rect.height;
      var x2 = rect.x + obj.box[2] * rect.width;
      var y2 = rect.y + obj.box[3] * rect.height;
      var color = LEVEL_COLORS[obj.level] || LEVEL_COLORS.SAFE;
      context.lineWidth = obj.held ? 2 : 4;
      context.strokeStyle = color;
      context.strokeRect(x1, y1, x2 - x1, y2 - y1);
      if (obj.target) {
        context.lineWidth = 2;
        context.strokeStyle = "#ffffff";
        context.strokeRect(x1 - 5, y1 - 5, x2 - x1 + 10, y2 - y1 + 10);
      }
      if (obj.held) {
        return;
      }
      var label = obj.class_name_vi + " " + formatNumber(obj.distance_m, 1) + " m";
      var textWidth = context.measureText(label).width + 12;
      var labelY = y1 - fontSize - 8 < rect.y ? y1 + 2 : y1 - fontSize - 8;
      context.fillStyle = color;
      context.fillRect(x1, labelY, textWidth, fontSize + 8);
      context.fillStyle = "#000000";
      context.fillText(label, x1 + 6, labelY + 4);
    });
  }

  function sendSos() {
    if (!state.credentials) {
      return;
    }
    var now = performance.now();
    if (now - state.sosLastPress < (policy.sos_debounce_s || 2) * 1000 || state.sosSending) {
      return;
    }
    state.sosLastPress = now;
    window.clearTimeout(state.sosRetryTimer);
    showAlert("SOS: đang gửi tín hiệu cầu cứu...", "sos");
    deliverSos(true);
  }

  function deliverSos(firstAttempt) {
    state.sosSending = true;
    api("/sos", { method: "POST", json: {} }).then(function (data) {
      state.sosSending = false;
      var message = "Đã gửi tín hiệu cầu cứu";
      showAlert("SOS: " + message + " (#" + data.sos_id + ") tới người thân.", "sos");
      speaker.say(message + ".", { priority: 3, interrupt: true });
    }, function (error) {
      state.sosSending = false;
      if (error.status === 401) {
        handleUnauthorized();
        return;
      }
      showAlert("SOS: chưa gửi được, đang thử lại...", "sos");
      if (firstAttempt) {
        speaker.say("Chưa gửi được tín hiệu cầu cứu, đang thử lại.", { priority: 3, interrupt: true });
      }
      state.sosRetryTimer = window.setTimeout(function () { deliverSos(false); }, (policy.sos_retry_s || 3) * 1000);
    });
  }

  function setMuted(muted, announce) {
    if (!muted) {
      speaker.setMuted(false);
    }
    elements.mute.setAttribute("aria-pressed", muted ? "true" : "false");
    elements.mute.setAttribute("aria-label", muted ? "Bật lại tiếng đọc cảnh báo. Phím tắt: M" : "Tắt tiếng đọc cảnh báo. Phím tắt: M");
    elements.muteText.textContent = muted ? "Bật tiếng" : "Tắt tiếng";
    elements.mute.querySelector("i").className = "bi " + (muted ? "bi-volume-mute-fill" : "bi-volume-up-fill");
    writeStorage(MUTE_KEY, muted ? "1" : null);
    if (announce) {
      if (muted) {
        speaker.stopAll();
        speaker.say("Đã tắt tiếng.", { priority: 2 });
        window.setTimeout(function () { speaker.setMuted(true); }, 1200);
      } else {
        speaker.say("Đã bật tiếng.", { priority: 2, interrupt: true });
      }
    } else if (muted) {
      speaker.setMuted(true);
    }
  }

  function isTypingTarget(target) {
    if (!target) {
      return false;
    }
    var tag = (target.tagName || "").toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select" || target.isContentEditable;
  }

  document.addEventListener("keydown", function (event) {
    if (elements.app.hidden || isTypingTarget(event.target) || event.ctrlKey || event.altKey || event.metaKey) {
      return;
    }
    if (event.code === "Space" || event.key === " ") {
      event.preventDefault();
      if (!event.repeat) {
        toggle();
      }
    } else if (event.code === "KeyS" || event.key === "s" || event.key === "S") {
      event.preventDefault();
      if (!event.repeat) {
        sendSos();
      }
    } else if (event.code === "KeyM" || event.key === "m" || event.key === "M") {
      event.preventDefault();
      if (!event.repeat) {
        setMuted(!speaker.muted, true);
      }
    }
  });

  document.addEventListener("keyup", function (event) {
    if (!elements.app.hidden && !isTypingTarget(event.target) && (event.code === "Space" || event.key === " ")) {
      event.preventDefault();
    }
  });

  elements.toggle.addEventListener("click", toggle);
  elements.sos.addEventListener("click", sendSos);
  elements.mute.addEventListener("click", function () { setMuted(!speaker.muted, true); });
  elements.logout.addEventListener("click", function () {
    stopRunning("Đã dừng nhận diện.", false).then(function () {
      window.clearInterval(state.heartbeatTimer);
      writeStorage(STORAGE_KEY, null);
      state.credentials = null;
      state.connected = false;
      elements.setupKey.value = "";
      showSetup("");
    });
  });
  elements.camera.addEventListener("change", function () {
    writeStorage(CAMERA_KEY, elements.camera.value || null);
    if (!state.running) {
      return;
    }
    if (state.stream) {
      state.stream.getTracks().forEach(function (track) { track.stop(); });
    }
    openCamera().then(attachStream).catch(function (error) {
      showAlert(describeCameraError(error), "info");
    });
  });

  elements.setupForm.addEventListener("submit", function (event) {
    event.preventDefault();
    var credentials = {
      device_code: elements.setupCode.value.trim().toUpperCase(),
      api_key: elements.setupKey.value.trim()
    };
    if (!credentials.device_code || !credentials.api_key) {
      elements.setupError.textContent = "Vui lòng nhập đủ mã thiết bị và khóa thiết bị.";
      return;
    }
    elements.setupSubmit.disabled = true;
    elements.setupError.textContent = "Đang kết nối...";
    connect(credentials, true).then(function (ok) {
      elements.setupSubmit.disabled = false;
      if (ok) {
        elements.setupError.textContent = "";
        announceWelcome();
      }
    });
  });

  window.addEventListener("pagehide", function () {
    if (state.running) {
      state.running = false;
      closeSession(true);
    }
  });

  window.addEventListener("resize", function () {
    if (state.lastDetection && state.running) {
      drawDetections(state.lastDetection);
    }
  });

  function announceWelcome() {
    var message = "Chế độ người khiếm thị. Bấm nút Bắt đầu hoặc phím cách để bật camera. Bấm nút S O S hoặc phím S để gửi tín hiệu cầu cứu.";
    speaker.say(message, { priority: 1 });
  }

  window.BlindAssistMode = {
    metrics: function () {
      var metrics = state.metrics;
      var elapsed = (performance.now() - metrics.startedAt) / 1000;
      return {
        running: state.running,
        sessionId: state.sessionId,
        frames: metrics.frames,
        alerts: metrics.alerts,
        alertsSaved: metrics.alertsSaved,
        errors: metrics.errors,
        elapsedSeconds: elapsed,
        fps: elapsed > 0 ? metrics.frames / elapsed : 0,
        roundTripAvgMs: average(metrics.roundTrips),
        roundTripP50Ms: percentile(metrics.roundTrips, 0.5),
        roundTripP95Ms: percentile(metrics.roundTrips, 0.95),
        serverProcessAvgMs: average(metrics.serverProcess),
        inferenceAvgMs: average(metrics.inference),
        messages: metrics.messages.slice(-20),
        voice: speaker.voice ? speaker.voice.name : null
      };
    }
  };

  function initialize() {
    if (!window.isSecureContext) {
      elements.secureWarning.hidden = false;
    }
    setMuted(readStorage(MUTE_KEY) === "1", false);
    updateToggle();
    var presetNode = document.getElementById("bm-preset");
    if (presetNode) {
      try {
        var preset = JSON.parse(presetNode.textContent);
        writeStorage(STORAGE_KEY, JSON.stringify({ device_code: preset.device_code, api_key: preset.api_key }));
      } catch (error) {
        writeStorage(STORAGE_KEY, null);
      }
      presetNode.parentNode.removeChild(presetNode);
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, "", options.page_url);
      }
    }
    var credentials = loadCredentials();
    if (!credentials) {
      showSetup("");
      speaker.say("Chế độ người khiếm thị. Vui lòng nhập mã thiết bị và khóa thiết bị.", { priority: 1 });
      return;
    }
    state.credentials = credentials;
    elements.deviceName.textContent = credentials.device_code;
    showApp();
    setConnection("warn", "Đang kết nối...");
    connect(credentials, false).then(function (ok) {
      if (ok) {
        announceWelcome();
      }
    });
  }

  initialize();
})();
