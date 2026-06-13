import React, { useState, useEffect } from 'react';
import {
  StyleSheet, 
  View, Text, 
  TextInput, 
  TouchableOpacity,
  FlatList, 
  SafeAreaView, 
  StatusBar, 
  ActivityIndicator,
} from 'react-native';
import { ArrowLeft, Search, MapPin, XCircle } from 'lucide-react-native';
import { fetchGeocodeAddress } from '../api/geocode'; 
import { updateCachedLocation } from '../api/locationService'; 

export default function SearchLocationScreen({ navigation, route }: any) {
  const { type } = route.params; 
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    const delayDebounceTimer = setTimeout(async () => {
      setLoading(true);
      try {
        const results = await fetchGeocodeAddress(searchQuery);
        setSearchResults(results); 
      } catch (error) {
        console.error('Live search error:', error);
      } finally {
        setLoading(false);
      }
    }, 500);

    return () => clearTimeout(delayDebounceTimer);
  }, [searchQuery]);

  const handleSelectLocation = (item: any) => {
    const existingHome = route.params?.currentHome || '';
    const existingWork = route.params?.currentWork || '';

    updateCachedLocation(type, item.formattedAddress);

    navigation.navigate({
      name: 'SetLocation',
      params: {
        selectedLocation: item.formattedAddress,
        locationType: type,
        currentHome: type === 'Home' ? item.formattedAddress : existingHome,
        currentWork: type === 'Work' ? item.formattedAddress : existingWork
      },
      merge: true,
    });
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <ArrowLeft color="#1F2937" size={24} />
        </TouchableOpacity>
        <Text style={styles.title}>Search {type}</Text>
        <View style={{ width: 24 }} />
      </View>

      <View style={styles.searchContainer}>
        <View style={[styles.searchBar, searchQuery ? styles.activeSearchBar : null]}>
          <Search color={searchQuery ? '#4475F2' : '#9CA3AF'} size={20} />
          <TextInput
            style={styles.input}
            placeholder={`Search your ${type.toLowerCase()} address...`}
            placeholderTextColor="#9CA3AF"
            value={searchQuery}
            onChangeText={setSearchQuery}
            returnKeyType="search"
          />
          {searchQuery ? (
            <TouchableOpacity onPress={() => { setSearchQuery(''); setSearchResults([]); }}>
              <XCircle color="#9CA3AF" size={20} />
            </TouchableOpacity>
          ) : null}
        </View>

        {loading && <ActivityIndicator style={{ marginTop: 20 }} size="large" color="#4475F2" />}

        <FlatList
          data={searchResults}
          keyExtractor={(item) => item.id}
          style={styles.resultsList}
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
                  <MapPin color="#4475F2" size={20} />
                </View>
                <View style={styles.textContainer}>
                  <Text style={styles.locationName} numberOfLines={1}>
                    {mainTitle}
                  </Text>
                  <Text style={styles.locationAddress} numberOfLines={2}>
                    {cleanSubtitle || item.formattedAddress}
                  </Text>
                </View>
              </TouchableOpacity>
            );
          }}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#fff' 
  },
  header: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'space-between', 
    paddingHorizontal: 20, 
    height: 60, 
    borderBottomWidth: 1, 
    borderBottomColor: '#F3F4F6' 
  },
  title: { 
    fontSize: 18, 
    fontWeight: '700', 
    color: '#1F2937' 
  },
  searchContainer: { 
    flex: 1, 
    paddingHorizontal: 25, 
    paddingTop: 20 
  },
  searchBar: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: '#F8F9FE', 
    borderRadius: 25, 
    paddingHorizontal: 20, 
    height: 55, 
    width: '100%' 
  },
  activeSearchBar: { 
    borderWidth: 1.5, 
    borderColor: '#4475F2', 
    backgroundColor: '#fff' 
  },
  input: { 
    flex: 1, 
    fontSize: 16, 
    color: '#1F2937', 
    marginLeft: 10 
  },
  resultsList: { marginTop: 20 },
  resultItem: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingVertical: 15, 
    borderBottomWidth: 1, 
    borderBottomColor: '#F3F4F6' 
  },
  iconCircle: { 
    width: 40, 
    height: 40, 
    backgroundColor: '#EEF2FF', 
    borderRadius: 20, 
    justifyContent: 'center', 
    alignItems: 'center', 
    marginRight: 15 
  },
  textContainer: { flex: 1 },
  locationName: { 
    fontSize: 15, 
    fontWeight: '600', 
    color: '#1F2937' 
  },
  locationAddress: { 
    fontSize: 13, 
    color: '#9CA3AF', 
    marginTop: 2 
  }
});