import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import apiClient from '../api/client';

const LandingScreen = () => {
  const [status, setStatus] = useState({
    database: 'checking...',
    redis: 'checking...',
  });

  const checkHealth = async () => {
    try {
      const response = await apiClient.get('/api/health');
      setStatus(response.data);
    } catch (error) {
      setStatus({
        database: 'error',
        redis: 'error',
      });
      console.error(error);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Event-Aware Traffic Forecasting</Text>
      <TouchableOpacity
        style={styles.button}
        onPress={checkHealth}
      >
        <Text style={styles.buttonText}>Ping Backend</Text>
      </TouchableOpacity>
      <View style={styles.card}>
        <Text style={styles.statusText}>Database Status: {status.database}</Text>
        <Text style={styles.statusText}>Redis Status: {status.redis}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f3f4f6',
    paddingHorizontal: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 16,
    textAlign: 'center',
    color: '#111827',
  },
  button: {
    backgroundColor: '#2563eb',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 10,
    marginBottom: 16,
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '700',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 10,
    padding: 16,
    width: '100%',
    maxWidth: 420,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  statusText: {
    fontSize: 18,
    color: '#1f2937',
    marginBottom: 6,
  },
});

export default LandingScreen;
