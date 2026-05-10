import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { ArrowLeft, Search, MapPin, Navigation, XCircle } from 'lucide-react-native';

export default function SearchLocationScreen({ navigation, route }: any) {
  const { type } = route.params; 
  const [searchQuery, setSearchQuery] = useState('');

  const [allLocations] = useState([
    { id: '1', name: 'Sta. Mesa, Manila', address: 'Sampaloc / Santa Mesa, Metro Manila' },
    { id: '2', name: 'SM City Sta. Mesa', address: 'Aurora Blvd, Sta. Mesa, Manila' },
    { id: '3', name: 'PUP Sta. Mesa', address: 'Anonas St, Sta. Mesa, Manila' },
    { id: '4', name: 'V. Mapa Station', address: 'Ramon Magsaysay Blvd, Sta. Mesa Manila' },
  ]);

  const filteredResults = allLocations.filter(location =>
    location.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    location.address.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleSelectLocation = (item: any) => {
    navigation.navigate({
      name: 'SetLocation',
      params: {
        selectedLocation: item.name,
        locationType: type 
      },
      merge: true, 
    });
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {/* Header */}
      <View style={styles.blueHeader}>
        <View style={styles.notchCircle} />
      </View>

      <View style={styles.mainCard}>
        <SafeAreaView style={{ flex: 1 }}>
          <View style={styles.content}>
            
            {/* Header Row */}
            <View style={styles.headerRow}>
              <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backIconCircle}>
                <ArrowLeft size={22} color="#fff" />
              </TouchableOpacity>
              <Text style={styles.titleText}>Set {type}</Text>
            </View>

            {/* Search Input */}
            <View style={[styles.searchBar, searchQuery.length > 0 && styles.activeSearchBar]}>
              <Search size={20} color={searchQuery.length > 0 ? "#4475F2" : "#9CA3AF"} />
              <TextInput
                style={styles.input}
                placeholder="Search..."
                placeholderTextColor="#9CA3AF"
                value={searchQuery}
                onChangeText={setSearchQuery}
                autoFocus
              />
              {searchQuery.length > 0 && (
                <TouchableOpacity onPress={() => setSearchQuery('')}>
                  <XCircle size={20} color="#D1D5DB" />
                </TouchableOpacity>
              )}
            </View>

            {/* Use Current Location */}
            <TouchableOpacity style={styles.currentLocationBtn}>
              <Navigation size={18} color="#4475F2" fill="#4475F2" />
              <Text style={styles.currentLocationText}>Use Current Location</Text>
            </TouchableOpacity>

            {/* Filtered Results List */}
            {searchQuery.length > 0 && (
              <FlatList
                data={filteredResults}
                keyExtractor={(item) => item.id}
                style={styles.resultsList}
                ListHeaderComponent={<Text style={styles.sectionTitle}>Search Results</Text>}
                ListEmptyComponent={<Text style={styles.noResultText}>No locations found.</Text>}
                showsVerticalScrollIndicator={false}
                renderItem={({ item }) => (
                  <TouchableOpacity 
                    style={styles.resultItem} 
                    onPress={() => handleSelectLocation(item)}
                  >
                    <View style={styles.locationIconCircle}>
                      <MapPin size={20} color="#9CA3AF" />
                    </View>
                    <View style={styles.textGroup}>
                      <Text style={styles.locationName}>{item.name}</Text>
                      <Text style={styles.locationAddress}>{item.address}</Text>
                    </View>
                  </TouchableOpacity>
                )}
              />
            )}
          </View>
        </SafeAreaView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#4670DD' 
  },
  blueHeader: { 
    height: 120, 
    backgroundColor: '#4670DD', 
    alignItems: 'center' 
  },
  notchCircle: {
    width: 50, 
    height: 50, 
    borderRadius: 25, 
    backgroundColor: '#4670DD',
    marginTop: 50, 
    borderWidth: 8, 
    borderColor: '#4670DD',
    zIndex: 10, 
    position: 'absolute', 
    top: 15,
  },
  mainCard: {
    flex: 1, 
    backgroundColor: '#fff', 
    borderTopLeftRadius: 60, 
    borderTopRightRadius: 60,
    marginTop: -20, 
    overflow: 'hidden',
  },
  content: { 
    flex: 1, 
    paddingHorizontal: 30, 
    paddingTop: 40 
  },
  headerRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginBottom: 25 
  },
  backIconCircle: {
    width: 35, 
    height: 35, 
    borderRadius: 18, 
    backgroundColor: '#4475F2',
    justifyContent: 'center', 
    alignItems: 'center', 
    marginRight: 15
  },
  titleText: { 
    fontSize: 22, 
    fontWeight: 'bold', 
    color: '#4475F2' 
  },
  searchBar: {
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: '#F8F9FE',
    borderRadius: 25, 
    paddingHorizontal: 20, 
    height: 55, 
    width: '100%',
  },
  activeSearchBar: {
    borderWidth: 1.5, 
    borderColor: '#4475F2', 
    backgroundColor: '#fff',
  },
  input: { 
    flex: 1, 
    fontSize: 16, 
    color: '#1F2937', 
    marginLeft: 10 
  },
  currentLocationBtn: {
    flexDirection: 'row', 
    alignItems: 'center', 
    marginTop: 20, 
    paddingLeft: 10
  },
  currentLocationText: {
    color: '#4475F2', 
    fontSize: 14, 
    fontWeight: '600', 
    marginLeft: 10
  },
  resultsList: { marginTop: 30 },
  sectionTitle: {
    fontSize: 14, 
    color: '#9CA3AF', 
    fontWeight: '600', 
    marginBottom: 15, 
    borderTopWidth: 1, 
    borderTopColor: '#F3F4F6', 
    paddingTop: 20
  },
  noResultText: { 
    textAlign: 'center', 
    marginTop: 20, 
    color: '#9CA3AF' 
  },
  resultItem: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginBottom: 25 
  },
  locationIconCircle: {
    width: 40, 
    height: 40, 
    borderRadius: 20, 
    backgroundColor: '#F3F4F6',
    justifyContent: 'center', 
    alignItems: 'center', 
    marginRight: 15
  },
  textGroup: { flex: 1 },
  locationName: { 
    fontSize: 15, 
    fontWeight: 'bold', 
    color: '#1F2937' },
  locationAddress: { 
    fontSize: 12, 
    color: '#9CA3AF', 
    marginTop: 2 },
});