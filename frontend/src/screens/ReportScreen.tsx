import React, { useState } from 'react';
import { useIsFocused } from '@react-navigation/native';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  SafeAreaView,
  StatusBar,
  Alert,
} from 'react-native';

import { Minus } from 'lucide-react-native';

const EVENT_TYPES = [
  'Accident',
  'Road closure',
  'Flooding',
  'Public event',
  'Road works',
  'Other',
];

export default function ReportScreen({ navigation }: any) {
  const [selectedType, setSelectedType] = useState('Accident');
  const [description, setDescription] = useState('');
  const isFocused = useIsFocused();

  const handleSubmit = () => {
    Alert.alert(
      "Success",
      "Report submitted successfully",
      [
        {
          text: "OK",
          onPress: () => navigation.navigate('Feed'),
        },
      ]
    );
  };

  return (
    <View style={styles.mainContainer}>

      {/* STATUS BAR */}
      {isFocused && (
        <StatusBar
          barStyle="dark-content"
          backgroundColor="#FBC02D"
        />
      )}

      {/* HEADER AREA */}
      <View style={styles.topYellowBoundary}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>
              Report Submission
            </Text>
          </View>
        </SafeAreaView>
      </View>

      {/* FORM */}
      <SafeAreaView style={styles.formContentArea}>
        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
        >

          {/* EVENT TYPE */}
          <Text style={styles.sectionTitle}>Event Type</Text>

          <View style={styles.grid}>
            {EVENT_TYPES.map((type) => {
              const isSelected = selectedType === type;

              return (
                <TouchableOpacity
                  key={type}
                  style={[
                    styles.gridItem,
                    isSelected && styles.selectedGridItem,
                  ]}
                  onPress={() => setSelectedType(type)}
                >
                  <Text
                    style={[
                      styles.gridText,
                      isSelected && styles.selectedGridText,
                    ]}
                  >
                    {type}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {/* LOCATION */}
          <Text style={styles.sectionTitle}>Location</Text>

          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.input}
              placeholder="Enter location"
              placeholderTextColor="#9ca3af"
            />

            <TouchableOpacity>
              <Text style={styles.useGpsText}>Use GPS</Text>
            </TouchableOpacity>
          </View>

          {/* DESCRIPTION */}
          <Text style={styles.sectionTitle}>Description</Text>

          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="Describe what you observed..."
            placeholderTextColor="#9ca3af"
            multiline
            value={description}
            onChangeText={setDescription}
          />

          {/* RELIABILITY */}
          <View style={styles.reliabilityCard}>
            <View style={styles.reliabilityHeader}>
              <Text style={styles.reliabilityTitle}>
                Preliminary reliability estimate
              </Text>
              <Minus size={20} color="#6b7280" />
            </View>

            <Text style={styles.reliabilitySubtitle}>
              DistilBERT score
            </Text>

            <Text style={styles.reliabilityStatus}>
              {description.length > 0
                ? "Analyzing text..."
                : "Score appears after description is entered"}
            </Text>
          </View>

          {/* SUBMIT BUTTON */}
          <TouchableOpacity
            style={styles.submitButton}
            onPress={handleSubmit}
          >
            <Text style={styles.submitButtonText}>
              Submit Report
            </Text>
          </TouchableOpacity>

          {/* FOOTER */}
          <Text style={styles.aiNote}>
            Reports are scored by{' '}
            <Text style={styles.boldText}>DistilBERT</Text>
            {' '}and may be escalated to{' '}
            <Text style={styles.boldText}>RoBERTa</Text>
            {' '}for verification.
          </Text>

        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  mainContainer: {
    flex: 1,
    backgroundColor: '#fff',
  },

  topYellowBoundary: {
    backgroundColor: '#FBC02D',
  },

  safeArea: {
    backgroundColor: '#FBC02D',
  },

  header: {
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
  },

  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1f2937',
  },

  formContentArea: {
    flex: 1,
    backgroundColor: '#fff',
  },

  content: {
    padding: 20,
  },

  sectionTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 10,
    textTransform: 'uppercase',
  },

  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 25,
  },

  gridItem: {
    width: '48%',
    padding: 12,
    marginBottom: 10,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    alignItems: 'center',
  },

  selectedGridItem: {
    backgroundColor: '#eff6ff',
    borderColor: '#3b82f6',
  },

  gridText: {
    fontSize: 13,
    color: '#6b7280',
  },

  selectedGridText: {
    fontWeight: '700',
    color: '#3b82f6',
  },

  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    marginBottom: 25,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    borderRadius: 8,
  },

  input: {
    flex: 1,
    height: 45,
    color: '#1f2937',
  },

  useGpsText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#3b82f6',
  },

  textArea: {
    height: 100,
    padding: 12,
    marginBottom: 30,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    borderRadius: 8,
  },

  reliabilityCard: {
    padding: 15,
    marginBottom: 30,
    backgroundColor: '#f9fafb',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 12,
  },

  reliabilityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },

  reliabilityTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#374151',
  },

  reliabilitySubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 10,
  },

  reliabilityStatus: {
    fontSize: 13,
    color: '#9ca3af',
  },

  submitButton: {
    paddingVertical: 15,
    borderRadius: 30,
    backgroundColor: '#4475F2',
    alignItems: 'center',
  },

  submitButtonText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 16,
  },

  aiNote: {
    marginTop: 15,
    textAlign: 'center',
    fontSize: 11,
    color: '#6b7280',
    lineHeight: 16,
  },

  boldText: {
    fontWeight: '700',
  },
});