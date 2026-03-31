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
    statClosest: document.getElementById("stat-closest"),
    statAvg:     document.getElementById("stat-avg-rating"),
    shopList:    document.getElementById("shop-list"),
    shopsHead:   document.getElementById("shops-heading"),
    priceCard:   document.getElementById("price-card"),
    priceValue:  document.getElementById("price-value"),
    priceSqft:   document.getElementById("price-sqft"),
    priceZip:    document.getElementById("price-zip"),
    corrToggle:  document.getElementById("correlation-toggle"),
    corrWrap:    document.getElementById("correlation-chart-wrap"),
    corrCanvas:  document.getElementById("correlation-chart"),
  };

  // ---- Leaflet setup ----
  var map = L.map("map", { zoomControl: false }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
  L.tileLayer(TILE_URL, { attribution: TILE_ATTR, maxZoom: 19 }).addTo(map);
  L.control.zoom({ position: "topright" }).addTo(map);

  var homeMarker = null;
  var radiusCircle = null;
  var shopMarkers = L.layerGroup().addTo(map);

  // ---- Correlation state ----
  var correlationData = null;
  var correlationChart = null;
  var correlationOpen = false;
  var currentPoint = null;

  // ---- Icons ----
  function bobaIcon(isPremium) {
    var color = isPremium ? "#f0a040" : "#60a5fa";
    return L.divIcon({
      className: "",
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      html: '<svg width="26" height="26" viewBox="0 0 26 26"><circle cx="13" cy="13" r="11" fill="' + color + '" fill-opacity=".85" stroke="#fff" stroke-width="2"/><text x="13" y="17" text-anchor="middle" font-size="12">\uD83E\uDDCB</text></svg>',
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
    els.corrToggle.textContent = correlationOpen ? "Price Correlation \u25BE" : "Price Correlation \u25B8";
    if (correlationOpen && !correlationData) {
      fetchCorrelation();
    } else if (correlationOpen && correlationData) {
      renderCorrelationChart(correlationData, currentPoint);
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
    fetch("/api/correlation")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        correlationData = data;
        renderCorrelationChart(data, currentPoint);
      })
      .catch(function () {});
  }

  // ---- Render score ----
  function renderResult(data) {
    showPanel("result");

    var pct = data.index;
    var offset = CIRCUMFERENCE * (1 - pct);
    els.scoreArc.style.strokeDashoffset = offset;
    els.scoreArc.style.stroke = GRADE_COLORS[data.grade] || "#f0a040";
    animateNumber(els.scoreValue, data.index, 1200, 2);

    els.gradeBadge.textContent = data.grade;
    els.gradeBadge.className = "grade-badge grade-" + data.grade;
    els.summary.textContent = data.summary;

    var premiumCount = (data.breakdown || []).filter(function (b) { return b.brand_multiplier > 1; }).length;
    var closest = data.shops && data.shops.length
      ? Math.min.apply(null, data.shops.map(function (s) { return s.distance_miles; }))
      : null;
    var avgRating = data.shops && data.shops.length
      ? data.shops.reduce(function (sum, s) { return sum + (s.rating || 0); }, 0) / data.shops.length
      : 0;

    els.statShops.textContent = data.shop_count;
    els.statPremium.textContent = premiumCount;
    els.statClosest.textContent = closest !== null ? closest.toFixed(2) : "\u2014";
    els.statAvg.textContent = avgRating ? avgRating.toFixed(1) + "\u2605" : "\u2014";

    // Price card
    var pe = data.price_estimate;
    if (pe) {
      els.priceCard.classList.remove("hidden");
      els.priceValue.textContent = formatPrice(pe.median_price);
      els.priceSqft.textContent = "$" + pe.price_per_sqft.toLocaleString();
      els.priceZip.textContent = pe.zip_code + " " + pe.label;
    } else {
      els.priceCard.classList.add("hidden");
    }

    currentPoint = { boba_index: data.index, median_price: pe ? pe.median_price : null, label: "You" };
    if (correlationOpen && correlationData) {
      renderCorrelationChart(correlationData, currentPoint);
    }

    // Shop list
    els.shopList.innerHTML = "";
    (data.shops || []).forEach(function (shop) {
      var isPremium = !!shop.is_premium;
      var yelpUrl = yelpSearchUrl(shop.name, shop.address);
      var li = document.createElement("li");
      li.className = "shop-item";
      li.innerHTML =
        '<div>' +
          '<div class="shop-name ' + (isPremium ? "shop-brand" : "") + '">' +
            '<a href="' + yelpUrl + '" target="_blank" rel="noopener" class="shop-link">' +
              escapeHtml(shop.name) +
            '</a>' +
            (isPremium ? ' <span style="font-size:.65rem">\u2605 PREMIUM</span>' : "") +
          '</div>' +
          '<div style="font-size:.73rem;color:#8b8fa3;margin-top:2px">' + escapeHtml(shop.address) + '</div>' +
        '</div>' +
        '<div class="shop-details">' +
          '<span class="shop-rating">' + (shop.rating || "?") + '\u2605</span>' +
          '<span class="shop-dist">' + shop.distance_miles.toFixed(2) + ' mi</span>' +
        '</div>';
      li.addEventListener("click", function (e) {
        if (e.target.tagName === "A") return;
        map.flyTo([shop.lat, shop.lng], 16, { duration: 0.6 });
      });
      els.shopList.appendChild(li);
    });
    els.shopsHead.textContent = "Nearby Shops (" + data.shop_count + ")";

    // Map markers
    shopMarkers.clearLayers();
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

    (data.shops || []).forEach(function (shop) {
      var isPremium = !!shop.is_premium;
      var yelpUrl = yelpSearchUrl(shop.name, shop.address);
      var marker = L.marker([shop.lat, shop.lng], { icon: bobaIcon(isPremium) });
      marker.bindPopup(
        '<div class="boba-popup">' +
          (isPremium ? '<div class="pop-brand">\u2605 Premium Brand</div>' : "") +
          '<strong><a href="' + yelpUrl + '" target="_blank" rel="noopener" style="color:#1e293b;text-decoration:underline">' + escapeHtml(shop.name) + '</a></strong><br>' +
          '<span class="pop-rating">' + (shop.rating || "?") + '\u2605</span> (' + (shop.review_count || 0) + ' reviews)' +
          '<br><span style="font-size:.78rem;color:#64748b">' + shop.distance_miles.toFixed(2) + ' mi away</span>' +
        '</div>'
      );
      shopMarkers.addLayer(marker);
    });

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
  function renderCorrelationChart(data, current) {
    if (!data || !data.length) return;

    var points = data
      .filter(function (d) { return d.median_price !== null; })
      .map(function (d) {
        return { x: d.boba_index, y: d.median_price, label: d.label };
      });

    var datasets = [{
      label: "Bay Area Neighborhoods",
      data: points,
      backgroundColor: "rgba(96, 165, 250, 0.7)",
      borderColor: "rgba(96, 165, 250, 1)",
      pointRadius: 6,
      pointHoverRadius: 8,
    }];

    if (current && current.median_price !== null) {
      datasets.push({
        label: "Your Search",
        data: [{ x: current.boba_index, y: current.median_price, label: current.label }],
        backgroundColor: "#f0a040",
        borderColor: "#f0a040",
        pointRadius: 10,
        pointStyle: "star",
        pointHoverRadius: 12,
      });
    }

    if (correlationChart) {
      correlationChart.data.datasets = datasets;
      correlationChart.update();
      return;
    }

    correlationChart = new Chart(els.corrCanvas, {
      type: "scatter",
      data: { datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, labels: { color: "#8b8fa3", font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var pt = ctx.raw;
                return pt.label + ": Index " + pt.x.toFixed(2) + " / $" + (pt.y / 1e6).toFixed(1) + "M";
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
            title: { display: true, text: "Median Home Price ($)", color: "#8b8fa3" },
            ticks: {
              color: "#8b8fa3",
              callback: function (v) { return "$" + (v / 1e6).toFixed(1) + "M"; },
            },
            grid: { color: "rgba(45,49,61,0.5)" },
          },
        },
      },
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

  function yelpSearchUrl(name, address) {
    var q = encodeURIComponent(name + " " + address);
    return "https://www.yelp.com/search?find_desc=" + q;
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }
})();
