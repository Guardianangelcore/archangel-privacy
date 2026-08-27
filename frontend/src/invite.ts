/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. */
// VOICE PRINT INVITE — one-tap share helper that opens the native SMS / Share
// sheet with a pre-composed Slovak message + a deep link back to /voice-signature.
// No backend required: the receiver simply follows the link, signs in with
// their own Google account, and taps record.
import { Share, Platform, Linking } from 'react-native';

function baseUrl(): string {
  const raw = process.env.EXPO_PUBLIC_BACKEND_URL || '';
  // Strip trailing slash so the join is always clean.
  return raw.replace(/\/+$/, '');
}

export function voicePrintInviteMessage(recipientName?: string): { message: string; url: string } {
  const url = `${baseUrl()}/voice-signature`;
  const nm = (recipientName || '').trim();
  const salut = nm ? `Ahoj ${nm}, ` : 'Ahoj, ';
  const message =
    `${salut}prosím, nahraj svoj 5-sekundový hlasový podpis do Guardian Angel — pomôže, ` +
    `aby babička/rodina hneď vedela, kto jej píše.\n\n` +
    `Otvor a ťukni na mikrofón:\n${url}`;
  return { message, url };
}

/**
 * Open the native share sheet. On SMS-friendly Android/iOS this brings up
 * Messages / WhatsApp / Signal etc. On web this falls back to a mailto URL
 * so the sender at least has a copy-paste-ready invite.
 */
export async function inviteFamilyToRecord(recipientName?: string): Promise<boolean> {
  const { message, url } = voicePrintInviteMessage(recipientName);
  try {
    if (Platform.OS === 'web') {
      // navigator.share is not universally available on desktop; fall back to mailto.
      const anyNav: any = typeof navigator !== 'undefined' ? navigator : {};
      if (anyNav.share) {
        await anyNav.share({ title: 'Guardian Angel · Hlasový podpis', text: message, url });
        return true;
      }
      const mailto = `mailto:?subject=${encodeURIComponent('Guardian Angel · Hlasový podpis')}&body=${encodeURIComponent(message)}`;
      await Linking.openURL(mailto);
      return true;
    }
    const res = await Share.share({ message, url, title: 'Guardian Angel · Hlasový podpis' } as any);
    return res.action !== Share.dismissedAction;
  } catch {
    // Never throw from a share; the caller UI must not crash.
    return false;
  }
}

/** Directly open the SMS app pre-filled with the invite (deep-linked to /voice-signature). */
export async function inviteFamilyViaSMS(phone: string, recipientName?: string): Promise<boolean> {
  const { message } = voicePrintInviteMessage(recipientName);
  const separator = Platform.OS === 'ios' ? '&' : '?';
  const url = `sms:${phone.replace(/[^\d+]/g, '')}${separator}body=${encodeURIComponent(message)}`;
  try {
    const can = await Linking.canOpenURL(url);
    if (!can) return false;
    await Linking.openURL(url);
    return true;
  } catch { return false; }
}
