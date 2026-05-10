import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  SafeAreaView,
  StatusBar,
  Dimensions
} from 'react-native';
import { Home, Briefcase, ChevronRight } from 'lucide-react-native';

const { width } = Dimensions.get('window');

export default function SetLocationScreen({ navigation, route }: any) {
  const [locations, setLocations] = useState({
    Home: 'Search your Home Address',
    Work: 'Search your Work Address'
  });

  useEffect(() => {
    if (route.params?.selectedLocation && route.params?.locationType) {
      const { selectedLocation, locationType } = route.params;

      setLocations(prev => ({
        ...prev,
        [locationType]: selectedLocation
      }));

      navigation.setParams({ selectedLocation: undefined, locationType: undefined });
    }
  }, [route.params?.selectedLocation, route.params?.locationType]);

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

            {/* Location Selection Cards */}
            <View style={styles.cardContainer}>
              {/* Home Selection Card */}
              <TouchableOpacity 
                style={styles.locationCard}
                onPress={() => navigation.navigate('SearchLocation', { type: 'Home' })}
              >
                <Home size={22} color="#4475F2" fill="#4475F2" fillOpacity={0.1} />
                <Text 
                  style={[
                    styles.cardText, 
                    locations.Home !== 'Search your Home Address' && styles.activeText
                  ]} 
                  numberOfLines={1}
                >
                  {locations.Home}
                </Text>
                <ChevronRight size={20} color="#4475F2" />
              </TouchableOpacity>

              {/* Work Selection Card */}
              <TouchableOpacity 
                style={styles.locationCard}
                onPress={() => navigation.navigate('SearchLocation', { type: 'Work' })}
              >
                <Briefcase size={22} color="#4475F2" fill="#4475F2" fillOpacity={0.1} />
                <Text 
                  style={[
                    styles.cardText, 
                    locations.Work !== 'Search your Work Address' && styles.activeText
                  ]} 
                  numberOfLines={1}
                >
                  {locations.Work}
                </Text>
                <ChevronRight size={20} color="#4475F2" />
              </TouchableOpacity>
            </View>

            <View style={styles.footer}>
              <TouchableOpacity 
                style={styles.saveButton}
                onPress={() => navigation.navigate('Main')}
              >
                <Text style={styles.saveButtonText}>Save & Continue</Text>
              </TouchableOpacity>
              
              <TouchableOpacity onPress={() => navigation.goBack()}>
                <Text style={styles.backText}>Back</Text>
              </TouchableOpacity>
            </View>
          </View>
        </SafeAreaView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, 
    backgroundColor: '#4475F2' 
  },
  blueHeader: {
    height: 120,
    backgroundColor: '#4670DD',
    alignItems: 'center',
    justifyContent: 'flex-start',
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
    width: '100%',
  },
  cardText: { 
    flex: 1, 
    fontSize: 15, 
    color: '#9CA3AF', 
    marginLeft: 15,
    fontWeight: '500' 
  },
  activeText: {
    color: '#4475F2', 
  },
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
    elevation: 8,
  },
  saveButtonText: { 
    color: '#fff', 
    fontSize: 18, 
    fontWeight: '600' },
  backText: { 
    color: '#9CA3AF', 
    fontSize: 16, 
    fontWeight: '500' 
  },
});