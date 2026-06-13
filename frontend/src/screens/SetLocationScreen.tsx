import React, { useState, useEffect } from 'react';
import {
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  SafeAreaView,
  StatusBar, 
  Alert, 
  ActivityIndicator,
} from 'react-native';
import { useIsFocused } from '@react-navigation/native'; 
import { Home, Briefcase, ChevronRight } from 'lucide-react-native';
import { saveUserLocations, geocodeAddress, getCachedLocations, clearCachedLocations } from '../api/locationService';

const PLACEHOLDER_HOME = 'Search your Home Address';
const PLACEHOLDER_WORK = 'Search your Work Address';

export default function SetLocationScreen({ navigation, route }: any) {
  const isFocused = useIsFocused(); 
  const [locations, setLocations] = useState({ Home: PLACEHOLDER_HOME, Work: PLACEHOLDER_WORK });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    clearCachedLocations();
    setLocations({ Home: PLACEHOLDER_HOME, Work: PLACEHOLDER_WORK });
  }, []);

  useEffect(() => {
    if (isFocused) {
      const activeCache = getCachedLocations();
      
      const currentHomeParam = route.params?.currentHome;
      const currentWorkParam = route.params?.currentWork;

      setLocations({
        Home: currentHomeParam || (activeCache.Home !== PLACEHOLDER_HOME ? activeCache.Home : PLACEHOLDER_HOME),
        Work: currentWorkParam || (activeCache.Work !== PLACEHOLDER_WORK ? activeCache.Work : PLACEHOLDER_WORK)
      });
    }
  }, [isFocused, route.params?.currentHome, route.params?.currentWork]);

  const handleSave = async () => {
    const homeSet = locations.Home !== PLACEHOLDER_HOME;
    const workSet = locations.Work !== PLACEHOLDER_WORK;

    if (!homeSet && !workSet) {
      Alert.alert('Missing Info', 'Please set at least one location.');
      return;
    }

    setLoading(true);
    try {
      const [homeCoords, workCoords] = await Promise.all([
        homeSet ? geocodeAddress(locations.Home) : Promise.resolve(null),
        workSet ? geocodeAddress(locations.Work) : Promise.resolve(null),
      ]);

      await saveUserLocations({
        home: homeSet ? { address: locations.Home, lat: homeCoords?.lat ?? null, lng: homeCoords?.lng ?? null } : null,
        work: workSet ? { address: locations.Work, lat: workCoords?.lat ?? null, lng: workCoords?.lng ?? null } : null,
      });

      clearCachedLocations();
      navigation.navigate('Main');
    } catch (err: any) {
      Alert.alert('Error', err?.message ?? 'Could not save locations. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const noneSet = locations.Home === PLACEHOLDER_HOME && locations.Work === PLACEHOLDER_WORK;

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <View style={styles.blueHeader}>
        <View style={styles.notchCircle} />
      </View>

      <View style={styles.mainCard}>
        <SafeAreaView style={{ flex: 1 }}>
          <View style={styles.content}>
            <Text style={styles.title}>Set Home & Work</Text>
            <Text style={styles.subtitle}>
              Please enter your locations to improve your experience and get better routing
            </Text>

            <View style={styles.cardContainer}>
              <TouchableOpacity
                style={styles.locationCard}
                onPress={() => navigation.navigate('SearchLocation', { 
                  type: 'Home',
                  currentHome: locations.Home !== PLACEHOLDER_HOME ? locations.Home : '',
                  currentWork: locations.Work !== PLACEHOLDER_WORK ? locations.Work : ''
                })}
              >
                <Home size={22} color="#4475F2" />
                <Text style={[styles.cardText, locations.Home !== PLACEHOLDER_HOME && styles.activeText]} numberOfLines={1}>
                  {locations.Home}
                </Text>
                <ChevronRight size={20} color="#4475F2" />
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.locationCard}
                onPress={() => navigation.navigate('SearchLocation', { 
                  type: 'Work',
                  currentHome: locations.Home !== PLACEHOLDER_HOME ? locations.Home : '',
                  currentWork: locations.Work !== PLACEHOLDER_WORK ? locations.Work : ''
                })}
              >
                <Briefcase size={22} color="#4475F2" />
                <Text style={[styles.cardText, locations.Work !== PLACEHOLDER_WORK && styles.activeText]} numberOfLines={1}>
                  {locations.Work}
                </Text>
                <ChevronRight size={20} color="#4475F2" />
              </TouchableOpacity>
            </View>

            <View style={styles.footer}>
              <TouchableOpacity
                style={[styles.saveButton, (noneSet || loading) && styles.saveButtonDisabled]}
                onPress={handleSave}
                disabled={noneSet || loading}
              >
                {loading
                  ? <ActivityIndicator color="#fff" />
                  : <Text style={styles.saveButtonText}>Save & Continue</Text>}
              </TouchableOpacity>

              <TouchableOpacity onPress={() => { clearCachedLocations(); navigation.navigate('Main'); }}>
                <Text style={styles.backText}>Skip for now</Text>
              </TouchableOpacity>
            </View>
          </View>
        </SafeAreaView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#4475F2' 
  },
  blueHeader: { 
    height: 120, 
    backgroundColor: '#4670DD', 
    alignItems: 'center', 
    justifyContent: 'flex-start' 
  },
  notchCircle: {
    width: 50, 
    height: 50, 
    borderRadius: 25, 
    backgroundColor: '#4670DD',
    marginTop: 50, 
    borderWidth: 8, 
    borderColor: '#4670DD', 
    position: 'absolute', 
    top: 15
  },
  mainCard: { 
    flex: 1, 
    backgroundColor: '#fff', 
    borderTopLeftRadius: 60, 
    borderTopRightRadius: 60, 
    marginTop: -20, 
    overflow: 'hidden' 
  },
  content: { 
    flex: 1, 
    paddingHorizontal: 40, 
    paddingTop: 60, 
    alignItems: 'center' 
  },
  title: { 
    fontSize: 32, 
    fontWeight: 'bold', 
    color: '#4475F2', 
    marginBottom: 10, 
    textAlign: 'center' 
  },
  subtitle: { 
    fontSize: 16, 
    color: '#9CA3AF', 
    textAlign: 'center', 
    lineHeight: 22, 
    marginBottom: 40, 
    paddingHorizontal: 10 
  },
  cardContainer: { 
    width: '100%', 
    gap: 20 
  },
  locationCard: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    padding: 20, 
    borderRadius: 12, 
    backgroundColor: '#F8F9FE', 
    width: '100%' 
  },
  cardText: { 
    flex: 1, 
    fontSize: 15, 
    color: '#9CA3AF',
    marginLeft: 15, 
    fontWeight: '500' 
  },
  activeText: { color: '#4475F2' },
  footer: { 
    width: '100%', 
    marginTop: 'auto', 
    paddingBottom: 40, 
    alignItems: 'center' 
  },
  saveButton: { 
    backgroundColor: '#4475F2', 
    width: '100%', 
    paddingVertical: 18, 
    borderRadius: 25, 
    alignItems: 'center', 
    marginBottom: 15, 
    shadowColor: '#4475F2', 
    shadowOffset: { 
      width: 0, 
      height: 4 
    }, 
    shadowOpacity: 0.3, 
    shadowRadius: 5, 
    elevation: 8 
  },
  saveButtonDisabled: { opacity: 0.45 },
  saveButtonText: { 
    color: '#fff', 
    fontSize: 18, 
    fontWeight: '600' 
  },
  backText: { 
    color: '#9CA3AF', 
    fontSize: 16, 
    fontWeight: '500' 
  },
});