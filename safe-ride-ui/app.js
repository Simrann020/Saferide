// ---------- Config ----------
const API_BASE = "https://39lch19vrb.execute-api.us-west-2.amazonaws.com/prod";
const DEFAULT_BUFFER_M = 60;
const MAX_ALTS = 3;

// Test log to verify JavaScript is loading
console.log('🚀 SafeRide JavaScript loaded! API_BASE:', API_BASE);

// store meta for hover explanations
let routesMeta = null;

// ---------- Map ----------
const map = new maplibregl.Map({
  container: 'map',
  style: { version: 8, sources: {}, layers: [] },
  center: [-104.99, 39.74],
  zoom: 12
});
map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

map.on('load', () => {
  addBasemaps();
  setTheme(document.getElementById('theme').value);
  ensureRouteLayers();
});

// ---------- Basemaps / theme ----------
function addBasemaps() {
  const lightTiles = [
    'https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    'https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    'https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    'https://d.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png'
  ];
  const darkTiles = [
    'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    'https://d.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'
  ];
  if (!map.getSource('lightBase')) {
    map.addSource('lightBase', { type:'raster', tiles: lightTiles, tileSize:256, attribution:'© OSM, © CARTO' });
    map.addLayer({ id:'lightBase', type:'raster', source:'lightBase', layout:{ visibility:'none' } });
  }
  if (!map.getSource('darkBase')) {
    map.addSource('darkBase', { type:'raster', tiles: darkTiles, tileSize:256, attribution:'© OSM, © CARTO' });
    map.addLayer({ id:'darkBase', type:'raster', source:'darkBase', layout:{ visibility:'visible' } });
  }
}

function setTheme(theme) {
  const showLight = (theme === 'light') ? 'visible' : 'none';
  const showDark  = (theme === 'light') ? 'none' : 'visible';
  if (map.getLayer('lightBase')) map.setLayoutProperty('lightBase','visibility',showLight);
  if (map.getLayer('darkBase'))  map.setLayoutProperty('darkBase','visibility',showDark);
  ensureRouteLayers();
}
document.getElementById('theme').addEventListener('change', e => setTheme(e.target.value));

// ---------- Animated markers ----------
let startMarker = null, endMarker = null;

function setStartMarker(lngLat) {
  if (startMarker) startMarker.remove();
  const el = document.createElement('div');
  el.className = 'marker start';
  const ring = document.createElement('div'); ring.className = 'ring'; el.appendChild(ring);
  startMarker = new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(lngLat).addTo(map);
}

function setEndMarker(lngLat) {
  if (endMarker) endMarker.remove();
  const el = document.createElement('div');
  el.className = 'marker end';
  const ring = document.createElement('div'); ring.className = 'ring'; el.appendChild(ring);
  endMarker = new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat(lngLat).addTo(map);
}

// ---------- Route layers ----------
function ensureRouteLayers() {
  if (!map.getSource('routes')) {
    map.addSource('routes', { type:'geojson', data:{ type:'FeatureCollection', features:[] } });
  }
}

function createRouteLayersForRoutes(numRoutes, winnerIndex) {
  // Ensure map is ready
  if (!map.getStyle() || !map.getStyle().layers) {
    console.warn('Map style not ready yet');
    return;
  }

  // Remove old route layers
  const layerIds = map.getStyle().layers.map(l => l.id).filter(id => id.startsWith('route-'));
  layerIds.forEach(id => {
    if (map.getLayer(id)) map.removeLayer(id);
  });

  // Color palette: green for winner, then gradient from yellow to red
  const colors = [];
  
  for (let i = 0; i < numRoutes; i++) {
    if (i === winnerIndex) {
      colors[i] = '#10b981'; // Green for best route
    } else {
      const nonWinnerIdx = i < winnerIndex ? i : i - 1;
      const totalNonWinners = numRoutes - 1;
      
      if (totalNonWinners === 1) {
        colors[i] = '#ef4444'; // Red if only one other route
      } else if (totalNonWinners === 2) {
        colors[i] = nonWinnerIdx === 0 ? '#f59e0b' : '#ef4444'; // Yellow and Red
      } else {
        // Gradient from yellow to red for 3+ routes
        const ratio = nonWinnerIdx / (totalNonWinners - 1);
        const hue = 60 - (ratio * 60); // 60 (yellow) to 0 (red)
        colors[i] = `hsl(${hue}, 100%, 50%)`;
      }
    }

    // Create a layer for each route
    const layerId = `route-${i}`;
    if (!map.getLayer(layerId)) {
      map.addLayer({
        id: layerId,
        type: 'line',
        source: 'routes',
        paint: {
          'line-color': colors[i],
          'line-width': 5,
          'line-opacity': 0.95
        },
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        },
        filter: ['==', ['get', 'index'], i]
      });
    }
  }

  return colors;
}

