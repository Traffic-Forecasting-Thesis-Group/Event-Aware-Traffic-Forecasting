import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Switch,
  Alert,
} from 'react-native';

import {
  ChevronLeft,
  Eye,
  EyeOff,
  Info,
  Lock,
  Bell,
  Monitor,
  ChevronRight,
} from 'lucide-react-native';

export default function PasswordSecurityScreen({ navigation }: any) {
  const [currentPassword, setCurrentPassword] = useState('password123');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [isTwoFactorEnabled, setIsTwoFactorEnabled] = useState(true);
  const [isNotificationsEnabled, setIsNotificationsEnabled] = useState(true);

  const handleUpdate = () => {
    if (!newPassword || !confirmPassword) {
      Alert.alert("Error", "Please fill in all password fields.");
      return;
    }

    if (newPassword !== confirmPassword) {
      Alert.alert(
        "Validation Error",
        "The New Password and Confirm Password do not match."
      );
      return;
    }

    Alert.alert("Success", "Password updated successfully!");
    navigation.goBack();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* HEADER */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
        >
          <ChevronLeft size={24} color="#0084FF" />
        </TouchableOpacity>

        <Text style={styles.headerTitle}>Password & security</Text>
        <View style={{ width: 32 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* INFO */}
        <View style={styles.infoBanner}>
          <Info size={18} color="#0084FF" />
          <Text style={styles.infoText}>
            Password last changed 3 months ago. We recommend updating every 90 days.
          </Text>
        </View>

        {/* PASSWORD SECTION */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>CHANGE PASSWORD</Text>

          <PasswordField
            label="CURRENT PASSWORD"
            value={currentPassword}
            onChangeText={setCurrentPassword}
            secureTextEntry={!showCurrent}
            onToggle={() => setShowCurrent(!showCurrent)}
          />

          <PasswordField
            label="NEW PASSWORD"
            placeholder="Enter new password"
            value={newPassword}
            onChangeText={setNewPassword}
            secureTextEntry={!showNew}
            onToggle={() => setShowNew(!showNew)}
          />

          <PasswordField
            label="CONFIRM NEW PASSWORD"
            placeholder="Re-enter password"
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            secureTextEntry={!showConfirm}
            onToggle={() => setShowConfirm(!showConfirm)} 
            isError={newPassword !== confirmPassword && confirmPassword.length > 0}
          />

          {/* PASSWORD STRENGTH */}
          <View style={styles.strengthContainer}>
            <Text style={styles.strengthLabel}>Password strength</Text>
            <Text style={styles.strengthValue}>Moderate</Text>
          </View>

          <View style={styles.strengthBarContainer}>
            <View style={[styles.strengthBar, { backgroundColor: '#FF4D4D' }]} />
            <View style={[styles.strengthBar, { backgroundColor: '#FFA500', marginHorizontal: 4 }]} />
            <View style={[styles.strengthBar, { backgroundColor: '#E5E7EB' }]} />
            <View style={[styles.strengthBar, { backgroundColor: '#E5E7EB', marginLeft: 4 }]} />
          </View>
        </View>

        {/* SECURITY SETTINGS */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>SECURITY</Text>

          <SecurityToggle
            icon={<Lock size={20} color="#0084FF" />}
            label="Two-factor auth"
            sublabel="Extra layer on sign-in"
            value={isTwoFactorEnabled}
            onValueChange={setIsTwoFactorEnabled}
          />

          <SecurityToggle
            icon={<Bell size={20} color="#0084FF" />}
            label="Login notifications"
            sublabel="Alert on new device sign-ins"
            value={isNotificationsEnabled}
            onValueChange={setIsNotificationsEnabled}
          />

          <TouchableOpacity style={styles.menuItem}>
            <View style={styles.menuLeft}>
              <View style={styles.iconCircle}>
                <Monitor size={20} color="#FFA500" />
              </View>
              <View>
                <Text style={styles.menuLabel}>Active sessions</Text>
                <Text style={styles.menuSublabel}>2 devices signed in</Text>
              </View>
            </View>
            <ChevronRight size={18} color="#D1D5DB" />
          </TouchableOpacity>
        </View>

        {/* BUTTONS */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.updateButton} onPress={handleUpdate}>
            <Text style={styles.updateButtonText}>Update password</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.deleteButton}
            onPress={() => Alert.alert("Confirm", "Delete account?")}
          >
            <Text style={styles.deleteButtonText}>Delete account</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const PasswordField = ({
  label,
  value,
  onChangeText,
  secureTextEntry,
  onToggle,
  placeholder,
  isError,
}: any) => (
  <View style={styles.fieldWrapper}>
    <Text style={[styles.fieldLabel, isError && { color: '#EF4444' }]}>
      {isError ? "PASSWORDS DO NOT MATCH" : label}
    </Text>

    <View style={styles.inputRow}>
      <TextInput
        style={styles.textInput}
        value={value}
        onChangeText={onChangeText}
        secureTextEntry={secureTextEntry}
        placeholder={placeholder}
        placeholderTextColor="#9CA3AF"
      />

      <TouchableOpacity onPress={onToggle}>
        {secureTextEntry ? (
          <EyeOff size={20} color="#D1D5DB" />
        ) : (
          <Eye size={20} color="#D1D5DB" />
        )}
      </TouchableOpacity>
    </View>
  </View>
);

const SecurityToggle = ({ icon, label, sublabel, value, onValueChange }: any) => (
  <View style={styles.menuItem}>
    <View style={styles.menuLeft}>
      <View style={styles.iconCircle}>{icon}</View>
      <View>
        <Text style={styles.menuLabel}>{label}</Text>
        <Text style={styles.menuSublabel}>{sublabel}</Text>
      </View>
    </View>

    <Switch
      value={value}
      onValueChange={onValueChange}
      trackColor={{ false: "#E5E7EB", true: "#0084FF" }}
    />
  </View>
);

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#fff' },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },

  backButton: {
    padding: 8,
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
  },

  headerTitle: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#111827',
  },

  infoBanner: {
    flexDirection: 'row',
    backgroundColor: '#F0F7FF',
    marginHorizontal: 20,
    marginVertical: 15,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },

  infoText: {
    flex: 1,
    fontSize: 13,
    color: '#0084FF',
    marginLeft: 12,
    lineHeight: 18,
  },

  section: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },

  sectionLabel: {
    fontSize: 11,
    fontWeight: 'bold',
    color: '#9CA3AF',
    marginBottom: 10,
    letterSpacing: 0.5,
  },

  fieldWrapper: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },

  fieldLabel: {
    fontSize: 10,
    color: '#9CA3AF',
    marginBottom: 4,
    fontWeight: '600',
  },

  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },

  textInput: {
    flex: 1,
    fontSize: 15,
    color: '#111827',
    paddingVertical: 4,
  },

  strengthContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 15,
    marginBottom: 8,
  },

  strengthLabel: {
    fontSize: 11,
    color: '#9CA3AF',
  },

  strengthValue: {
    fontSize: 11,
    color: '#FFA500',
    fontWeight: 'bold',
  },

  strengthBarContainer: {
    flexDirection: 'row',
    height: 4,
  },

  strengthBar: {
    flex: 1,
    borderRadius: 2,
  },

  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
  },

  menuLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },

  iconCircle: {
    width: 42,
    height: 42,
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },

  menuLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },

  menuSublabel: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 2,
  },

  buttonContainer: {
    paddingHorizontal: 20,
    marginTop: 10,
    paddingBottom: 40,
  },

  updateButton: {
    backgroundColor: '#FFD700',
    padding: 18,
    borderRadius: 14,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#EAB308',
  },

  updateButtonText: {
    color: '#000',
    fontWeight: 'bold',
    fontSize: 15,
  },

  deleteButton: {
    backgroundColor: '#FFF1F2',
    padding: 18,
    borderRadius: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#FFE4E6',
  },

  deleteButtonText: {
    color: '#EF4444',
    fontWeight: 'bold',
    fontSize: 15,
  },
});