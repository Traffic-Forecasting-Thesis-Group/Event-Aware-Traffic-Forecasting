import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

export default function AlertScreen({ navigation }: any) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Traffic Alerts</Text>
      <Text style={styles.subtitle}>This is for traffic alert.</Text>

      <TouchableOpacity 
        style={styles.backButton} 
        onPress={() => navigation.goBack()}
      >
        <Text style={styles.buttonText}>Go Back</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#ffffff', padding: 20 },
  title: { fontSize: 26, fontWeight: 'bold', color: '#1f2937', marginBottom: 10 },
  subtitle: { fontSize: 16, color: '#6b7280', textAlign: 'center', marginBottom: 30 },
  backButton: { backgroundColor: '#6b7280', padding: 12, borderRadius: 8, width: '80%', alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: '600' },
});