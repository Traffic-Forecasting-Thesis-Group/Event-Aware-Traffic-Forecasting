import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  SafeAreaView,
  ImageBackground,
  Dimensions,
  StatusBar,
  Image,
  Alert,
} from 'react-native';
import { ArrowRight, ArrowLeft } from 'lucide-react-native';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';

const { width, height } = Dimensions.get('window');

const onboardingContent = [
  {
    id: 1,
    bg: require('../../assets/onboarding/bg1.png'),
    isFirst: true,
  },
  {
    id: 2,
    title: 'Allow Location Access',
    desc: 'We use your location to show real-time traffic, suggest better routes, and provide accurate travel estimates.',
    bg: require('../../assets/onboarding/bg2.png'),
    btnText: 'Allow Location Access',
    type: 'location',
  },
  {
    id: 3,
    title: 'Stay Updated',
    desc: 'Enable notifications to receive real-time traffic alerts, road incidents, and important updates on the go.',
    bg: require('../../assets/onboarding/bg3.png'),
    btnText: 'Enable Notifications',
    type: 'notification',
  },
  {
    id: 4,
    title: 'Set Home & Work',
    desc: 'Set your home and work locations to get personalized route suggestions and accurate travel estimates.',
    bg: require('../../assets/onboarding/bg4.png'),
    btnText: 'Set Locations',
    type: 'travel_setup',
  },
];

