import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
  Image,
  Modal,
  KeyboardAvoidingView,
  Platform,
  TouchableWithoutFeedback,
  Keyboard,
} from 'react-native';
import { ChevronLeft, Camera, X } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';

export default function EditProfileScreen({ navigation }: any) {
  const [image, setImage] = useState<string | null>(null);
  const [isViewVisible, setIsViewVisible] = useState(false);

  // States for profile data
  const [firstName, setFirstName] = useState("Juan");
  const [lastName, setLastName] = useState("Dela Cruz");
  const [displayName, setDisplayName] = useState("juan.dc");
  const [email, setEmail] = useState("juan.delacruz@email.com");
  const [phone, setPhone] = useState("+63 917 123 4567");
  const [city, setCity] = useState("Quezon City");
  const [region, setRegion] = useState("National Capital Region");

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert("Permission denied. Access to the gallery is required.");
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 1,
    });
    if (!result.canceled) {
      setImage(result.assets[0].uri);
    }
  };

  const handleSave = () => {
    Alert.alert("Success", "Profile updated successfully!");
    navigation.goBack();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <Modal visible={isViewVisible} transparent={true} animationType="fade">
        <View style={styles.modalBackground}>
          <TouchableOpacity 
            style={styles.closeModalButton} 
            onPress={() => setIsViewVisible(false)}
          >
            <X size={30} color="#fff" />
          </TouchableOpacity>
          {image ? (
            <Image source={{ uri: image }} style={styles.fullScreenImage} />
          ) : (
            <View style={[styles.avatarCircle, { width: 250, height: 250, borderRadius: 125 }]}>
              <Text style={[styles.avatarText, { fontSize: 80 }]}>JD</Text>
            </View>
          )}
        </View>
      </Modal>

      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
            <ChevronLeft size={24} color="#0084FF" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Personal information</Text>
          <View style={{ width: 40 }} /> 
        </View>

        <ScrollView 
          showsVerticalScrollIndicator={false} 
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.photoSection}>
            <View style={styles.avatarWrapper}>
              <TouchableOpacity 
                activeOpacity={0.8}
                onPress={() => setIsViewVisible(true)} 
                style={styles.avatarCircle}
              >
                {image ? (
                  <Image source={{ uri: image }} style={styles.profileImage} />
                ) : (
                  <Text style={styles.avatarText}>JD</Text>
                )}
              </TouchableOpacity>
              
              <TouchableOpacity 
                activeOpacity={0.9}
                onPress={pickImage} 
                style={styles.cameraBadge}
              >
                <Camera size={14} color="#000" />
              </TouchableOpacity>
            </View>
            
            <TouchableOpacity onPress={pickImage}>
              <Text style={styles.changePhotoText}>Change photo</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.sectionLabel}>BASIC DETAILS</Text>
            <EditableField label="FIRST NAME" value={firstName} onChangeText={setFirstName} />
            <EditableField label="LAST NAME" value={lastName} onChangeText={setLastName} />
            <EditableField label="DISPLAY NAME" value={displayName} onChangeText={setDisplayName} />

            <Text style={[styles.sectionLabel, { marginTop: 25 }]}>CONTACT</Text>
            <EditableField 
              label="EMAIL ADDRESS" 
              value={email} 
              onChangeText={setEmail} 
              isVerified={true} 
              keyboardType="email-address" 
            />
            <EditableField 
              label="PHONE NUMBER" 
              value={phone} 
              onChangeText={setPhone} 
              keyboardType="phone-pad" 
            />

            <Text style={[styles.sectionLabel, { marginTop: 25 }]}>LOCATION</Text>
            <EditableField label="CITY / MUNICIPALITY" value={city} onChangeText={setCity} />
            <EditableField label="REGION" value={region} onChangeText={setRegion} />
          </View>

          <TouchableOpacity style={styles.mainSaveButton} onPress={handleSave}>
            <Text style={styles.mainSaveText}>Save changes</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const EditableField = ({ label, value, onChangeText, isVerified, keyboardType }: any) => (
  <View style={styles.fieldWrapper}>
    <Text style={styles.fieldLabel}>{label}</Text>
    <View style={styles.inputRow}>
      <TextInput
        style={styles.textInput}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType || 'default'}
        autoCapitalize="none"
        placeholderTextColor="#9CA3AF"
      />
      {isVerified && (
        <View style={styles.verifiedTag}>
          <Text style={styles.verifiedTagText}>Verified</Text>
        </View>
      )}
    </View>
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
    borderBottomColor: '#F3F4F6' 
  },
  backButton: { 
    padding: 8, 
    backgroundColor: '#F3F4F6', 
    borderRadius: 12 
  },
  headerTitle: { 
    fontSize: 16, 
    fontWeight: 'bold', 
    color: '#000' 
  },
  scrollContent: { paddingBottom: 40 },
  photoSection: { 
    alignItems: 'center', 
    marginVertical: 25 
  },
  avatarWrapper: {
    position: 'relative',
    marginBottom: 10,
  },
  avatarCircle: { 
    width: 80, 
    height: 80, 
    borderRadius: 40, 
    backgroundColor: '#0084FF', 
    justifyContent: 'center', 
    alignItems: 'center', 
    overflow: 'hidden',
  },
  profileImage: { width: '100%', height: '100%' },
  avatarText: { color: '#fff', fontSize: 28, fontWeight: 'bold' },
  cameraBadge: { 
    position: 'absolute', 
    bottom: 0, 
    right: 0, 
    backgroundColor: '#FFD700', 
    padding: 6, 
    borderRadius: 15, 
    borderWidth: 2, 
    borderColor: '#fff',
    zIndex: 10,
  },
  modalBackground: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fullScreenImage: {
    width: '90%',
    height: '60%',
    resizeMode: 'contain',
  },
  closeModalButton: {
    position: 'absolute',
    top: 50,
    right: 20,
    zIndex: 20,
  },
  changePhotoText: { 
    color: '#0084FF', 
    fontSize: 13, 
    fontWeight: '500' 
  },
  inputContainer: { paddingHorizontal: 20 },
  sectionLabel: { 
    fontSize: 11, 
    fontWeight: 'bold', 
    color: '#9CA3AF', 
    marginBottom: 10 
  },
  fieldWrapper: { 
    paddingVertical: 8, 
    borderBottomWidth: 1, 
    borderBottomColor: '#F3F4F6' 
  },
  fieldLabel: { 
    fontSize: 10, 
    color: '#9CA3AF', 
    marginBottom: 2 
  },
  inputRow: { 
    flexDirection: 'row', 
    alignItems: 'center' 
  },
  textInput: { 
    flex: 1, 
    fontSize: 14, 
    color: '#111827', 
    paddingVertical: 4 
  },
  verifiedTag: { 
    backgroundColor: '#EEF2FF', 
    paddingHorizontal: 8, 
    paddingVertical: 2, 
    borderRadius: 4, 
    borderWidth: 1, 
    borderColor: '#0084FF' 
  },
  verifiedTagText: { 
    fontSize: 9, 
    color: '#0084FF', 
    fontWeight: 'bold' 
  },
  mainSaveButton: { 
    backgroundColor: '#FFD700', 
    marginHorizontal: 20, 
    marginTop: 40, 
    padding: 16, 
    borderRadius: 12, 
    alignItems: 'center', 
    borderWidth: 0
  },
  mainSaveText: { 
    color: '#000', 
    fontWeight: 'bold', 
    fontSize: 15 
  },
});