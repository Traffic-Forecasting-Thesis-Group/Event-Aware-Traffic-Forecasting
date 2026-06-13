import React, { useState, useEffect, useRef } from 'react';
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
  StatusBar,
  ActivityIndicator,
  Alert,
  FlatList,
} from 'react-native';

import MapView, { PROVIDER_GOOGLE, Marker, Polyline } from 'react-native-maps';
import * as Location from 'expo-location'; 
import { X, ArrowUpDown, Info, CarFront, Search, MapPin, Circle, LocateFixed, XCircle } from 'lucide-react-native';
import { fetchDynamicRouteEstimation, RouteDataResponse } from '../api/locationService';
import { fetchGeocodeAddress } from '../api/geocode'; 

export default function HomeScreen({ navigation }: any) {
  const mapRef = useRef<MapView | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [origin, setOrigin] = useState('Current location');
  const [destination, setDestination] = useState('');
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [routeData, setRouteData] = useState<RouteDataResponse | null>(null);

  const [showActivePath, setShowActivePath] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeInputNode, setActiveInputNode] = useState<'origin' | 'destination' | null>(null);
  const [loadingSearch, setLoadingSearch] = useState(false);

  const [originCoords, setOriginCoords] = useState<{ latitude: number; longitude: number } | null>(null);
  const [destCoords, setDestCoords] = useState<{ latitude: number; longitude: number } | null>(null);

  const [mapRegion, setMapRegion] = useState({
    latitude: 14.5995,
    longitude: 120.9842,
    latitudeDelta: 0.0622,
    longitudeDelta: 0.0421,
  });

  useEffect(() => {
    getCurrentDeviceLocation();
  }, []);

  useEffect(() => {
    const currentQueryText = activeInputNode === 'origin' ? origin : destination;

    if (!currentQueryText.trim() || currentQueryText === 'Current location') {
      setSearchResults([]);
      setShowSuggestions(false);
      return;
    }

    const delayDebounceTimer = setTimeout(async () => {
      setLoadingSearch(true);
      try {
        const results = await fetchGeocodeAddress(currentQueryText);
        setSearchResults(results);
        setShowSuggestions(results.length > 0 && activeInputNode !== null);
      } catch (error) {
        console.error('Live search dynamic layer error:', error);
      } finally {
        setLoadingSearch(false);
      }
    }, 500);

    return () => clearTimeout(delayDebounceTimer);
  }, [origin, destination, activeInputNode]);

  const getCurrentDeviceLocation = async () => {
    try {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Location permission is required to access your current location.');
        return;
      }

      let currentDeviceLocation = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      
      const currentCoords = {
        latitude: currentDeviceLocation.coords.latitude,
        longitude: currentDeviceLocation.coords.longitude,
      };

      setOrigin('Current location');
      setOriginCoords(currentCoords);
      setShowActivePath(false);
      
      setMapRegion((prev) => ({
        ...prev,
        latitude: currentCoords.latitude,
        longitude: currentCoords.longitude,
        latitudeDelta: 0.02,
        longitudeDelta: 0.02,
      }));

      if (destination.trim()) {
        triggerDynamicRouting('Current location', destination, currentCoords);
      }
    } catch (error) {
      Alert.alert('Error', 'Cannot get your current location.');
    }
  };

  const handleInputChange = (text: string, targetField: 'origin' | 'destination') => {
    setShowActivePath(false);
    if (targetField === 'origin') {
      setOrigin(text);
    } else {
      setDestination(text);
    }
    setActiveInputNode(targetField);
    if (!text.trim()) {
      setSearchResults([]);
      setShowSuggestions(false);
      setRouteData(null);
    }
  };

  const handleSelectLocation = async (item: any) => {
    setShowActivePath(false);
    
    const preciseCoordinates = {
      latitude: parseFloat(item.latitude || item.lat),
      longitude: parseFloat(item.longitude || item.lon || item.lng)
    };

    if (isNaN(preciseCoordinates.latitude) || isNaN(preciseCoordinates.longitude)) {
      console.warn("Invalid precise metadata format. Falling back to native geocoder.");
      const resolvedFallback = await geocodeAddressString(item.formattedAddress, activeInputNode === 'origin');
      if (resolvedFallback) {
        preciseCoordinates.latitude = resolvedFallback.latitude;
        preciseCoordinates.longitude = resolvedFallback.longitude;
      }
    }

    if (activeInputNode === 'origin') {
      setOrigin(item.formattedAddress);
      setOriginCoords(preciseCoordinates);
      triggerDynamicRouting(item.formattedAddress, destination, preciseCoordinates, destCoords || undefined);
    } else {
      setDestination(item.formattedAddress);
      setDestCoords(preciseCoordinates);
      triggerDynamicRouting(origin, item.formattedAddress, originCoords || undefined, preciseCoordinates);
    }
    setShowSuggestions(false);
    setActiveInputNode(null);
    Keyboard.dismiss();
  };

  const handleExpand = () => {
    setIsExpanded(true);
    if (originCoords) {
      triggerDynamicRouting(origin, destination, originCoords, destCoords || undefined);
    } else {
      getCurrentDeviceLocation();
    }
  };
  
  const handleCollapse = () => {
    setIsExpanded(false);
    setShowSuggestions(false);
    setActiveInputNode(null);
  };

  const handleStartNavigation = () => {
    if (originCoords && destCoords) {
      setShowActivePath(true);
      setIsExpanded(false);
      
      mapRef.current?.fitToCoordinates([originCoords, destCoords], {
        edgePadding: { top: 80, right: 50, bottom: 80, left: 50 },
        animated: true,
      });
    } else {
      Alert.alert('Missing Location', 'Ensure both origin and destination are set with valid locations before starting navigation.');
    }
  };

  const geocodeAddressString = async (addressString: string, isOriginNode: boolean, forcedCoords?: any) => {
    const textClean = addressString.toLowerCase().trim();
    if (!textClean) return null;

    if (textClean === 'current location') {
      if (forcedCoords) return forcedCoords;
      if (isOriginNode && originCoords) return originCoords;
      let currentDeviceLocation = await Location.getCurrentPositionAsync({});
      return {
        latitude: currentDeviceLocation.coords.latitude,
        longitude: currentDeviceLocation.coords.longitude,
      };
    }

    if (forcedCoords) return forcedCoords;

    try {
      let geocodeResults = await Location.geocodeAsync(addressString);
      if (geocodeResults.length > 0) {
        return {
          latitude: geocodeResults[0].latitude,
          longitude: geocodeResults[0].longitude,
        };
      }
    } catch (e) {
      console.warn("Native geocoding tracking node failed.", e);
    }

    return null;
  };

  const triggerDynamicRouting = async (startPoint: string, endPoint: string, forcedOriginCoords?: any, forcedDestCoords?: any) => {
    if (!startPoint.trim() || !endPoint.trim()) {
      setRouteData(null);
      return;
    }

    setLoadingRoute(true);
    try {
      const resolvedOrigin = await geocodeAddressString(startPoint, true, forcedOriginCoords);
      const resolvedDest = await geocodeAddressString(endPoint, false, forcedDestCoords);

      if (resolvedOrigin && resolvedDest) {
        setOriginCoords(resolvedOrigin);
        setDestCoords(resolvedDest);

        const evaluationResult = await fetchDynamicRouteEstimation(startPoint, endPoint);
        setRouteData(evaluationResult);

        setMapRegion({
          latitude: (resolvedOrigin.latitude + resolvedDest.latitude) / 2,
          longitude: (resolvedOrigin.longitude + resolvedDest.longitude) / 2,
          latitudeDelta: Math.max(Math.abs(resolvedOrigin.latitude - resolvedDest.latitude) * 1.6, 0.05),
          longitudeDelta: Math.max(Math.abs(resolvedOrigin.longitude - resolvedDest.longitude) * 1.6, 0.05),
        });
      }
    } catch (error) {
      console.error("Routing integration error:", error);
      setRouteData(null);
    } finally {
      setLoadingRoute(false);
    }
  };

  const handleSwapAddresses = () => {
    setShowActivePath(false);
    const temporaryValue = origin;
    const tempCoords = originCoords;
    
    setOrigin(destination);
    setOriginCoords(destCoords);
    
    setDestination(temporaryValue);
    setDestCoords(tempCoords);
    
    triggerDynamicRouting(destination, temporaryValue, destCoords || undefined, tempCoords || undefined);
  };

  const getCalculatedArrivalTime = (additionalMinutes: number) => {
    const currentDeviceDate = new Date();
    currentDeviceDate.setMinutes(currentDeviceDate.getMinutes() + additionalMinutes);
    return currentDeviceDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent={true} />

      <MapView
        ref={mapRef}
        provider={PROVIDER_GOOGLE}
        style={styles.map}
        region={mapRegion}
        onPress={() => {
          Keyboard.dismiss();
          if (isExpanded) handleCollapse();
        }}
      >
        {origin.trim() && originCoords && (
          <Marker coordinate={originCoords} title="Origin Start Location" pinColor="#4476F1" />
        )}
        {destination.trim() && destCoords && (
          <Marker coordinate={destCoords} title="Target Destination Location" pinColor="#F1B545" />
        )}

        {showActivePath && originCoords && destCoords && (
          <Polyline
            coordinates={[originCoords, destCoords]}
            strokeColor="#4475F2"
            strokeWidth={5}
          />
        )}
      </MapView>

      <View style={styles.legendCard}>
        <View style={styles.legendItem}><View style={[styles.dot, { backgroundColor: '#ef4444' }]} /><Text style={styles.legendText}>Heavy</Text></View>
        <View style={styles.legendItem}><View style={[styles.dot, { backgroundColor: '#f59e0b' }]} /><Text style={styles.legendText}>Moderate</Text></View>
        <View style={styles.legendItem}><View style={[styles.dot, { backgroundColor: '#10b981' }]} /><Text style={styles.legendText}>Low / Clear</Text></View>
      </View>

      <KeyboardAvoidingView
        style={styles.flexContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : -40}
        pointerEvents="box-none"
      >
        <TouchableWithoutFeedback onPress={() => { Keyboard.dismiss(); setShowSuggestions(false); }}>
          <View style={styles.innerContainer} pointerEvents="box-none">
            <View style={[styles.overlayWrapper, isExpanded && styles.expandedWrapper]}>
              
              {!isExpanded ? (
                <TouchableOpacity style={styles.searchBar} onPress={handleExpand}>
                  <Search size={20} color="#6b7280" style={styles.searchIcon} />
                  <Text style={styles.placeholderText}>Plan Your Route!</Text>
                </TouchableOpacity>
              ) : (
                <View style={styles.routeBox}>
                  <View style={styles.dragHandle} />
                  
                  <View style={styles.inputSection}>
                    <View style={styles.inputRow}>
                      <View style={[styles.pillInputContainer, activeInputNode === 'origin' ? styles.activeOriginSearchBar : styles.currentLocationInput]}>
                        <Circle size={10} color="#3b82f6" fill="#3b82f6" style={styles.originIcon} />
                        <TextInput
                          value={origin}
                          onChangeText={(text) => handleInputChange(text, 'origin')}
                          onFocus={() => origin.trim() && handleInputChange(origin, 'origin')}
                          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                          onSubmitEditing={() => triggerDynamicRouting(origin, destination, originCoords || undefined, destCoords || undefined)}
                          placeholder="Enter start location..."
                          style={[styles.actualInput, styles.originInputText]}
                          returnKeyType="search"
                        />
                        <TouchableOpacity style={styles.actionButton} onPress={getCurrentDeviceLocation}>
                          <LocateFixed size={18} color="#3b82f6" />
                        </TouchableOpacity>
                        <TouchableOpacity style={styles.actionButton} onPress={() => { setOrigin(''); setRouteData(null); setOriginCoords(null); setSearchResults([]); setShowSuggestions(false); setShowActivePath(false); }}>
                          <XCircle size={18} color="#9ca3af" />
                        </TouchableOpacity>
                      </View>
                    </View>

                    <View style={styles.inputRow}>
                      <View style={[styles.pillInputContainer, activeInputNode === 'destination' ? styles.activeDestSearchBar : styles.activePillInput]}>
                        <MapPin size={18} color="#f59e0b" style={styles.destinationIcon} />
                        <TextInput
                          value={destination}
                          onChangeText={(text) => handleInputChange(text, 'destination')}
                          onFocus={() => destination.trim() && handleInputChange(destination, 'destination')}
                          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                          onSubmitEditing={() => triggerDynamicRouting(origin, destination, originCoords || undefined, destCoords || undefined)}
                          placeholder="Where to in Metro Manila?"
                          style={[styles.actualInput, styles.destinationInputText]}
                          returnKeyType="search"
                        />
                        <TouchableOpacity onPress={() => { setDestination(''); setRouteData(null); setDestCoords(null); setSearchResults([]); setShowSuggestions(false); setShowActivePath(false); }}>
                          <XCircle size={18} color="#9ca3af" />
                        </TouchableOpacity>
                      </View>
                    </View>

                    <TouchableOpacity style={styles.swapButton} onPress={handleSwapAddresses}>
                      <View style={styles.swapIconCircle}><ArrowUpDown size={20} color="#1f2937" /></View>
                    </TouchableOpacity>

                    {showSuggestions && (
                      <View style={[
                        styles.suggestionsContainer, 
                        activeInputNode === 'destination' ? { top: 114 } : { top: 52 }
                      ]}>
                        {loadingSearch ? (
                          <ActivityIndicator style={{ padding: 15 }} size="small" color="#4475F2" />
                        ) : (
                          <FlatList
                            data={searchResults}
                            keyExtractor={(item) => item.id || item.formattedAddress}
                            keyboardShouldPersistTaps="handled"
                            renderItem={({ item }) => {
                              const addressParts = item.formattedAddress.split(', ');
                              const mainTitle = addressParts[0]; 
                              const cleanSubtitle = addressParts
                                .slice(1)
                                .filter((part: string) => 
                                  !part.toLowerCase().includes('philippines') && 
                                  !/^\d{4}$/.test(part)
                                )
                                .join(', ');

                              return (
                                <TouchableOpacity style={styles.resultItem} onPress={() => handleSelectLocation(item)}>
                                  <View style={styles.iconCircle}>
                                    <MapPin color="#4475F2" size={18} />
                                  </View>
                                  <View style={styles.textContainer}>
                                    <Text style={styles.locationName} numberOfLines={1}>{mainTitle}</Text>
                                    <Text style={styles.locationAddress} numberOfLines={2}>
                                      {cleanSubtitle || item.formattedAddress}
                                    </Text>
                                  </View>
                                </TouchableOpacity>
                              );
                            }}
                          />
                        )}
                      </View>
                    )}
                  </View>

                  <View style={styles.divider} />

                  {loadingRoute ? (
                    <View style={styles.loadingWrapper}>
                      <ActivityIndicator size="large" color="#4475F2" />
                      <Text style={styles.loadingRouteText}>Processing AI Traffic Optimization Layers...</Text>
                    </View>
                  ) : routeData && origin.trim() && destination.trim() && !showSuggestions ? (
                    <View>
                      <View style={styles.summaryRow}>
                        <View style={styles.etaInfo}>
                          <CarFront size={28} color="#1f2937" />
                          <View style={styles.etaTextContainer}>
                            <Text style={styles.timeText}>
                              <PlatformTextHighlight level={routeData.congestion.level}>
                                {routeData.duration_minutes}
                              </PlatformTextHighlight> min
                            </Text>
                            <Text style={styles.subText}>
                              Arrive By {getCalculatedArrivalTime(routeData.duration_minutes)} • {routeData.distance_km} km
                            </Text>
                          </View>
                        </View>
                        <TouchableOpacity style={styles.startButton} onPress={handleStartNavigation}>
                          <Text style={styles.startButtonText}>Start</Text>
                        </TouchableOpacity>
                      </View>

                      <View style={styles.detailsCard}>
                        <View style={styles.cardHeader}>
                          <View>
                            <Text style={styles.cardTitle}>{routeData.primary_route}</Text>
                            <Text style={styles.cardSubtitle}>Fastest route • event-aware</Text>
                          </View>
                          <View style={styles.badge}><Text style={styles.badgeText}>{routeData.duration_minutes} min</Text></View>
                        </View>

                        <View style={styles.metricsRow}>
                          <Text style={styles.metricLabel}>Congestion</Text>
                          <View style={styles.progressBar}>
                            <View style={[styles.progress, { 
                              width: `${routeData.congestion.percentage}%`, 
                              backgroundColor: routeData.congestion.level === 'Heavy' ? '#ef4444' : routeData.congestion.level === 'Moderate' ? '#f59e0b' : '#10b981' 
                            }]} />
                          </View>
                          <Text style={styles.metricValue}>{routeData.congestion.level}</Text>
                        </View>

                        <View style={styles.metricsRow}>
                          <Text style={styles.metricLabel}>Distance</Text>
                          <View style={styles.progressBar}>
                            <View style={[styles.progress, styles.distanceProgress, { width: `${Math.min((routeData.distance_km / 30) * 100, 100)}%` }]} />
                          </View>
                          <Text style={styles.metricValue}>{routeData.distance_km} km</Text>
                        </View>

                        <View style={styles.infoBox}>
                          <Info size={14} color="#3b82f6" />
                          <Text style={styles.infoText}>{routeData.intelligence_note}</Text>
                        </View>
                      </View>
                    </View>
                  ) : null}
                </View>
              )}
            </View>
          </View>
        </TouchableWithoutFeedback>
      </KeyboardAvoidingView>
    </View>
  );
}

