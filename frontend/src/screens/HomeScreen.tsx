import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  Text,
  KeyboardAvoidingView,
  Platform,
  TouchableWithoutFeedback,
  Keyboard,
} from 'react-native';

import MapView, { PROVIDER_GOOGLE } from 'react-native-maps';

import {
  X,
  ArrowUpDown,
  Info,
  CarFront,
  Search,
  MapPin,
  Circle,
} from 'lucide-react-native';

export default function HomeScreen() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showLegend, setShowLegend] = useState(false);
  const [origin, setOrigin] = useState('Current location');
  const [destination, setDestination] = useState(
    'Pup, Manila Mabini Campus'
  );

  const handleExpand = () => setIsExpanded(true);
  const handleCollapse = () => setIsExpanded(false);

  const clearOrigin = () => setOrigin('');
  const clearDestination = () => setDestination('');

  return (
    <View style={styles.container}>
      {/* 1. Background Map */}
      <MapView
        provider={PROVIDER_GOOGLE}
        style={styles.map}
        initialRegion={{
          latitude: 14.5995,
          longitude: 120.9842,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        }}
      />

      {/* 2. Floating Legend Section (Top Right) */}
      <View style={styles.legendWrapper}>
        {showLegend && (
          <View style={styles.legendCard}>
            <Text style={styles.legendTitle}>Traffic Density</Text>
            <View style={styles.legendItem}>
              <View style={[styles.dot, { backgroundColor: '#ef4444' }]} />
              <Text style={styles.legendText}>Heavy Traffic</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.dot, { backgroundColor: '#f59e0b' }]} />
              <Text style={styles.legendText}>Moderate</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.dot, { backgroundColor: '#10b981' }]} />
              <Text style={styles.legendText}>Light / Clear</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.dot, { backgroundColor: '#3b82f6' }]} />
              <Text style={styles.legendText}>Event Detour</Text>
            </View>
          </View>
        )}
        <TouchableOpacity 
          style={styles.legendButton} 
          onPress={() => setShowLegend(!showLegend)}
          activeOpacity={0.7}
        >
          <Info size={22} color={showLegend ? "#4475F2" : "#6b7280"} />
        </TouchableOpacity>
      </View>

      {/* 3. Main Overlay (Search & Route Planner) */}
      <KeyboardAvoidingView
        style={styles.flexContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : -40}
        pointerEvents="box-none"
      >
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <View style={styles.innerContainer} pointerEvents="box-none">
            
            <View style={[
                styles.overlayWrapper,
                isExpanded && styles.expandedWrapper,
              ]}
            >
              {!isExpanded ? (
                /* Compact Search Bar */
                <TouchableOpacity
                  style={styles.searchBar}
                  onPress={handleExpand}
                >
                  <Search size={20} color="#6b7280" style={styles.searchIcon} />
                  <Text style={styles.placeholderText}>Plan Your Route!</Text>
                </TouchableOpacity>
              ) : (
                /* Expanded Route Planner */
                <View style={styles.routeBox}>
                  <View style={styles.dragHandle} />

                  <View style={styles.inputSection}>
                    <View style={styles.inputRow}>
                      <View style={[styles.pillInputContainer, styles.currentLocationInput]}>
                        <Circle size={10} color="#3b82f6" fill="#3b82f6" style={styles.originIcon} />
                        <TextInput
                          value={origin}
                          onChangeText={setOrigin}
                          style={[styles.actualInput, styles.originInputText]}
                        />
                        <TouchableOpacity onPress={clearOrigin}><X size={18} color="#3b82f6" /></TouchableOpacity>
                      </View>
                    </View>

                    <View style={styles.inputRow}>
                      <View style={[styles.pillInputContainer, styles.activePillInput]}>
                        <MapPin size={18} color="#f59e0b" style={styles.destinationIcon} />
                        <TextInput
                          value={destination}
                          onChangeText={setDestination}
                          style={styles.actualInput}
                          autoFocus
                        />
                        <TouchableOpacity onPress={clearDestination}><X size={18} color="#9ca3af" /></TouchableOpacity>
                      </View>
                    </View>

                    <TouchableOpacity style={styles.swapButton}>
                      <View style={styles.swapIconCircle}>
                        <ArrowUpDown size={20} color="#1f2937" />
                      </View>
                    </TouchableOpacity>
                  </View>

                  <View style={styles.divider} />

                  <View style={styles.summaryRow}>
                    <View style={styles.etaInfo}>
                      <CarFront size={28} color="#1f2937" />
                      <View style={styles.etaTextContainer}>
                        <Text style={styles.timeText}><Text style={styles.highlightText}>20</Text> min</Text>
                        <Text style={styles.subText}>Arrive By 10:01 AM • 10.6 km</Text>
                      </View>
                    </View>
                    <TouchableOpacity style={styles.startButton} onPress={handleCollapse}>
                      <Text style={styles.startButtonText}>Start</Text>
                    </TouchableOpacity>
                  </View>

                  <View style={styles.detailsCard}>
                    <View style={styles.cardHeader}>
                      <View>
                        <Text style={styles.cardTitle}>Via EDSA Southbound</Text>
                        <Text style={styles.cardSubtitle}>Fastest route • event-aware</Text>
                      </View>
                      <View style={styles.badge}><Text style={styles.badgeText}>38 min</Text></View>
                    </View>

                    <View style={styles.metricsRow}>
                      <Text style={styles.metricLabel}>Congestion</Text>
                      <View style={styles.progressBar}>
                        <View style={[styles.progress, styles.congestionProgress]} />
                      </View>
                      <Text style={styles.metricValue}>Moderate</Text>
                    </View>

                    <View style={styles.metricsRow}>
                      <Text style={styles.metricLabel}>Distance</Text>
                      <View style={styles.progressBar}>
                        <View style={[styles.progress, styles.distanceProgress]} />
                      </View>
                      <Text style={styles.metricValue}>14.2 km</Text>
                    </View>

                    <View style={styles.infoBox}>
                      <Info size={14} color="#3b82f6" />
                      <Text style={styles.infoText}>Event detour applied: concert at MOA reroutes via Macapagal Blvd</Text>
                    </View>
                  </View>
                </View>
              )}
            </View>
          </View>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  flexContainer: { flex: 1 },
  innerContainer: { flex: 1, justifyContent: 'flex-end' },
  map: { ...StyleSheet.absoluteFillObject },

  /* Legend Styles */
  legendWrapper: {
    position: 'absolute',
    top: 50,
    right: 20,
    alignItems: 'flex-end',
    zIndex: 100,
  },
  legendButton: {
    width: 48,
    height: 48,
    backgroundColor: '#fff',
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 8,
  },
  legendCard: {
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 16,
    marginBottom: 12,
    width: 140,
    elevation: 8,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 10,
  },
  legendTitle: { fontSize: 13, fontWeight: '700', marginBottom: 10, color: '#1f2937' },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  dot: { width: 10, height: 10, borderRadius: 5, marginRight: 10 },
  legendText: { fontSize: 11, color: '#4b5563', fontWeight: '500' },

  /* Overlay Styles */
  overlayWrapper: { paddingHorizontal: 20, marginBottom: 20 },
  expandedWrapper: {
    marginTop: 'auto',
    marginBottom: 0,
    width: '100%',
    backgroundColor: '#fff',
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    paddingTop: 10,
    paddingBottom: 40,
    paddingHorizontal: 25,
    elevation: 20,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 60,
    paddingHorizontal: 20,
    backgroundColor: '#fff',
    borderRadius: 30,
    elevation: 10,
  },
  searchIcon: { marginRight: 12 },
  placeholderText: { fontSize: 16, fontWeight: '600', color: '#9ca3af' },
  routeBox: { width: '100%' },
  dragHandle: { alignSelf: 'center', width: 40, height: 4, marginBottom: 15, backgroundColor: '#e5e7eb', borderRadius: 2 },
  inputSection: { width: '100%', position: 'relative', gap: 10 },
  inputRow: { width: '92%' },
  pillInputContainer: { flexDirection: 'row', alignItems: 'center', height: 52, paddingHorizontal: 15, backgroundColor: '#f9fafb', borderRadius: 25, borderWidth: 1, borderColor: '#f3f4f6' },
  currentLocationInput: { backgroundColor: '#fff', borderColor: '#3b82f6' },
  activePillInput: { backgroundColor: '#fffcf0', borderColor: '#ffe082' },
  actualInput: { flex: 1, fontSize: 14, fontWeight: '500', color: '#1f2937' },
  originInputText: { color: '#3b82f6' },
  originIcon: { marginRight: 10 },
  destinationIcon: { marginRight: 8 },
  swapButton: { position: 'absolute', right: 0, top: '50%', zIndex: 10, transform: [{ translateY: -25 }, { translateX: 5 }] },
  swapIconCircle: { padding: 8, backgroundColor: '#fff', borderRadius: 20, borderWidth: 1, borderColor: '#f3f4f6', elevation: 4 },
  divider: { height: 1, marginVertical: 15, backgroundColor: '#f3f4f6' },
  summaryRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 15 },
  etaInfo: { flexDirection: 'row', alignItems: 'center' },
  etaTextContainer: { marginLeft: 12 },
  timeText: { fontSize: 26, fontWeight: 'bold' },
  highlightText: { color: '#f59e0b' },
  subText: { fontSize: 12, color: '#6b7280' },
  startButton: { paddingVertical: 14, paddingHorizontal: 35, backgroundColor: '#4475F2', borderRadius: 30 },
  startButtonText: { fontSize: 18, fontWeight: 'bold', color: '#fff' },
  detailsCard: { padding: 15, backgroundColor: '#fff', borderRadius: 20, borderWidth: 1, borderColor: '#f3f4f6' },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 },
  cardTitle: { fontSize: 15, fontWeight: 'bold', color: '#111827' },
  cardSubtitle: { marginTop: 2, fontSize: 12, color: '#9ca3af' },
  badge: { paddingHorizontal: 12, paddingVertical: 4, backgroundColor: '#eff6ff', borderRadius: 12 },
  badgeText: { fontSize: 11, fontWeight: 'bold', color: '#3b82f6' },
  metricsRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  metricLabel: { width: 75, fontSize: 11, color: '#6b7280' },
  progressBar: { flex: 1, height: 6, marginHorizontal: 10, backgroundColor: '#f3f4f6', borderRadius: 3 },
  progress: { height: '100%', borderRadius: 3 },
  congestionProgress: { width: '60%', backgroundColor: '#f59e0b' },
  distanceProgress: { width: '80%', backgroundColor: '#3b82f6' },
  metricValue: { width: 60, textAlign: 'right', fontSize: 11, fontWeight: '600', color: '#4b5563' },
  infoBox: { flexDirection: 'row', alignItems: 'center', marginTop: 10, padding: 12, backgroundColor: '#f0f7ff', borderRadius: 12 },
  infoText: { flex: 1, marginLeft: 8, fontSize: 11, color: '#3b82f6' },
});