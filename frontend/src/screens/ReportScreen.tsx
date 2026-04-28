import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  SafeAreaView,
  Modal,
} from 'react-native';

import {
  ChevronLeft,
  CheckCircle2,
  Minus,
} from 'lucide-react-native';

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
  const [showModal, setShowModal] = useState(false);

  const handleSubmit = () => {
    setShowModal(true);
  };

  const handleGoToFeed = () => {
    setShowModal(false);
    navigation.goBack();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Report Submission</Text>
      </View>

      {/* Main Content */}
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Event Type */}
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

        {/* Location */}
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

        {/* Description */}
        <Text style={styles.sectionTitle}>Description</Text>

        <TextInput
          style={[styles.input, styles.textArea]}
          placeholder="Describe what you observed..."
          placeholderTextColor="#9ca3af"
          multiline
          numberOfLines={4}
          value={description}
          onChangeText={setDescription}
          textAlignVertical="top"
        />

        {/* Reliability Card */}
        <View style={styles.reliabilityCard}>
          <View style={styles.reliabilityHeader}>
            <Text style={styles.reliabilityTitle}>
              Preliminary reliability estimate
            </Text>

            <Minus size={20} color="#6b7280" />
          </View>

          <Text style={styles.reliabilitySubtitle}>DistilBERT score</Text>

          <Text style={styles.reliabilityStatus}>
            Score appears after description is entered
          </Text>
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={styles.submitButton}
          onPress={handleSubmit}
        >
          <Text style={styles.submitButtonText}>Submit Report</Text>
        </TouchableOpacity>

        {/* Footer Note */}
        <Text style={styles.aiNote}>
          Reports are scored by{' '}
          <Text style={styles.boldText}>DistilBERT</Text>
          {' '}and may be escalated to{' '}
          <Text style={styles.boldText}>RoBERTa</Text>
          {' '}for verification before appearing on the live feed.
        </Text>
      </ScrollView>

      {/* Success Modal */}
      <Modal
        visible={showModal}
        transparent
        animationType="fade"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalIconWrapper}>
              <CheckCircle2
                size={80}
                color="#ffffff"
                fill="#4475F2"
              />
            </View>

            <Text style={styles.modalTitle}>
              Report submitted successfully
            </Text>

            <TouchableOpacity
              style={styles.modalButton}
              onPress={() => {
                setShowModal(false);
                navigation.navigate('Feed'); 
              }}
            >
              <Text style={styles.modalButtonText}>Go to Feed</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#ffffff',
  },

  header: {
    height: 60,
    backgroundColor: '#FBC02D',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },

  backButton: {
    position: 'absolute',
    left: 15,
  },

  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1f2937',
  },

  container: {
    flex: 1,
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
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
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
    borderWidth: 1,
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
    borderWidth: 1,
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
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },

  reliabilityTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#374151',
  },

  reliabilitySubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 16,
  },

  reliabilityStatus: {
    fontSize: 13,
    color: '#9ca3af',
  },

  submitButton: {
    paddingVertical: 15,
    alignItems: 'center',
    backgroundColor: '#4475F2',
    borderRadius: 30,
  },

  submitButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#ffffff',
  },

  aiNote: {
    marginTop: 15,
    paddingHorizontal: 10,
    textAlign: 'center',
    fontSize: 11,
    lineHeight: 16,
    color: '#6b7280',
  },

  boldText: {
    fontWeight: '700',
    color: '#4b5563',
  },

  modalOverlay: {
    flex: 1,
    padding: 30,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },

  modalContent: {
    width: '100%',
    padding: 30,
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 25,
  },

  modalIconWrapper: {
    marginBottom: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },

  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
    color: '#1f2937',
    marginBottom: 30,
  },

  modalButton: {
    width: '100%',
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: '#4475F2',
    borderRadius: 25,
  },

  modalButtonText: {
    fontWeight: '700',
    color: '#ffffff',
  },
});
