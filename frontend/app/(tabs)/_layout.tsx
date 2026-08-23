import React from 'react';
import { Tabs } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Platform } from 'react-native';
import { C } from '@/src/theme';
import { useAuth } from '@/src/auth';
import { t } from '@/src/i18n';

export default function TabsLayout() {
  const { user } = useAuth();
  const angel = !!user?.angel_mode;
  const lang = (user?.language as any) || 'sk';

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: angel
          ? { display: 'none' }
          : {
              backgroundColor: C.inverse,
              borderTopColor: C.inverse,
              borderTopWidth: 0,
              height: Platform.OS === 'ios' ? 84 : 64,
              paddingTop: 6,
            },
        tabBarActiveTintColor: C.onInverse,
        tabBarInactiveTintColor: '#8a8a8a',
        tabBarLabelStyle: { fontSize: 11, fontWeight: '800', letterSpacing: 1 },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: t('home', lang).toUpperCase(),
          tabBarIcon: ({ color, size }) => <Ionicons name="grid-outline" size={size} color={color} />,
          tabBarButtonTestID: 'tab-home',
        }}
      />
      <Tabs.Screen
        name="vault"
        options={{
          title: t('vault', lang).toUpperCase(),
          tabBarIcon: ({ color, size }) => <Ionicons name="lock-closed-outline" size={size} color={color} />,
          tabBarButtonTestID: 'tab-vault',
        }}
      />
      <Tabs.Screen
        name="waitlist"
        options={{
          title: t('waitlist', lang).toUpperCase(),
          tabBarIcon: ({ color, size }) => <Ionicons name="calendar-outline" size={size} color={color} />,
          tabBarButtonTestID: 'tab-waitlist',
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: t('profile', lang).toUpperCase(),
          tabBarIcon: ({ color, size }) => <Ionicons name="person-outline" size={size} color={color} />,
          tabBarButtonTestID: 'tab-profile',
        }}
      />
    </Tabs>
  );
}
