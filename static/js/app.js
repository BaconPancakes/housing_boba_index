/* ============================================================
   Housing Boba Index — Frontend Application
   ============================================================ */

(function () {
  "use strict";

  const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
  const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>';
  const DEFAULT_CENTER = [37.378, -122.036];
  const DEFAULT_ZOOM = 14;
  const CIRCUMFERENCE = 2 * Math.PI * 52;

  const GRADE_COLORS = {
    S: "#fbbf24", A: "#34d399", B: "#60a5fa",
    C: "#a78bfa", D: "#fb923c", F: "#f87171",
  };

  // ---- DOM refs ----
  var els = {
    form:        document.getElementById("search-form"),
    input:       document.getElementById("address-input"),
    resultPanel: document.getElementById("result-panel"),
    loadPanel:   document.getElementById("loading-panel"),
    errorPanel:  document.getElementById("error-panel"),
    errorMsg:    document.getElementById("error-msg"),
    scoreArc:    document.getElementById("score-arc"),
    scoreValue:  document.getElementById("score-value"),
    gradeBadge:  document.getElementById("grade-badge"),
    summary:     document.getElementById("summary-text"),
    statShops:   document.getElementById("stat-shops"),
    statPremium: document.getElementById("stat-premium"),
    statCurated: document.getElementById("stat-curated"),
    statClosest: document.getElementById("stat-closest"),
    shopList:    document.getElementById("shop-list"),
    shopsHead:   document.getElementById("shops-heading"),
    priceCard:   document.getElementById("price-card"),
    priceValue:  document.getElementById("price-value"),
    priceZip:    document.getElementById("price-zip"),
    corrToggle:  document.getElementById("correlation-toggle"),
    corrWrap:    document.getElementById("correlation-chart-wrap"),
    corrCanvas:  document.getElementById("correlation-chart"),
    corrLoading: document.getElementById("corr-loading"),
  };

  // ---- Leaflet setup ----
  var map = L.map("map", { zoomControl: false }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
  L.tileLayer(TILE_URL, { attribution: TILE_ATTR, maxZoom: 19 }).addTo(map);
  L.control.zoom({ position: "topright" }).addTo(map);

  var homeMarker = null;
  var radiusCircle = null;
  var shopMarkers = L.layerGroup().addTo(map);
  var shopMarkerMap = {};

  // ---- Correlation state ----
  var correlationData = null;
  var correlationChart = null;
  var correlationChartFS = null;
  var correlationOpen = false;
  var correlationLoading = false;
  var currentPoint = null;
  var corrFSBtn = document.getElementById("corr-fullscreen-btn");
  var corrOverlay = document.getElementById("corr-overlay");
  var corrOverlayClose = document.getElementById("corr-overlay-close");
  var corrCanvasFS = document.getElementById("correlation-chart-fs");

  // ---- Tier metadata ----
  var TIER_META = {
    premium:     { color: "#f0a040", icon: "\u2B50", label: "Premium", tip: "Top-tier, widely recognized boba brand" },
    curated:     { color: "#34d399", icon: "\u2714\uFE0F", label: "Curated",  tip: "Hand-picked notable shop" },
    default:     { color: "#60a5fa", icon: "",       label: "",        tip: "" },
    blacklisted: { color: "#6b7280", icon: "",       label: "",        tip: "" },
  };

  function shopTier(shop) {
    if (shop.is_blacklisted) return "blacklisted";
    if (shop.is_premium) return "premium";
    if (shop.is_curated) return "curated";
    return "default";
  }

  // ---- Icons ----
  function bobaIcon(shop) {
    var tier = shopTier(shop);
    var meta = TIER_META[tier];
    var strokeW = tier === "premium" ? 2.5 : 2;
    return L.divIcon({
      className: "",
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      html: '<svg width="26" height="26" viewBox="0 0 26 26"><circle cx="13" cy="13" r="11" fill="' + meta.color + '" fill-opacity=".85" stroke="#fff" stroke-width="' + strokeW + '"/><text x="13" y="17" text-anchor="middle" font-size="12">\uD83E\uDDCB</text></svg>',
    });
  }

  var homeIcon = L.divIcon({
    className: "",
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    html: '<div class="home-pulse"></div>',
  });

  // ---- Events ----
  els.form.addEventListener("submit", function (e) {
    e.preventDefault();
    var addr = els.input.value.trim();
    if (addr) fetchScore({ address: addr });
  });

  document.querySelectorAll(".quick-link").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var addr = btn.dataset.addr;
      els.input.value = addr;
      fetchScore({ address: addr });
    });
  });

  map.on("click", function (e) {
    els.input.value = "";
    fetchScore({ lat: e.latlng.lat, lng: e.latlng.lng });
  });

  els.corrToggle.addEventListener("click", function () {
    correlationOpen = !correlationOpen;
    els.corrWrap.classList.toggle("hidden", !correlationOpen);
    corrFSBtn.classList.toggle("hidden", !correlationOpen);
    els.corrToggle.textContent = correlationOpen ? "Price Correlation \u25BE" : "Price Correlation \u25B8";
    if (correlationOpen && !correlationData && !correlationLoading) {
      fetchCorrelation();
    } else if (correlationOpen && correlationData) {
      renderCorrelationChart(correlationData, currentPoint);
    }
  });

  corrFSBtn.addEventListener("click", function () {
    corrOverlay.classList.remove("hidden");
    if (correlationData) renderFSChart(correlationData, currentPoint);
  });
  corrOverlayClose.addEventListener("click", function () {
    corrOverlay.classList.add("hidden");
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !corrOverlay.classList.contains("hidden")) {
      corrOverlay.classList.add("hidden");
    }
  });

  // ---- API calls ----
  function fetchScore(params) {
    showPanel("loading");
    var qs = new URLSearchParams(params).toString();
    fetch("/api/score?" + qs)
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || "Request failed"); });
        return r.json();
      })
      .then(renderResult)
      .catch(function (err) {
        showPanel("error");
        els.errorMsg.textContent = err.message;
      });
  }

  function fetchCorrelation() {
    correlationLoading = true;
    els.corrLoading.classList.remove("hidden");
    els.corrCanvas.style.display = "none";

    fetch("/api/correlation")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        correlationData = data;
        correlationLoading = false;
        els.corrLoading.classList.add("hidden");
        els.corrCanvas.style.display = "";
        renderCorrelationChart(data, currentPoint);
      })
      .catch(function () {
        correlationLoading = false;
        els.corrLoading.innerHTML = '<p style="color:#f87171">Failed to load correlation data.</p>';
      });
  }

  // ---- Render score ----
  function renderResult(data) {
    showPanel("result");

    var pct = Math.min(data.index, 1);
    var offset = CIRCUMFERENCE * (1 - pct);
    els.scoreArc.style.strokeDashoffset = offset;
    els.scoreArc.style.stroke = GRADE_COLORS[data.grade] || "#f0a040";
    animateNumber(els.scoreValue, data.index, 1200, 2);

    els.gradeBadge.textContent = data.grade;
    els.gradeBadge.className = "grade-badge grade-" + data.grade;
    els.summary.textContent = data.summary;

    var premiumCount = (data.breakdown || []).filter(function (b) { return b.tier === "premium"; }).length;
    var curatedCount = (data.breakdown || []).filter(function (b) { return b.tier === "curated"; }).length;
    var closest = data.shops && data.shops.length
      ? Math.min.apply(null, data.shops.map(function (s) { return s.distance_miles; }))
      : null;

    els.statShops.textContent = data.shop_count;
    els.statPremium.textContent = premiumCount;
    els.statCurated.textContent = curatedCount;
    els.statClosest.textContent = closest !== null ? closest.toFixed(2) : "\u2014";

    // Price card
    var pe = data.price_estimate;
    els.priceCard.classList.remove("hidden");
    if (pe) {
      var redfinUrl = "https://www.redfin.com/zipcode/" + pe.zip_code + "/housing-market";
      els.priceValue.textContent = formatPrice(pe.median_price);
      els.priceZip.innerHTML = '<a href="' + redfinUrl + '" target="_blank" rel="noopener" class="price-redfin-link">' + pe.zip_code + " " + pe.label + ' \u2197</a>';
      els.priceCard.classList.remove("price-unavailable");
    } else {
      els.priceValue.textContent = "\u2014";
      els.priceZip.textContent = "No price data available";
      els.priceCard.classList.add("price-unavailable");
    }

    currentPoint = { boba_index: data.index, median_price: pe ? pe.median_price : null, label: "You", grade: data.grade };
    if (correlationOpen && correlationData) renderCorrelationChart(correlationData, currentPoint);
    if (correlationChartFS && correlationData) renderFSChart(correlationData, currentPoint);

    // Map markers (build before shop list so we can reference them)
    shopMarkers.clearLayers();
    shopMarkerMap = {};
    if (homeMarker) map.removeLayer(homeMarker);
    if (radiusCircle) map.removeLayer(radiusCircle);

    homeMarker = L.marker([data.lat, data.lng], { icon: homeIcon })
      .addTo(map)
      .bindPopup('<div class="boba-popup"><strong>Search Location</strong><br>' + escapeHtml(data.address) + '<br><em>Index: ' + data.index.toFixed(2) + ' (' + data.grade + ')</em></div>');

    var radiusMeters = (data.search_radius_miles || 3) * 1609.34;
    radiusCircle = L.circle([data.lat, data.lng], {
      radius: radiusMeters,
      color: GRADE_COLORS[data.grade] || "#f0a040",
      fillColor: GRADE_COLORS[data.grade] || "#f0a040",
      fillOpacity: 0.06,
      weight: 1.5,
      dashArray: "6 4",
    }).addTo(map);

    (data.shops || []).forEach(function (shop, i) {
      var googleUrl = googleMapsUrl(shop.name, shop.lat, shop.lng);
      var tier = shopTier(shop);
      var meta = TIER_META[tier];
      var marker = L.marker([shop.lat, shop.lng], { icon: bobaIcon(shop) });
      var popupClass = "boba-popup" + (meta.label ? " popup-" + tier : "");
      var tierLine = meta.label
        ? '<div class="pop-tier pop-tier-' + tier + '" title="' + meta.tip + '">' + meta.icon + ' ' + meta.label + '</div>'
        : "";
      marker.bindPopup(
        '<div class="' + popupClass + '">' +
          '<strong><a href="' + googleUrl + '" target="_blank" rel="noopener" style="color:#1e293b;text-decoration:underline">' + escapeHtml(shop.name) + '</a></strong>' +
          '<div class="pop-dist">' + shop.distance_miles.toFixed(2) + ' mi away</div>' +
          tierLine +
        '</div>'
      );
      shopMarkers.addLayer(marker);
      shopMarkerMap[i] = marker;
    });

    // Shop list
    els.shopList.innerHTML = "";
    (data.shops || []).forEach(function (shop, i) {
      var tier = shopTier(shop);
      var meta = TIER_META[tier];
      var googleUrl = googleMapsUrl(shop.name, shop.lat, shop.lng);
      var li = document.createElement("li");
      li.className = "shop-item" + (meta.label ? " shop-item-" + tier : "");
      if (meta.tip) li.title = meta.tip;
      var iconHtml = meta.icon
        ? '<span class="tier-icon">' + meta.icon + '</span>'
        : "";
      li.innerHTML =
        '<div style="min-width:0">' +
          '<div class="shop-name">' +
            iconHtml +
            '<a href="' + googleUrl + '" target="_blank" rel="noopener" class="shop-link">' +
              escapeHtml(shop.name) + ' <span class="link-icon">\u2197</span>' +
            '</a>' +
          '</div>' +
          '<div style="font-size:.73rem;color:#8b8fa3;margin-top:2px">' + escapeHtml(shop.address) + '</div>' +
        '</div>' +
        '<div class="shop-details">' +
          '<span class="shop-dist">' + shop.distance_miles.toFixed(2) + ' mi</span>' +
        '</div>';
      li.addEventListener("click", function (e) {
        if (e.target.tagName === "A") return;
        var marker = shopMarkerMap[i];
        if (marker) {
          map.flyTo([shop.lat, shop.lng], 16, { duration: 0.6 });
          setTimeout(function () { marker.openPopup(); }, 650);
        }
      });
      els.shopList.appendChild(li);
    });
    els.shopsHead.textContent = "Nearby Shops (" + data.shop_count + ")";

    var allLats = [data.lat].concat((data.shops || []).map(function (s) { return s.lat; }));
    var allLngs = [data.lng].concat((data.shops || []).map(function (s) { return s.lng; }));
    var bounds = L.latLngBounds(
      [Math.min.apply(null, allLats) - 0.005, Math.min.apply(null, allLngs) - 0.005],
      [Math.max.apply(null, allLats) + 0.005, Math.max.apply(null, allLngs) + 0.005]
    );
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });

    if (data.address && !els.input.value) {
      els.input.value = data.address;
    }
  }

  // ---- Correlation chart ----
  var GRADE_BANDS = [
    { min: 0,    max: 0.20, grade: "F", color: GRADE_COLORS.F },
    { min: 0.20, max: 0.40, grade: "D", color: GRADE_COLORS.D },
    { min: 0.40, max: 0.60, grade: "C", color: GRADE_COLORS.C },
    { min: 0.60, max: 0.75, grade: "B", color: GRADE_COLORS.B },
    { min: 0.75, max: 0.90, grade: "A", color: GRADE_COLORS.A },
    { min: 0.90, max: 1.00, grade: "S", color: GRADE_COLORS.S },
  ];

  var gradeBandsPlugin = {
    id: "gradeBands",
    beforeDraw: function (chart) {
      var ctx = chart.ctx;
      var xScale = chart.scales.x;
      var yScale = chart.scales.y;
      var top = yScale.top;
      var bottom = yScale.bottom;

      GRADE_BANDS.forEach(function (band) {
        var x0 = xScale.getPixelForValue(band.min);
        var x1 = xScale.getPixelForValue(band.max);
        ctx.save();
        ctx.fillStyle = band.color + "18";
        ctx.fillRect(x0, top, x1 - x0, bottom - top);

        ctx.fillStyle = band.color + "90";
        ctx.font = "bold 11px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillText(band.grade, (x0 + x1) / 2, top + 4);
        ctx.restore();
      });

      [0.20, 0.40, 0.60, 0.75, 0.90].forEach(function (val) {
        var x = xScale.getPixelForValue(val);
        ctx.save();
        ctx.strokeStyle = "rgba(139,143,163,0.25)";
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(x, top);
        ctx.lineTo(x, bottom);
        ctx.stroke();
        ctx.restore();
      });
    },
  };

  function corrDatasets(data, current) {
    var points = data
      .filter(function (d) { return d.median_price !== null; })
      .map(function (d) {
        return { x: d.boba_index, y: d.median_price, label: d.label, lat: d.lat, lng: d.lng, zip: d.zip_code, grade: d.grade };
      });
    var ds = [{
      label: "Bay Area Neighborhoods",
      data: points,
      backgroundColor: "rgba(200, 210, 230, 0.7)",
      borderColor: "rgba(200, 210, 230, 0.9)",
      pointRadius: 5,
      pointHoverRadius: 8,
    }];
    if (current && current.median_price !== null) {
      ds.push({
        label: "Your Search",
        data: [{ x: current.boba_index, y: current.median_price, label: current.label }],
        backgroundColor: "#f0a040",
        borderColor: "#f0a040",
        pointRadius: 10,
        pointStyle: "star",
        pointHoverRadius: 13,
      });
    }
    return ds;
  }

  function corrChartOptions(onClickPt) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      onClick: function (_evt, elements) {
        if (!elements.length) return;
        var el = elements[0];
        var chart = this;
        var pt = chart.data.datasets[el.datasetIndex].data[el.index];
        if (pt && pt.lat && pt.lng) onClickPt(pt);
      },
      plugins: {
        legend: { display: true, labels: { color: "#8b8fa3", font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              var pt = ctx.raw;
              var zip = pt.zip ? " (" + pt.zip + ")" : "";
              var grade = pt.grade ? " (" + pt.grade + ")" : "";
              return pt.label + zip + ": Index " + pt.x.toFixed(2) + grade + " / $" + (pt.y / 1e6).toFixed(1) + "M";
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: "Boba Index", color: "#8b8fa3" },
          min: 0, max: 1,
          ticks: { color: "#8b8fa3" },
          grid: { color: "rgba(45,49,61,0.5)" },
        },
        y: {
          title: { display: true, text: "Median SFH Sale Price ($)", color: "#8b8fa3" },
          ticks: {
            color: "#8b8fa3",
            callback: function (v) { return "$" + (v / 1e6).toFixed(1) + "M"; },
          },
          grid: { color: "rgba(45,49,61,0.5)" },
        },
      },
    };
  }

  function searchFromPoint(pt) {
    corrOverlay.classList.add("hidden");
    els.input.value = pt.label;
    fetchScore({ lat: pt.lat, lng: pt.lng });
  }

  function renderCorrelationChart(data, current) {
    if (!data || !data.length) return;
    var ds = corrDatasets(data, current);
    if (correlationChart) {
      correlationChart.data.datasets = ds;
      correlationChart.update();
      return;
    }
    correlationChart = new Chart(els.corrCanvas, {
      type: "scatter",
      data: { datasets: ds },
      options: corrChartOptions(searchFromPoint),
      plugins: [gradeBandsPlugin],
    });
  }

  function renderFSChart(data, current) {
    if (!data || !data.length) return;
    var ds = corrDatasets(data, current);
    if (correlationChartFS) {
      correlationChartFS.data.datasets = ds;
      correlationChartFS.update();
      return;
    }
    correlationChartFS = new Chart(corrCanvasFS, {
      type: "scatter",
      data: { datasets: ds },
      options: corrChartOptions(searchFromPoint),
      plugins: [gradeBandsPlugin],
    });
  }

  // ---- Helpers ----
  function showPanel(which) {
    els.resultPanel.classList.toggle("hidden", which !== "result");
    els.loadPanel.classList.toggle("hidden", which !== "loading");
    els.errorPanel.classList.toggle("hidden", which !== "error");
  }

  function formatPrice(n) {
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
    if (n >= 1e3) return "$" + (n / 1e3).toFixed(0) + "K";
    return "$" + n;
  }

  function animateNumber(el, target, durationMs, decimals) {
    var dp = decimals !== undefined ? decimals : 1;
    var start = parseFloat(el.textContent) || 0;
    var diff = target - start;
    var startTime = performance.now();
    function step(now) {
      var elapsed = now - startTime;
      var progress = Math.min(elapsed / durationMs, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = (start + diff * eased).toFixed(dp);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function googleMapsUrl(name, lat, lng) {
    var q = encodeURIComponent(name);
    return "https://www.google.com/maps/search/" + q + "/@" + lat + "," + lng + ",17z";
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  // ---- Sidebar resize ----
  (function () {
    var handle = document.getElementById("sidebar-resize");
    var sidebar = document.getElementById("sidebar");
    if (!handle || !sidebar) return;
    var dragging = false;

    handle.addEventListener("mousedown", function (e) {
      e.preventDefault();
      dragging = true;
      handle.classList.add("active");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    });

    document.addEventListener("mousemove", function (e) {
      if (!dragging) return;
      var newW = Math.min(Math.max(e.clientX, 300), 700);
      sidebar.style.width = newW + "px";
      map.invalidateSize();
    });

    document.addEventListener("mouseup", function () {
      if (!dragging) return;
      dragging = false;
      handle.classList.remove("active");
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      map.invalidateSize();
    });
  })();
})();
