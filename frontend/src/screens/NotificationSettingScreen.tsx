import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ScrollView,
  Switch,
  Platform,
  Modal,
} from 'react-native';

import DateTimePicker from '@react-native-community/datetimepicker';

import {
  ChevronLeft,
  AlertTriangle,
  CloudRain,
  Construction,
  Heart,
  Flame,
  Bell,
  Mail,
  Moon,
} from 'lucide-react-native';

export default function NotificationSettingsScreen({ navigation }: any) {
  // Main notification toggles
  const [allowNotifications, setAllowNotifications] = useState(true);
  const [accidents, setAccidents] = useState(true);
  const [weather, setWeather] = useState(true);
  const [roadWorks, setRoadWorks] = useState(true);
  const [community, setCommunity] = useState(false);
  const [emergencies, setEmergencies] = useState(true);

  // Delivery settings
  const [pushNotifications, setPushNotifications] = useState(true);
  const [emailDigest, setEmailDigest] = useState(false);
  const [frequency, setFrequency] = useState('Hourly');

  // Quiet hours
  const [quietHours, setQuietHours] = useState(true);
  const [startTime, setStartTime] = useState(new Date(2026, 4, 2, 22, 0));
  const [endTime, setEndTime] = useState(new Date(2026, 4, 2, 7, 0));
  const [showPicker, setShowPicker] = useState(false);
  const [pickerMode, setPickerMode] = useState<'start' | 'end'>('start');
  const [allowCritical, setAllowCritical] = useState(true);

  // HANDLERS
  const onTimeChange = (event: any, selectedDate?: Date) => {
    if (Platform.OS === 'android' && event.type === 'set') {
      setShowPicker(false);
    }

    if (selectedDate) {
      if (pickerMode === 'start') {
        setStartTime(selectedDate);
      } else {
        setEndTime(selectedDate);
      }
    }
  };

  const formatTime = (date: Date) =>
    date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });

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

        <Text style={styles.headerTitle}>Notification settings</Text>

        <View style={{ width: 32 }} />
      </View>

      {/* CONTENT */}
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.masterSection}>
          <View>
            <Text style={styles.masterTitle}>Allow notifications</Text>
            <Text style={styles.subtext}>
              Master switch for all alerts
            </Text>
          </View>

          <Switch
            value={allowNotifications}
            onValueChange={setAllowNotifications}
            trackColor={{ false: '#E5E7EB', true: '#0084FF' }}
          />
        </View>

        {/* ALERT TYPES */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>ALERT TYPES</Text>
        </View>

        <NotificationItem
          icon={<AlertTriangle size={20} color="#EF4444" />}
          bg="#FEF2F2"
          label="Accidents & incidents"
          sublabel="High-priority safety alerts"
          value={accidents}
          onValueChange={setAccidents}
        />

        <NotificationItem
          icon={<CloudRain size={20} color="#0084FF" />}
          bg="#EFF6FF"
          label="Flooding & weather"
          sublabel="Flood advisories, storm alerts"
          value={weather}
          onValueChange={setWeather}
        />

        <NotificationItem
          icon={<Construction size={20} color="#6B7280" />}
          bg="#F9FAFB"
          label="Road works & closures"
          sublabel="Disruptions on your routes"
          value={roadWorks}
          onValueChange={setRoadWorks}
        />

        <NotificationItem
          icon={<Heart size={20} color="#A855F7" />}
          bg="#FAF5FF"
          label="Community events"
          sublabel="Sales, protests, local events"
          value={community}
          onValueChange={setCommunity}
        />

        <NotificationItem
          icon={<Flame size={20} color="#F59E0B" />}
          bg="#FFFBEB"
          label="Fire & emergencies"
          sublabel="Critical emergency broadcasts"
          value={emergencies}
          onValueChange={setEmergencies}
        />

        {/* DELIVERY */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>DELIVERY</Text>
        </View>

        <NotificationItem
          icon={<Bell size={20} color="#0084FF" />}
          bg="#EFF6FF"
          label="Push notifications"
          sublabel="Instant alerts on device"
          value={pushNotifications}
          onValueChange={setPushNotifications}
        />

        <NotificationItem
          icon={<Mail size={20} color="#10B981" />}
          bg="#ECFDF5"
          label="Email digest"
          sublabel="Daily summary of area activity"
          value={emailDigest}
          onValueChange={setEmailDigest}
        />

        {/* FREQUENCY */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>FREQUENCY</Text>
        </View>

        <View style={styles.frequencyPadding}>
          <Text style={styles.frequencyDesc}>
            How often to receive non-critical alerts
          </Text>

          <View style={styles.segmentContainer}>
            {['Real-time', 'Hourly', 'Daily'].map((option) => (
              <TouchableOpacity
                key={option}
                style={[
                  styles.segmentButton,
                  frequency === option && styles.segmentActive,
                ]}
                onPress={() => setFrequency(option)}
              >
                <Text
                  style={[
                    styles.segmentText,
                    frequency === option &&
                      styles.segmentTextActive,
                  ]}
                >
                  {option}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* QUIET HOURS */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>QUIET HOURS</Text>
        </View>

        <NotificationItem
          icon={<Moon size={20} color="#6B7280" />}
          bg="#F9FAFB"
          label="Enable quiet hours"
          sublabel="Mute alerts during set times"
          value={quietHours}
          onValueChange={setQuietHours}
        />

        {quietHours && (
          <View style={styles.quietHoursContent}>
            <View style={styles.timeRow}>
              {/* START TIME */}
              <View style={styles.timeBox}>
                <Text style={styles.timeLabel}>FROM</Text>

                <TouchableOpacity
                  style={styles.timePickerButton}
                  onPress={() => {
                    setPickerMode('start');
                    setShowPicker(true);
                  }}
                >
                  <Text style={styles.timeValue}>
                    {formatTime(startTime)}
                  </Text>
                </TouchableOpacity>
              </View>

              <View style={styles.timeDivider} />

              {/* END TIME */}
              <View style={styles.timeBox}>
                <Text style={styles.timeLabel}>TO</Text>

                <TouchableOpacity
                  style={styles.timePickerButton}
                  onPress={() => {
                    setPickerMode('end');
                    setShowPicker(true);
                  }}
                >
                  <Text style={styles.timeValue}>
                    {formatTime(endTime)}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* EXCEPTION */}
            <View style={styles.exceptionRow}>
              <View>
                <Text style={styles.exceptionTitle}>
                  Allow critical alerts
                </Text>
                <Text style={styles.subtext}>
                  Overrides quiet hours for emergencies
                </Text>
              </View>

              <Switch
                value={allowCritical}
                onValueChange={setAllowCritical}
                trackColor={{
                  false: '#E5E7EB',
                  true: '#0084FF',
                }}
              />
            </View>
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>

      {/* MODAL */}
      <Modal
        transparent
        visible={showPicker}
        animationType="slide"
        onRequestClose={() => setShowPicker(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowPicker(false)}
        >
          <View
            style={styles.bottomSheet}
            onStartShouldSetResponder={() => true}
          >
            {/* HEADER */}
            <View style={styles.sheetHeader}>
              <TouchableOpacity onPress={() => setShowPicker(false)}>
                <Text style={styles.cancelText}>Cancel</Text>
              </TouchableOpacity>

              <Text style={styles.sheetTitle}>
                {pickerMode === 'start'
                  ? 'Start Time'
                  : 'End Time'}
              </Text>

              <TouchableOpacity onPress={() => setShowPicker(false)}>
                <Text style={styles.doneText}>Done</Text>
              </TouchableOpacity>
            </View>

            {/* PICKER */}
            <View style={styles.pickerWrapper}>
              <DateTimePicker
                value={
                  pickerMode === 'start'
                    ? startTime
                    : endTime
                }
                mode="time"
                is24Hour={false}
                display="spinner"
                onChange={onTimeChange}
                textColor="#111827"
                style={styles.picker}
              />
            </View>
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
}

const NotificationItem = ({
  icon,
  bg,
  label,
  sublabel,
  value,
  onValueChange,
}: any) => (
  <View style={styles.itemRow}>
    <View style={styles.itemLeft}>
      <View style={[styles.iconBox, { backgroundColor: bg }]}>
        {icon}
      </View>

      <View style={styles.textContainer}>
        <Text style={styles.itemLabel}>{label}</Text>
        <Text style={styles.subtext}>{sublabel}</Text>
      </View>
    </View>

    <Switch
      value={value}
      onValueChange={onValueChange}
      trackColor={{ false: '#E5E7EB', true: '#0084FF' }}
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

  masterSection: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },

  masterTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#111827',
  },

  sectionHeader: {
    backgroundColor: '#F9FAFB',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },

  sectionTitle: {
    fontSize: 11,
    fontWeight: 'bold',
    color: '#9CA3AF',
    letterSpacing: 0.5,
  },

  itemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },

  itemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },

  iconBox: {
    width: 40,
    height: 40,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },

  textContainer: { marginLeft: 12 },

  itemLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },

  subtext: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 2,
  },

  frequencyPadding: { padding: 20 },

  frequencyDesc: {
    fontSize: 12,
    color: '#9CA3AF',
    marginBottom: 12,
  },

  segmentContainer: {
    flexDirection: 'row',
    backgroundColor: '#F9FAFB',
    borderRadius: 10,
    padding: 4,
    borderWidth: 1,
    borderColor: '#F3F4F6',
  },

  segmentButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },

  segmentActive: { backgroundColor: '#0084FF' },

  segmentText: {
    fontSize: 13,
    color: '#6B7280',
    fontWeight: '500',
  },

  segmentTextActive: {
    color: '#fff',
    fontWeight: 'bold',
  },

  quietHoursContent: { backgroundColor: '#fff' },

  timeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    justifyContent: 'space-between',
  },

  timeBox: { flex: 1 },

  timeLabel: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#9CA3AF',
    marginBottom: 8,
  },

  timePickerButton: {
    backgroundColor: '#F3F4F6',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
    alignItems: 'center',
  },

  timeValue: {
    fontSize: 15,
    fontWeight: '600',
    color: '#111827',
  },

  timeDivider: {
    width: 15,
    height: 2,
    backgroundColor: '#E5E7EB',
    marginHorizontal: 15,
    marginTop: 20,
  },

  exceptionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },

  exceptionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
  },

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },

  bottomSheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    minHeight: 300,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 5,
  },

  sheetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },

  sheetTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
  },

  cancelText: {
    color: '#6B7280',
    fontSize: 16,
  },

  doneText: {
    color: '#0084FF',
    fontWeight: 'bold',
    fontSize: 16,
  },

  pickerWrapper: {
    height: 220,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },

  picker: {
    width: '100%',
    height: '100%',
  },
});