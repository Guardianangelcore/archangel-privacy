/* Copyright © 2026 Guardian Angel. All Rights Reserved. This source code and its logic are the sole property of Guardian Angel. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { API_BASE, getToken } from './api';

export async function shareFile(path: string, filename: string, mimeType: string) {
  const token = await getToken();
  const url = `${API_BASE}/api${path}${path.includes('?') ? '&' : '?'}token=${token}`;
  if (Platform.OS === 'web') {
    window.open(url, '_blank');
    return;
  }
  const dest = `${FileSystem.cacheDirectory}${filename}`;
  const res = await FileSystem.downloadAsync(url, dest);
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(res.uri, { mimeType, dialogTitle: filename });
  }
}

export async function sharePdf(path: string, filename: string) {
  return shareFile(path, filename, 'application/pdf');
}