function setRoutesGeoJSON(fc) {
  map.getSource('routes').setData(fc);
  const coords = [];
  for (const f of fc.features || []) {
    if (Array.isArray(f.geometry?.coordinates)) coords.push(...f.geometry.coordinates);
  }
  if (coords.length) {
    const b = coords.reduce((bb, p) => bb.extend(p), new maplibregl.LngLatBounds(coords[0], coords[0]));
    if (startLL) b.extend(startLL);
    if (endLL) b.extend(endLL);
    map.fitBounds(b, { padding: 100, duration: 800 });
  }
}

// ---------- Geocoding + autocomplete ----------
async function geocode(q) {
  const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(q)}`;
  const res = await fetch(url, { headers:{ 'Accept-Language':'en' } });
  if (!res.ok) throw new Error(`geocode HTTP ${res.status}`);
  const arr = await res.json();
  if (!arr?.length) throw new Error(`No results for "${q}"`);
  return [parseFloat(arr[0].lon), parseFloat(arr[0].lat)];
}

async function suggest(q, limit=5) {
  const url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=${limit}&q=${encodeURIComponent(q)}`;
  const res = await fetch(url, { headers:{ 'Accept-Language':'en' } });
  if (!res.ok) return [];
  const arr = await res.json();
  return arr.map(r => ({
    name: r.display_name,
    lon: parseFloat(r.lon),
    lat: parseFloat(r.lat),
    icon: r.icon || null,
    category: r.class || ''
  }));
}

function debounce(fn, ms=250) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(()=>fn(...args), ms); };
}

function makeAutocomplete(inputEl, listEl, onPick) {
  let items = [], active = -1;

  async function run(q) {
    if (q.trim().length < 3) { listEl.style.display = 'none'; return; }
    const s = await suggest(q);
    items = s; active = -1;
    render();
  }

  function render() {
    listEl.innerHTML = '';
    if (!items.length) { listEl.style.display = 'none'; return; }
    items.forEach((it, i) => {
      const div = document.createElement('div');
      div.className = 'ac-item' + (i===active ? ' active' : '');
      const emoji = document.createElement('div');
      emoji.className = 'ac-emoji';
      emoji.textContent = it.category === 'railway' ? '🚉' :
                          it.category === 'amenity' ? '📍' :
                          it.category === 'highway' ? '🛣️' : '📌';
      const name = document.createElement('div'); name.textContent = it.name;
      div.appendChild(emoji); div.appendChild(name);
      div.addEventListener('mousedown', e => { e.preventDefault(); pick(i); });
      listEl.appendChild(div);
    });
    const foot = document.createElement('div');
    foot.className = 'ac-footer';
    foot.textContent = 'Results by OpenStreetMap Nominatim';
    listEl.appendChild(foot);
    listEl.style.display = 'block';
  }

  function pick(i) {
    const it = items[i]; if (!it) return;
    inputEl.value = it.name;
    listEl.style.display = 'none';
    onPick([it.lon, it.lat], it.name);
  }

  inputEl.addEventListener('input', debounce(e => run(e.target.value)));
  inputEl.addEventListener('focus', () => { if (items.length) listEl.style.display = 'block'; });
  inputEl.addEventListener('blur',  () => setTimeout(()=> listEl.style.display='none', 150));

  inputEl.addEventListener('keydown', e => {
    if (!items.length) return;
    if (e.key === 'ArrowDown') { active = (active+1) % items.length; render(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { active = (active-1+items.length)%items.length; render(); e.preventDefault(); }
    else if (e.key === 'Enter')   { if (active>=0) { pick(active); e.preventDefault(); } }
  });
}

// ---------- DOM helpers ----------
const $ = id => document.getElementById(id);
const statusEl = $('status');

let startLL=null, endLL=null;

makeAutocomplete($('from'), $('ac-from'), (lngLat, name) => {
  startLL = lngLat; setStartMarker(lngLat); statusEl.textContent = `From: ${name}`;
});
makeAutocomplete($('to'), $('ac-to'), (lngLat, name) => {
  endLL = lngLat; setEndMarker(lngLat); statusEl.textContent = `To: ${name}`;
});

// ---------- Hover popup over routes ----------
const hoverPopup = new maplibregl.Popup({
  closeButton: false,
  closeOnClick: false
});

map.on('mousemove', (e) => {
  if (!routesMeta) return;

  const style = map.getStyle();
  if (!style || !style.layers) return;

  const layerIds = style.layers.map(l => l.id).filter(id => id.startsWith('route-'));
  const features = map.queryRenderedFeatures(e.point, { layers: layerIds });

  if (!features.length) {
    map.getCanvas().style.cursor = '';
    hoverPopup.remove();
    // Show all routes again when not hovering
    layerIds.forEach(id => {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, 'visibility', 'visible');
      }
    });
    return;
  }

  const f = features[0];
  const idx = Number(f.properties.index);
  const isWinner = f.properties.is_winner === true || f.properties.is_winner === 'true';

  // Hide all routes except the hovered one
  layerIds.forEach(id => {
    const layerIdx = parseInt(id.split('-')[1]);
    if (map.getLayer(id)) {
      map.setLayoutProperty(id, 'visibility', layerIdx === idx ? 'visible' : 'none');
    }
  });

  const meta = routesMeta.routes.find(r => r.index === idx);
  const winnerMeta = routesMeta.routes.find(r => r.index === routesMeta.winnerIndex);
  if (!meta || !winnerMeta) return;

  const crashDiff = meta.crashes - winnerMeta.crashes;
  const lenDiff = meta.length_km - winnerMeta.length_km;

  let label;
  if (isWinner) {
    label = '✓ Safest Route';
  } else {
    label = 'Alternative Route';
  }

  let explanation = '';
  if (!isWinner) {
    const crashText = crashDiff > 0
      ? `<span style="color:#ef4444;">+${crashDiff} more crashes</span>`
      : `<span style="color:#10b981;">${Math.abs(crashDiff)} fewer crashes</span>`;
    const lenText = lenDiff > 0
      ? `<span style="color:#f59e0b;">+${lenDiff.toFixed(1)} km longer</span>`
      : `<span style="color:#10b981;">${Math.abs(lenDiff).toFixed(1)} km shorter</span>`;

    explanation = `<br/><small>${crashText} | ${lenText}</small>`;
  }

  const html = `
    <div style="font-weight: 600; margin-bottom: 4px;">Route ${idx + 1} – ${label}</div>
    <div style="font-size: 13px; color: #666;">
      📏 ${meta.length_km.toFixed(2)} km | ⚠️ ${meta.crashes} crashes
    </div>
    ${explanation}
  `;

  hoverPopup
    .setLngLat(e.lngLat)
    .setHTML(html)
    .addTo(map);

  map.getCanvas().style.cursor = 'pointer';
});

