/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// OsmMap (web preview) — react-native-webview has no web implementation, so the same
// Leaflet document is rendered in a sandboxed iframe. Native builds use OsmMap.tsx.
import React, { useMemo } from 'react';
import { View, StyleSheet } from 'react-native';
import { buildOsmMapHtml, MapPin } from './osm-map-html';

export default function OsmMap({ center, pins, height = 240, accent = '#B8860B', testID }: {
  center: { lat: number; lng: number }; pins: MapPin[]; height?: number; accent?: string; testID?: string;
}) {
  const html = useMemo(() => buildOsmMapHtml(center, pins, accent), [center, pins, accent]);
  return (
    <View testID={testID} style={[st.box, { height }]}>
      {React.createElement('iframe', {
        srcDoc: html,
        sandbox: 'allow-scripts allow-same-origin',
        style: { border: 0, width: '100%', height: '100%', background: '#0B0B0F' },
        title: 'map',
      })}
    </View>
  );
}

const st = StyleSheet.create({
  box: { borderRadius: 16, overflow: 'hidden', borderWidth: 1, borderColor: '#2A2A33', backgroundColor: '#0B0B0F' },
});
