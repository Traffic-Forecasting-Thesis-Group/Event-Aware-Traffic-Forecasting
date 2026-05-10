import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import {
  Home,
  Megaphone,
  Newspaper,
  Bell,
  User,
} from 'lucide-react-native';

import SplashScreen from '../screens/SplashScreen';
import LandingScreen from '../screens/LandingScreen';
import SignInScreen from '../screens/SignInScreen';
import ForgotPasswordScreen from '../screens/ForgotPasswordScreen';
import VerificationCodeScreen from '../screens/VerificationCodeScreen';
import ResetPasswordScreen from '../screens/ResetPasswodScreen';
import SignUpScreen from '../screens/SignUpScreen';
import OnboardScreen from '../screens/OnboardScreen';
import SetLocationScreen from '../screens/SetLocationScreen';
import SearchLocationScreen from '../screens/SearchLocationScreen';
import HomeScreen from '../screens/HomeScreen';
import ReportScreen from '../screens/ReportScreen';
import FeedScreen from '../screens/FeedScreen';
import AlertScreen from '../screens/AlertScreen';
import ProfileScreen from '../screens/ProfileScreen';
import EditProfileScreen from '../screens/EditProfileScreen'; 
import PasswordScreen from '../screens/PasswordScreen';
import NotificationSettingsScreen from '../screens/NotificationSettingScreen';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

// Bottom Tab Navigator 
function MainTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          height: 70,
          paddingBottom: 10,
        },
        tabBarActiveTintColor: '#2563eb',
        tabBarInactiveTintColor: '#6b7280',
      }}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <Home color={color} size={24} />
          ),
        }}
      />

      <Tab.Screen
        name="Report"
        component={ReportScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <Megaphone color={color} size={24} />
          ),
        }}
      />

      <Tab.Screen
        name="Feed"
        component={FeedScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <Newspaper color={color} size={24} />
          ),
        }}
      />

      <Tab.Screen
        name="Alert"
        component={AlertScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <Bell color={color} size={24} />
          ),
        }}
      />

      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          tabBarIcon: ({ color }) => (
            <User color={color} size={24} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

// Stack Navigator for the app
export default function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="Splash"
      screenOptions={{
        headerShown: false,
        animation: 'fade',
      }}
    >

      <Stack.Screen 
        name="Splash" 
        component={SplashScreen} 
      />

      <Stack.Screen
        name="Landing"
        component={LandingScreen}
      />

      <Stack.Screen
        name="SignInScreen"
        component={SignInScreen}
        options={{
          animation: 'none'
        }}
      />

      <Stack.Screen
        name="ForgotPasswordScreen"
        component={ForgotPasswordScreen}
        options={{
          animation: 'none'
        }}
      />

      <Stack.Screen
        name="VerificationCodeScreen"
        component={VerificationCodeScreen}
        options={{
          animation: 'none'
        }}
      />

      <Stack.Screen
        name="ResetPasswordScreen"
        component={ResetPasswordScreen}
        options={{
          animation: 'none'
        }}
      />

      <Stack.Screen
        name="SignUpScreen"
        component={SignUpScreen}
        options={{
          animation: 'none'
        }}
      />

      <Stack.Screen 
        name="Onboarding" 
        component={OnboardScreen} 
      />
      
      <Stack.Screen 
        name="SetLocation" 
        component={SetLocationScreen} 
      />

      <Stack.Screen 
        name="SearchLocation" 
        component={SearchLocationScreen} 
      />

      <Stack.Screen
        name="Main"
        component={MainTabNavigator}
      />

      <Stack.Screen
        name="EditProfileScreen"
        component={EditProfileScreen}
        options={{
          headerShown: false, 
          animation: 'slide_from_right'
        }}
      />

      <Stack.Screen
        name="PasswordScreen"
        component={PasswordScreen}
        options={{
          headerShown: false, 
          animation: 'slide_from_right'
        }}
      />

      <Stack.Screen
        name="NotificationSettingsScreen"
        component={NotificationSettingsScreen}
        options={{
          headerShown: false,
          animation: 'slide_from_right'
        }}
      />
    </Stack.Navigator>
  );
}