// ---------- Button click / API call ----------
$('go').addEventListener('click', async () => {
  const mode = 'driving'; // Default to driving mode
  const fromQ = $('from').value.trim();
  const toQ   = $('to').value.trim();
  if (!fromQ || !toQ) { statusEl.textContent = 'Please enter both places.'; return; }

  $('go').disabled = true;
  try {
    if (!startLL) startLL = await geocode(fromQ);
    if (!endLL)   endLL   = await geocode(toQ);

    setStartMarker(startLL);
    setEndMarker(endLL);

    if (startLL && endLL) {
      const bounds = new maplibregl.LngLatBounds(startLL, endLL);
      map.fitBounds(bounds, { padding: 100, duration: 800 });
    }

    statusEl.textContent = 'Requesting routes…';
    const body = {
      start: startLL, end: endLL,
      buffer_m: DEFAULT_BUFFER_M,
      max_alternatives: MAX_ALTS,
      mode, use_fixture: false
    };
    console.log('🔍 Making API request to:', `${API_BASE}/routes/rank`);
    console.log('📤 Request body:', body);
    
    const res = await fetch(`${API_BASE}/routes/rank`, {
      method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(`API HTTP ${res.status}`);
    const data = await res.json();
    
    console.log('📥 API response:', data);
    console.log('🛣️ Routes from API:', data.routes_ranked);

    const routes = data.routes_ranked || [];
    const sorted = [...routes].sort((a,b)=> (a.crashes-b.crashes) || (a.length_km-b.length_km));
    const winnerIndex = (data.winner ?? (sorted[0]?.index ?? null));

    const riskIndex = {}; let rRank = 0;
    for (const r of sorted) {
      if (r.index===winnerIndex) continue;
      riskIndex[r.index] = rRank<2 ? rRank : 2;
      rRank++;
    }

    // store for hover popup
    routesMeta = { routes, winnerIndex, riskIndex };

    const features = routes.map(r => ({
      type:'Feature',
      geometry:{ type:'LineString', coordinates: wktToCoords(r.wkt) },
      properties:{
        index:r.index, crashes:r.crashes, length_km:r.length_km,
        is_winner:r.index===winnerIndex,
        risk_rank:(r.index===winnerIndex) ? -1 : (riskIndex[r.index] ?? 2)
      }
    }));
    setRoutesGeoJSON({ type:'FeatureCollection', features });

    // Create individual colored layers for each route
    createRouteLayersForRoutes(routes.length, winnerIndex);

    displayRouteInfo(routes, winnerIndex, riskIndex);

    statusEl.textContent = `Loaded ${routes.length} route(s). Winner: Route ${winnerIndex + 1}`;
  } catch (e) {
    console.error(e);
    statusEl.textContent = `Error: ${e.message || e}`;
  } finally {
    $('go').disabled = false;
  }
});

function wktToCoords(wkt) {
  try {
    const inner = wkt.replace(/^LINESTRING\s*\(/i, '').replace(/\)\s*$/, '');
    return inner.split(',').map(p => p.trim().split(/\s+/).map(Number));
  } catch { return []; }
}

function displayRouteInfo(routes, winnerIndex, riskIndex) {
  const infoEl = $('routes-info');
  const containerEl = $('routes-container');
  
  if (!routes.length) {
    containerEl.style.display = 'none';
    return;
  }
  
  infoEl.innerHTML = '';
  containerEl.style.display = 'block';

  const sorted = [...routes].sort((a,b) => (a.crashes - b.crashes) || (a.length_km - b.length_km));
  const winnerRoute = routes.find(r => r.index === winnerIndex);

  // Create "All Routes" card first
  const allCard = document.createElement('div');
  allCard.className = 'route-card winner all-routes-card';
  allCard.innerHTML = `
    <div class="route-header">
      <span class="route-title">📍 All Routes</span>
      <span class="route-badge winner">👁️ View All</span>
    </div>
    <div class="route-stats">
      <div class="route-stat">
        📏 <strong>${routes.length}</strong> routes available
      </div>
      <div class="route-stat">
        ⚠️ <strong>${Math.min(...routes.map(r => r.crashes))}-${Math.max(...routes.map(r => r.crashes))}</strong> crashes
      </div>
    </div>
  `;

  allCard.addEventListener('click', () => {
    // Show all routes
    const style = map.getStyle();
    if (style && style.layers) {
      const allLayerIds = style.layers.map(l => l.id).filter(id => id.startsWith('route-'));
      allLayerIds.forEach(id => {
        map.setLayoutProperty(id, 'visibility', 'visible');
      });
    }
    
    // Update card styling
    document.querySelectorAll('.route-card').forEach(c => {
      c.style.borderWidth = '1.5px';
      c.style.opacity = '1';
    });
    allCard.style.borderWidth = '3px';
    allCard.style.opacity = '1';
  });

  infoEl.appendChild(allCard);

  // Create individual route cards
  sorted.forEach((route) => {
    const isWinner = route.index === winnerIndex;
    const riskClass = isWinner ? 'winner' : (riskIndex[route.index] === 0 ? 'medium' : 'high');
    const routeNum = route.index + 1;
    
    let badgeText = '';
    let suggestion = '';
    
    if (isWinner) {
      badgeText = '🏆 Best Route';
      suggestion = 'Safest option with fewest crashes';
    } else if (riskIndex[route.index] === 0) {
      badgeText = '⚠️ Average Risk';
      suggestion = 'Moderate safety profile';
    } else {
      badgeText = '🚨 Higher Risk';
      suggestion = 'More crashes on this route';
    }

    // Calculate comparisons with winner
    const crashDiff = route.crashes - winnerRoute.crashes;
    const lenDiff = route.length_km - winnerRoute.length_km;
    
    let comparisonHTML = '';
    if (!isWinner) {
      const crashBadge = crashDiff > 0 ? 'worse' : 'better';
      const lenBadge = lenDiff > 0 ? 'worse' : 'better';
      
      const crashLabel = crashDiff > 0 
        ? `+${crashDiff} more crash${crashDiff !== 1 ? 'es' : ''}`
        : `${Math.abs(crashDiff)} fewer crash${Math.abs(crashDiff) !== 1 ? 'es' : ''}`;
      
      const lenLabel = lenDiff > 0 
        ? `+${lenDiff.toFixed(1)} km longer`
        : `${Math.abs(lenDiff).toFixed(1)} km shorter`;
      
      comparisonHTML = `
        <div class="route-comparison">
          <div class="route-comparison-item">
            <span class="comparison-badge ${crashBadge}">${crashDiff > 0 ? '✗' : '✓'}</span>
            <span class="comparison-text"><strong>Safety:</strong> ${crashLabel} vs safest route</span>
          </div>
          <div class="route-comparison-item">
            <span class="comparison-badge ${lenBadge}">${lenDiff > 0 ? '✗' : '✓'}</span>
            <span class="comparison-text"><strong>Distance:</strong> ${lenLabel}</span>
          </div>
        </div>
      `;
    } else {
      comparisonHTML = `
        <div class="route-comparison">
          <div class="route-comparison-item">
            <span class="comparison-badge better">✓</span>
            <span class="comparison-text">Lowest crash count on record</span>
          </div>
          <div class="route-comparison-item">
            <span class="comparison-badge better">✓</span>
            <span class="comparison-text">Optimal balance of safety & distance</span>
          </div>
        </div>
      `;
    }

    const card = document.createElement('div');
    card.className = `route-card ${riskClass}`;
    card.innerHTML = `
      <div class="route-header">
        <span class="route-title">Route ${routeNum}</span>
        <span class="route-badge ${riskClass}">${badgeText}</span>
      </div>
      <div class="route-stats">
        <div class="route-stat">
          📏 <strong>${route.length_km.toFixed(2)}</strong> km
        </div>
        <div class="route-stat">
          ⚠️ <strong>${route.crashes}</strong> crashes
        </div>
      </div>
      ${comparisonHTML}
    `;

    // Click to show only this route
    card.addEventListener('click', () => {
      const style = map.getStyle();
      if (style && style.layers) {
        const allLayerIds = style.layers.map(l => l.id).filter(id => id.startsWith('route-'));
        allLayerIds.forEach(id => {
          const layerIdx = parseInt(id.split('-')[1]);
          map.setLayoutProperty(id, 'visibility', layerIdx === route.index ? 'visible' : 'none');
        });
      }
      
      // Update card styling
      document.querySelectorAll('.route-card').forEach(c => {
        c.style.borderWidth = '1.5px';
        c.style.opacity = '0.7';
      });
      card.style.borderWidth = '3px';
      card.style.opacity = '1';
    });

    card.addEventListener('mouseenter', () => {
      // Hide all routes except hover
      const style = map.getStyle();
      if (style && style.layers) {
        const allLayerIds = style.layers.map(l => l.id).filter(id => id.startsWith('route-'));
        allLayerIds.forEach(id => {
          map.setLayoutProperty(id, 'visibility', 'none');
        });
        // Show only this route
        map.setLayoutProperty(`route-${route.index}`, 'visibility', 'visible');
      }
      // Highlight the card
      card.style.transform = 'scale(1.02)';
    });
    
    card.addEventListener('mouseleave', () => {
      // Restore previous state
      const style = map.getStyle();
      if (style && style.layers) {
        const allLayerIds = style.layers.map(l => l.id).filter(id => id.startsWith('route-'));
        
        // Check if any route card is currently selected (has thick border)
        const selectedCard = document.querySelector('.route-card[style*="border-width: 3px"]');
        
        if (selectedCard && !selectedCard.classList.contains('all-routes-card')) {
          // A specific route is selected, show only that one
          const selectedIdx = parseInt(selectedCard.querySelector('.route-title').textContent.match(/\d+/)[0]) - 1;
          allLayerIds.forEach(id => {
            const layerIdx = parseInt(id.split('-')[1]);
            map.setLayoutProperty(id, 'visibility', layerIdx === selectedIdx ? 'visible' : 'none');
          });
        } else if (selectedCard && selectedCard.classList.contains('all-routes-card')) {
          // All routes card is selected, show all
          allLayerIds.forEach(id => {
            map.setLayoutProperty(id, 'visibility', 'visible');
          });
        } else {
          // No selection, show all
          allLayerIds.forEach(id => {
            map.setLayoutProperty(id, 'visibility', 'visible');
          });
        }
      }
      // Reset highlight
      card.style.transform = 'scale(1)';
    });

    infoEl.appendChild(card);
  });
}

// demo defaults
$('from').value = 'Union Station Denver';
$('to').value = 'Jefferson Park Denver';
map.once('load', () => {
  // Use real location names, but override with test coordinates that have crash data
  startLL = [-105.0, 39.7];
  endLL = [-104.99, 39.75];
  $('go').click();
});