function PlatformTextHighlight({ level, children }: any) {
  const dynamicColor = level === 'Heavy' ? '#ef4444' : level === 'Moderate' ? '#f59e0b' : '#10b981';
  return <Text style={{ color: dynamicColor }}>{children}</Text>;
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#fff' 
  },
  flexContainer: { flex: 1 },
  innerContainer: { 
    flex: 1, 
    justifyContent: 'flex-end' 
  },
  map: { ...StyleSheet.absoluteFillObject },
  legendCard: { 
    position: 'absolute', 
    top: StatusBar.currentHeight ? StatusBar.currentHeight + 20 : 60, 
    right: 20, 
    backgroundColor: '#fff', 
    paddingVertical: 10, 
    paddingHorizontal: 12, 
    borderRadius: 16, 
    elevation: 4, 
    zIndex: 10 
  },
  legendItem: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginVertical: 3 
  },
  dot: { 
    width: 8, 
    height: 8, 
    borderRadius: 4, 
    marginRight: 8 
  },
  legendText: { 
    fontSize: 11, 
    fontWeight: '600', 
    color: '#374151' 
  },
  overlayWrapper: { 
    paddingHorizontal: 20, 
    paddingBottom: 20 
  },
  expandedWrapper: { 
    height: '65%', 
    backgroundColor: '#fff', 
    borderTopLeftRadius: 30, 
    borderTopRightRadius: 30, 
    paddingTop: 10, 
    paddingHorizontal: 25, 
    elevation: 20 
  },
  searchBar: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    height: 60, 
    paddingHorizontal: 20, 
    backgroundColor: '#fff', 
    borderRadius: 30, 
    elevation: 10 
  },
  searchIcon: { marginRight: 12 },
  placeholderText: { 
    fontSize: 16, 
    fontWeight: '600', 
    color: '#9ca3af' 
  },
  routeBox: { width: '100%' },
  dragHandle: { 
    alignSelf: 'center', 
    width: 40, 
    height: 4, 
    marginBottom: 15, 
    backgroundColor: '#e5e7eb', 
    borderRadius: 2 
  },
  
  inputSection: { 
    width: '100%', 
    position: 'relative', 
    gap: 10 
  },
  inputRow: { width: '88%' },
  pillInputContainer: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    height: 52, 
    paddingHorizontal: 15, 
    backgroundColor: '#f9fafb', 
    borderRadius: 25, 
    borderWidth: 1, 
    borderColor: '#f3f4f6' 
  },
  currentLocationInput: { 
    backgroundColor: '#fff', 
    borderColor: '#3b82f6' 
  },
  activePillInput: { 
    backgroundColor: '#fffcf0', 
    borderColor: '#ffe082' 
  },
  
  activeOriginSearchBar: { 
    borderWidth: 1.5, 
    borderColor: '#4475F2', 
    backgroundColor: '#fff' 
  },
  activeDestSearchBar: { 
    borderWidth: 1.5, 
    borderColor: '#f59e0b', 
    backgroundColor: '#fff' 
  },
  
  actualInput: { 
    flex: 1, 
    fontSize: 14, 
    fontWeight: '500', 
    color: '#1f2937' 
  },
  originInputText: { color: '#3b82f6' },
  destinationInputText: { color: '#f59e0b' },
  originIcon: { marginRight: 10 },
  destinationIcon: { marginRight: 8 },
  actionButton: { padding: 4, marginLeft: 6 },
  
  swapButton: { 
    position: 'absolute', 
    right: 0, 
    top: 52, 
    zIndex: 10, 
    transform: [{ translateY: -18 }] 
  },
  swapIconCircle: { 
    padding: 8, 
    backgroundColor: '#fff', 
    borderRadius: 20, 
    borderWidth: 1, 
    borderColor: '#f3f4f6', 
    elevation: 4 
  },
  
  suggestionsContainer: { 
    position: 'absolute', 
    left: 0, 
    right: '12%', 
    backgroundColor: '#fff', 
    borderRadius: 20, 
    borderWidth: 1, 
    borderColor: '#e5e7eb', 
    elevation: 99, 
    maxHeight: 180, 
    zIndex: 99 
  },
  resultItem: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingVertical: 12, 
    paddingHorizontal: 15, 
    borderBottomWidth: 1, 
    borderBottomColor: '#F3F4F6' 
  },
  iconCircle: { 
    width: 34, 
    height: 34, 
    backgroundColor: '#EEF2FF', 
    borderRadius: 17, 
    justifyContent: 'center', 
    alignItems: 'center', 
    marginRight: 12 
  },
  textContainer: { flex: 1 },
  locationName: { 
    fontSize: 14, 
    fontWeight: '600', 
    color: '#1F2937' 
  },
  locationAddress: { 
    fontSize: 12, 
    color: '#9CA3AF', 
    marginTop: 1 
  },

  divider: { 
    height: 1, 
    marginVertical: 15, 
    backgroundColor: '#f3f4f6' 
  },
  summaryRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'space-between', 
    marginBottom: 15 
  },
  etaInfo: { 
    flexDirection: 'row', 
    alignItems: 'center' 
  },
  etaTextContainer: { marginLeft: 12 },
  timeText: { 
    fontSize: 26, 
    fontWeight: 'bold' 
  },
  subText: { 
    fontSize: 12, 
    color: '#6b7280' 
  },
  startButton: { 
    paddingVertical: 14, 
    paddingHorizontal: 35, 
    backgroundColor: '#4475F2', 
    borderRadius: 30 
  },
  startButtonText: { 
    fontSize: 18, 
    fontWeight: 'bold', 
    color: '#fff' 
  },
  detailsCard: { 
    padding: 15, 
    backgroundColor: '#fff', 
    borderRadius: 20, 
    borderWidth: 1, 
    borderColor: '#f3f4f6' 
  },
  cardHeader: { 
    flexDirection: 'row', 
    alignItems: 'flex-start', 
    justifyContent: 'space-between', 
    marginBottom: 12 
  },
  cardTitle: { 
    fontSize: 15, 
    fontWeight: 'bold', 
    color: '#111827' 
  },
  cardSubtitle: { 
    marginTop: 2, 
    fontSize: 12, 
    color: '#9ca3af' 
  },
  badge: { 
    paddingHorizontal: 12, 
    paddingVertical: 4, 
    backgroundColor: '#eff6ff', 
    borderRadius: 12 
  },
  badgeText: { 
    fontSize: 11, 
    fontWeight: 'bold', 
    color: '#3b82f6' 
  },
  metricsRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginBottom: 8 
  },
  metricLabel: { 
    width: 75, 
    fontSize: 11, 
    color: '#6b7280' 
  },
  progressBar: { 
    flex: 1, 
    height: 6, 
    marginHorizontal: 10, 
    backgroundColor: '#f3f4f6', 
    borderRadius: 3 
  },
  progress: { 
    height: '100%', 
    borderRadius: 3 
  },
  distanceProgress: { backgroundColor: '#3b82f6' },
  metricValue: { 
    width: 60, 
    textAlign: 'right', 
    fontSize: 11, 
    fontWeight: '600', 
    color: '#4b5563' 
  },
  infoBox: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginTop: 10, 
    padding: 12, 
    backgroundColor: '#f0f7ff',
    borderRadius: 12 
  },
  infoText: { 
    flex: 1, 
    marginLeft: 8, 
    fontSize: 11, 
    color: '#3b82f6' 
  },
  loadingWrapper: { 
    paddingVertical: 30, 
    alignItems: 'center', 
    justifyContent: 'center', 
    gap: 12 
  },
  loadingRouteText: { 
    fontSize: 13, 
    fontWeight: '500', 
    color: '#6b7280', 
    textAlign: 'center' 
  }
});