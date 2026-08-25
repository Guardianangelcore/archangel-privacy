/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
// Zero-Typing Fields — pressable inputs that open native-style wheel/date/time bottom sheets.
// Policy: NO manual typing for numbers, dates or times anywhere in the app.
import React, { useState } from 'react';
import { Text, Pressable, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { C } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { WheelSheet, DateSheet, TimeSheet } from '@/src/ui/sheets';

type BaseProps = {
  value: string;
  onChange: (v: string) => void;
  title: string;
  placeholder?: string;
  testID?: string;
  style?: StyleProp<ViewStyle>;
};

/** Numeric field — opens a premium wheel-picker (no keyboard). */
export function WheelField({ value, onChange, title, min, max, step = 1, unit = '', decimals = 0, placeholder, testID, style }: BaseProps & {
  min: number; max: number; step?: number; unit?: string; decimals?: number;
}) {
  const [open, setOpen] = useState(false);
  const display = value !== '' && value != null ? `${value}${unit ? ` ${unit}` : ''}` : '';
  return (
    <>
      <Pressable testID={testID} onPress={() => { tap('light'); setOpen(true); }} style={[style, fs.row]}>
        <Text style={[fs.val, !display && fs.ph]} numberOfLines={1}>{display || placeholder || title}</Text>
        <Ionicons name="chevron-expand" size={16} color={C.brand} />
      </Pressable>
      <WheelSheet visible={open} onClose={() => setOpen(false)} title={title} min={min} max={max} step={step}
        unit={unit} decimals={decimals}
        initial={value ? parseFloat(String(value).replace(',', '.')) : undefined}
        onSelect={v => onChange(decimals > 0 ? v.toFixed(decimals) : String(v))}
        testID={testID ? `${testID}-sheet` : undefined} />
    </>
  );
}

/** Date field — opens the Slovak calendar bottom sheet (no typing). */
export function DateField({ value, onChange, title, placeholder, testID, style }: BaseProps) {
  const [open, setOpen] = useState(false);
  const disp = value && /^\d{4}-\d{2}-\d{2}/.test(value)
    ? `${parseInt(value.slice(8, 10), 10)}. ${parseInt(value.slice(5, 7), 10)}. ${value.slice(0, 4)}`
    : '';
  return (
    <>
      <Pressable testID={testID} onPress={() => { tap('light'); setOpen(true); }} style={[style, fs.row]}>
        <Text style={[fs.val, !disp && fs.ph]} numberOfLines={1}>{disp || placeholder || title}</Text>
        <Ionicons name="calendar-outline" size={16} color={C.brand} />
      </Pressable>
      <DateSheet visible={open} onClose={() => setOpen(false)} title={title} initial={value || undefined}
        onSelect={onChange} testID={testID ? `${testID}-sheet` : undefined} />
    </>
  );
}

/** Time field — opens a two-wheel HH:MM picker (no typing). */
export function TimeField({ value, onChange, title, placeholder, testID, style }: BaseProps) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Pressable testID={testID} onPress={() => { tap('light'); setOpen(true); }} style={[style, fs.row]}>
        <Text style={[fs.val, !value && fs.ph]} numberOfLines={1}>{value || placeholder || title}</Text>
        <Ionicons name="time-outline" size={16} color={C.brand} />
      </Pressable>
      <TimeSheet visible={open} onClose={() => setOpen(false)} title={title} initial={value || undefined}
        onSelect={onChange} testID={testID ? `${testID}-sheet` : undefined} />
    </>
  );
}

const fs = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, minHeight: 48 },
  val: { color: C.fg, fontSize: 15, fontWeight: '700', flex: 1 },
  ph: { color: '#8A8A93', fontWeight: '500' },
});
