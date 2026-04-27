import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import apiClient from '../api/client';

interface Props {
  navigation: any;
}

export default function LandingScreen({ navigation }: Props) {
  const [status, setStatus] = useState({
    database: 'checking...',
    redis: 'checking...',
  });

  const checkHealth = async () => {
    try {
      const response = await apiClient.get('/api/health');
      setStatus(response.data);
    } catch (error) {
      setStatus({ database: 'error', redis: 'error' });
      console.error(error);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Event-Aware Traffic Forecasting</Text>
      
      <TouchableOpacity style={styles.button} onPress={checkHealth}>
        <Text style={styles.buttonText}>Ping Backend</Text>
      </TouchableOpacity>

      <View style={styles.card}>
        <Text style={styles.statusText}>Database: {status.database}</Text>
        <Text style={styles.statusText}>Redis: {status.redis}</Text>
      </View>

      <TouchableOpacity 
        style={[styles.button, styles.dashboardButton]} 
        onPress={() => navigation.navigate("Main")}
      >
        <Text style={styles.buttonText}>Go to Dashboard</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f3f4f6',
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 20,
    color: '#111827',
  },
  button: {
    backgroundColor: '#2563eb',
    padding: 15,
    borderRadius: 10,
    width: '100%',
    alignItems: 'center',
  },
  dashboardButton: {
    backgroundColor: '#10b981',
    marginTop: 20,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 20,
    width: '100%',
    marginTop: 20,
    elevation: 3,
  },
  statusText: {
    fontSize: 16,
    marginBottom: 5,
  },
});