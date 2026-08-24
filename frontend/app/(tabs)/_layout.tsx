/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Platform } from 'react-native';
import { C } from '@/src/theme';
import { useAuth } from '@/src/auth';

export default function TabsLayout() {
  const { user } = useAuth();
  const angel = !!user?.angel_mode;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: angel
          ? { display: 'none' }
          : {
              backgroundColor: C.surface2,
              borderTopColor: C.border,
              borderTopWidth: 1,
              height: Platform.OS === 'ios' ? 84 : 66,
              paddingTop: 8,
            },
        tabBarActiveTintColor: C.brand,
        tabBarInactiveTintColor: C.info,
        tabBarLabelStyle: { fontSize: 10, fontWeight: '700', letterSpacing: 0.5 },
      }}
    >
      <Tabs.Screen name="index" options={{ href: null }} />
      <Tabs.Screen
        name="health"
        options={{
          title: 'HEALTH',
          tabBarIcon: ({ color, size }) => <Ionicons name="heart-outline" size={size} color={color} />,
          tabBarButtonTestID: 'tab-health',
        }}
      />
      <Tabs.Screen
        name="family"
        options={{
          title: 'FAMILY',
          tabBarIcon: ({ color, size }) => <Ionicons name="people-outline" size={size} color={color} />,
          tabBarButtonTestID: 'tab-family',
        }}
      />
      <Tabs.Screen
        name="legacy"
        options={{
          title: 'LEGACY',
          tabBarIcon: ({ color, size }) => <Ionicons name="rose-outline" size={size} color={color} />,
          tabBarButtonTestID: 'tab-legacy',
        }}
      />
      <Tabs.Screen
        name="hunter"
        options={{
          title: 'HUNTER',
          tabBarIcon: ({ color, size }) => <Ionicons name="search-outline" size={size} color={color} />,
          tabBarButtonTestID: 'tab-hunter',
        }}
      />
      <Tabs.Screen name="vault" options={{ href: null }} />
      <Tabs.Screen name="waitlist" options={{ href: null }} />
      <Tabs.Screen name="profile" options={{ href: null }} />
    </Tabs>
  );
}
