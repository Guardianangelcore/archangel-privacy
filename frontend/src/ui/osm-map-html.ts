/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Shared Leaflet + OpenStreetMap HTML document used by OsmMap (WebView on native, iframe on web).
export type MapPin = { lat: number; lng: number; label: string; color?: string };

export function buildOsmMapHtml(center: { lat: number; lng: number }, pins: MapPin[], accent: string): string {
  const data = JSON.stringify({ center, pins, accent });
  return `<!DOCTYPE html><html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#m{margin:0;padding:0;height:100%;width:100%;background:#0B0B0F}
.pin{width:26px;height:26px;border-radius:13px;border:2px solid #fff;color:#fff;font:700 12px/22px -apple-system,Helvetica,Arial;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.5)}
.me{width:16px;height:16px;border-radius:8px;background:#3B82F6;border:3px solid #fff;box-shadow:0 0 0 6px rgba(59,130,246,.25)}
.leaflet-container{font-family:-apple-system,Helvetica,Arial}
</style></head><body><div id="m"></div>
<script>
(function(){
  var d=${data};
  var map=L.map('m',{zoomControl:false,attributionControl:true}).setView([d.center.lat,d.center.lng],14);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);
  var pts=[[d.center.lat,d.center.lng]];
  L.marker([d.center.lat,d.center.lng],{icon:L.divIcon({className:'',html:'<div class="me"></div>',iconSize:[16,16],iconAnchor:[8,8]})}).addTo(map);
  d.pins.forEach(function(p,i){
    pts.push([p.lat,p.lng]);
    var ic=L.divIcon({className:'',html:'<div class="pin" style="background:'+(p.color||d.accent)+'">'+(i+1)+'</div>',iconSize:[26,26],iconAnchor:[13,13]});
    L.marker([p.lat,p.lng],{icon:ic}).addTo(map).bindPopup('<b>'+(i+1)+'. '+p.label.replace(/</g,'&lt;')+'</b>');
  });
  if(pts.length>1){map.fitBounds(L.latLngBounds(pts).pad(0.15));}
})();
</script></body></html>`;
}