export default function OnboardScreen({ navigation }: any) {
  const [index, setIndex] = useState(0);
  const current = onboardingContent[index];

  const handlePermissions = async () => {
    if (current.type === 'location') {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'The location is needed for travel estimates.');
        return;
      }
    } else if (current.type === 'notification') {
      const { status } = await Notifications.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Notifications are currently disabled. You will not be able to receive traffic alerts.');
        return;
      }
    }
    handleNext();
  };

  const handleNext = () => {
    if (current.type === 'travel_setup') {
      navigation.navigate('SetLocation'); 
    } else if (index < onboardingContent.length - 1) {
      setIndex(index + 1);
    } else {
      navigation.navigate('Main'); 
    }
  };

  const handleNotNow = () => {
    if (current.type === 'travel_setup') {
      navigation.navigate('Main'); 
    } else {
      setIndex(index + 1); 
    }
  };

  const handleBack = () => {
    if (index > 0) setIndex(index - 1);
  };

  return (
    <View style={styles.container}>
      <StatusBar translucent backgroundColor="transparent" barStyle="dark-content" />
      <ImageBackground source={current.bg} style={styles.bgImage} resizeMode="cover">
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.contentWrapper}>
            {current.isFirst ? (
              <View style={styles.firstScreenLayout}>
                <View style={styles.centerLogoContainer}>
                  <Image source={require('../../assets/logo-no-bg.png')} style={styles.logoImage} resizeMode="contain" />
                </View>
                <View style={styles.bottomActionArea}>
                  <TouchableOpacity style={styles.modernPillButton} onPress={handleNext} activeOpacity={0.8}>
                    <Text style={styles.modernButtonText}>GET STARTED</Text>
                    <View style={styles.modernIconCircle}><ArrowRight size={20} color="#4475F2" /></View>
                  </TouchableOpacity>
                </View>
              </View>
            ) : (
              <View style={styles.slidesLayout}>
                <TouchableOpacity style={styles.skipButton} onPress={() => navigation.navigate('Main')}>
                  <Text style={styles.skipText}>Skip</Text>
                </TouchableOpacity>

                <View style={styles.textGroup}>
                  <Text style={styles.titleText}>{current.title}</Text>
                  <Text style={styles.descText}>{current.desc}</Text>
                </View>

                <View style={styles.dotContainer}>
                  {[0, 1, 2].map((i) => (
                    <View key={i} style={[styles.dot, index - 1 === i ? styles.activeDot : null]} />
                  ))}
                </View>

                <TouchableOpacity 
                  style={styles.actionButton} 
                  onPress={(current.type === 'location' || current.type === 'notification') ? handlePermissions : handleNext}
                >
                  <Text style={styles.actionButtonText}>{current.btnText}</Text>
                </TouchableOpacity>
                
                <TouchableOpacity onPress={handleNotNow}>
                  <Text style={styles.notNowText}>Not Now</Text>
                </TouchableOpacity>

                <View style={styles.navArrows}>
                  <TouchableOpacity onPress={handleBack} style={styles.arrowBtn}>
                    <ArrowLeft size={24} color="#fff" />
                  </TouchableOpacity>
                  {index < onboardingContent.length - 1 ? (
                    <TouchableOpacity onPress={handleNext} style={styles.arrowBtn}>
                      <ArrowRight size={24} color="#fff" />
                    </TouchableOpacity>
                  ) : (
                    <View style={{ width: 44 }} />
                  )}
                </View>
              </View>
            )}
          </View>
        </SafeAreaView>
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#fff' 
  },
  bgImage: { 
    width: width, 
    height: height 
  },
  safeArea: { flex: 1 },
  contentWrapper: { flex: 1 },
  firstScreenLayout: { 
    flex: 1, 
    justifyContent: 'space-between' 
  },
  centerLogoContainer: { 
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  logoImage: { 
    width: 140, height: 140 }, 
  bottomActionArea: { 
    paddingBottom: 60, 
    alignItems: 'center', 
    width: '100%' 
  },
  modernPillButton: { 
    flexDirection: 'row', 
    backgroundColor: 'rgba(255, 255, 255, 0.95)', 
    paddingLeft: 35, 
    paddingRight: 8, 
    paddingVertical: 8, 
    borderRadius: 50, 
    alignItems: 'center', 
    justifyContent: 'center', 
    elevation: 12, 
    shadowColor: '#000', 
    shadowOffset: { 
      width: 0, 
      height: 6 }, 
      shadowOpacity: 0.35, 
      shadowRadius: 8 
    },
  modernButtonText: { 
    color: '#4475F2', 
    fontSize: 16, 
    fontWeight: 'bold', 
    letterSpacing: 1.2, 
    marginRight: 20 
  },
  modernIconCircle: { 
    width: 48, 
    height: 48, 
    borderRadius: 24, 
    backgroundColor: '#fff', 
    justifyContent: 'center', 
    alignItems: 'center', 
    borderWidth: 1, 
    borderColor: '#F0F0F0' 
  },
  slidesLayout: { 
    flex: 1, 
    justifyContent: 'flex-end', 
    alignItems: 'center', 
    paddingHorizontal: 35, 
    paddingBottom: 30 
  },
  skipButton: { 
    position: 'absolute', 
    top: 20, 
    left: 25, 
    padding: 10 
  },
  skipText: { 
    color: '#fff', 
    fontSize: 16, 
    fontWeight: '600'
   },
  textGroup: { 
    alignItems: 'center', 
    width: '100%', 
    marginBottom: 20, 
    paddingTop: height * 0.35 
  },
  titleText: { 
    color: '#fff', 
    fontSize: 26, 
    fontWeight: 'bold', 
    textAlign: 'center' 
  },
  descText: { 
    color: '#fff', 
    fontSize: 14, 
    textAlign: 'center', 
    marginTop: 10, 
    lineHeight: 20, 
    opacity: 0.9 
  },
  dotContainer: { 
    flexDirection: 'row', 
    marginBottom: 20 
  },
  dot: { 
    width: 8, 
    height: 8, 
    borderRadius: 4, 
    backgroundColor: 'rgba(255,255,255,0.3)', 
    marginHorizontal: 5 
  },
  activeDot: { 
    backgroundColor: '#fff', 
    width: 24 
  },
  actionButton: { 
    backgroundColor: '#fff', 
    width: '100%', 
    paddingVertical: 16, 
    borderRadius: 35, 
    alignItems: 'center', 
    elevation: 5 
  },
  actionButtonText: { 
    color: '#4475F2', 
    fontWeight: 'bold', 
    fontSize: 16 
  },
  notNowText: { 
    color: '#fff', 
    fontSize: 14, 
    marginTop: 12, 
    opacity: 0.8 
  },
  navArrows: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    width: '100%', 
    marginTop: 25 
  },
  arrowBtn: { padding: 10 },
});