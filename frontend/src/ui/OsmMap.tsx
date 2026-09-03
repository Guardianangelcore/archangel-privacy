/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// OsmMap — native: Leaflet/OpenStreetMap inside a WebView (keyless, no Google Maps SDK needed).
import React, { useMemo } from 'react';
import { View, StyleSheet } from 'react-native';
import { WebView } from 'react-native-webview';
import { buildOsmMapHtml, MapPin } from './osm-map-html';

export default function OsmMap({ center, pins, height = 240, accent = '#B8860B', testID }: {
  center: { lat: number; lng: number }; pins: MapPin[]; height?: number; accent?: string; testID?: string;
}) {
  const html = useMemo(() => buildOsmMapHtml(center, pins, accent), [center, pins, accent]);
  return (
    <View testID={testID} style={[st.box, { height }]}>
      <WebView
        originWhitelist={['*']}
        source={{ html }}
        style={st.web}
        javaScriptEnabled
        domStorageEnabled
        scrollEnabled={false}
        setBuiltInZoomControls={false}
      />
    </View>
  );
}

const st = StyleSheet.create({
  box: { borderRadius: 16, overflow: 'hidden', borderWidth: 1, borderColor: '#2A2A33', backgroundColor: '#0B0B0F' },
  web: { flex: 1, backgroundColor: '#0B0B0F' },
});
