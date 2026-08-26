/* Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved. This source code and its logic are the sole property of the Foundation. Unauthorized duplication, modification, or distribution is strictly prohibited. */
import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Platform } from 'react-native';
import { C } from '@/src/theme';
import { tap } from '@/src/ui/glass';
import { useAuth } from '@/src/auth';
import { t, Lang } from '@/src/i18n';

export default function TabsLayout() {
  const { user } = useAuth();
  const angel = !!user?.angel_mode;
  const lang: Lang = (user?.language as Lang) || 'sk';

  return (
    <Tabs
      screenListeners={{ tabPress: () => tap('light') }}
      screenOptions={{
        headerShown: false,
        tabBarStyle: angel
          ? { display: 'none' }
          : {
              backgroundColor: 'rgba(10,10,15,0.96)',
              borderTopColor: 'rgba(212,175,55,0.28)',
              borderTopWidth: 1,
              height: Platform.OS === 'ios' ? 88 : 70,
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
          title: t('pillar_health', lang).toUpperCase(),
          tabBarIcon: ({ color, size, focused }) => <Ionicons name={focused ? 'heart' : 'heart-outline'} size={size} color={color} />,
          tabBarButtonTestID: 'tab-health',
        }}
      />
      <Tabs.Screen
        name="family"
        options={{
          title: t('pillar_family', lang).toUpperCase(),
          tabBarIcon: ({ color, size, focused }) => <Ionicons name={focused ? 'people' : 'people-outline'} size={size} color={color} />,
          tabBarButtonTestID: 'tab-family',
        }}
      />
      <Tabs.Screen
        name="legacy"
        options={{
          title: 'MAJETOK',
          tabBarIcon: ({ color, size, focused }) => <Ionicons name={focused ? 'wallet' : 'wallet-outline'} size={size} color={color} />,
          tabBarButtonTestID: 'tab-legacy',
        }}
      />
      <Tabs.Screen
        name="hunter"
        options={{
          title: t('tab_hunter', lang).toUpperCase(),
          tabBarIcon: ({ color, size, focused }) => <Ionicons name={focused ? 'search' : 'search-outline'} size={size} color={color} />,
          tabBarButtonTestID: 'tab-hunter',
        }}
      />
      <Tabs.Screen name="vault" options={{ href: null }} />
      <Tabs.Screen name="waitlist" options={{ href: null }} />
      <Tabs.Screen name="profile" options={{ href: null }} />
    </Tabs>
  );
}
