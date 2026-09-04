/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// USER TYPE — who is holding the phone. Drives the Senior (65+) large-print mode and the
// clinician-only medical detail. Persisted in the user profile (PUT /me/user-type).
import { useAuth } from './auth';

export type UserType = 'adult' | 'senior' | 'clinician' | 'responder' | 'child';

export const USER_TYPES: { id: UserType; icon: string; label: string; sub: string }[] = [
  { id: 'adult',     icon: 'person',        label: 'Adult',            sub: 'Full experience' },
  { id: 'senior',    icon: 'glasses',       label: 'Senior (65+)',     sub: 'Large print · big tiles · only the essentials' },
  { id: 'clinician', icon: 'medkit',        label: 'Clinician',        sub: 'Medical detail, dosages, interactions' },
  { id: 'responder', icon: 'flash',         label: 'First responder',  sub: 'Tactical medic, triage, crisis protocols' },
  { id: 'child',     icon: 'happy',         label: 'Child',            sub: 'Simple, safe, guardian-supervised' },
];

export function useUserType() {
  const { user } = useAuth() as any;
  const type: UserType = (user?.user_type as UserType) || 'adult';
  const senior = type === 'senior';
  return {
    type,
    senior,
    clinician: type === 'clinician' || type === 'responder',
    /** Senior = 3× headline scale, ~1.6× body scale (readable without glasses, still fits a phone). */
    fs: (base: number, headline = false) => (senior ? Math.round(base * (headline ? 3 : 1.6)) : base),
  };
}
