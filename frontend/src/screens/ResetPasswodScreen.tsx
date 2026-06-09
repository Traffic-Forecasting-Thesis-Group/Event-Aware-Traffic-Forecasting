import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  StatusBar,
  Keyboard,
  TouchableWithoutFeedback,
  Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function ResetPasswordScreen({ navigation }: any) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  const [focusedField, setFocusedField] = useState<string | null>(null);

  const isMatching = confirmPassword === '' || password === confirmPassword;

  const handleUpdatePassword = () => {
    if (!password || !confirmPassword) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    Alert.alert(
      "Confirm Changes",
      "Are you sure you want to change your password?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Yes, Update", 
          onPress: () => showSuccessAlert() 
        }
      ]
    );
  };

  const showSuccessAlert = () => {
    Alert.alert(
      "Password updated successfully",
      "Your account is ready to use",
      [{ text: "Go Back to Sign In", onPress: () => navigation.navigate('SignInScreen') }]
    );
  };

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
      <View style={styles.container}>
        <StatusBar barStyle="light-content" translucent backgroundColor="transparent" />

        <View style={styles.blueHeader}>
          <View style={styles.notchCircle} />
        </View>

        <View style={styles.mainCard}>
          <SafeAreaView style={{ flex: 1 }}>
            <View style={styles.content}>
              <Text style={styles.title}>Reset Password</Text>
              <Text style={styles.subtitle}>
                The password must be different than before to ensure safety.
              </Text>

              {/* New Password Input */}
              <View style={[
                styles.inputContainer,
                focusedField === 'new' && styles.activeBorder
              ]}>
                <MaterialCommunityIcons 
                  name="lock-outline" 
                  size={22} 
                  color={focusedField === 'new' ? "#4475F2" : "#9CA3AF"} 
                />
                <TextInput
                  style={styles.input}
                  placeholder="New Password"
                  placeholderTextColor="#9ca3af"
                  secureTextEntry={!showPassword}
                  value={password}
                  onChangeText={setPassword}
                  onFocus={() => setFocusedField('new')}
                  onBlur={() => setFocusedField(null)}
                />
                <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
                  <MaterialCommunityIcons 
                    name={showPassword ? "eye-outline" : "eye-off-outline"} 
                    size={22} 
                    color="#9CA3AF" 
                  />
                </TouchableOpacity>
              </View>

              {/* Confirm Password Input */}
              <View style={[
                styles.inputContainer, 
                !isMatching && styles.errorBorder,
                focusedField === 'confirm' && isMatching && styles.activeBorder
              ]}>
                <MaterialCommunityIcons 
                  name="lock-outline" 
                  size={22} 
                  color={!isMatching ? "#ef4444" : (focusedField === 'confirm' ? "#4475F2" : "#9CA3AF")} 
                />
                <TextInput
                  style={styles.input}
                  placeholder="Confirm Password"
                  placeholderTextColor="#9ca3af"
                  secureTextEntry={!showConfirmPassword}
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  onFocus={() => setFocusedField('confirm')}
                  onBlur={() => setFocusedField(null)}
                />
                <TouchableOpacity onPress={() => setShowConfirmPassword(!showConfirmPassword)}>
                  <MaterialCommunityIcons 
                    name={showConfirmPassword ? "eye-outline" : "eye-off-outline"} 
                    size={22} 
                    color="#9CA3AF" 
                  />
                </TouchableOpacity>
              </View>
              
              {!isMatching && <Text style={styles.errorText}>Passwords do not match</Text>}

              <View style={styles.actionContainer}>
                <TouchableOpacity 
                  style={[styles.resetButton, !isMatching && { opacity: 0.6 }]} 
                  onPress={handleUpdatePassword}
                  disabled={!isMatching}
                >
                  <Text style={styles.resetButtonText}>Update Password</Text>
                </TouchableOpacity>

                <TouchableOpacity onPress={() => navigation.goBack()}>
                  <Text style={styles.backText}>Back</Text>
                </TouchableOpacity>
              </View>
            </View>
          </SafeAreaView>
        </View>
      </View>
    </TouchableWithoutFeedback>
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
    paddingHorizontal: 40, 
    paddingTop: 60, 
    alignItems: 'center' 
},
  title: { 
    fontSize: 32, 
    fontWeight: 'bold', 
    color: '#4475F2', 
    marginBottom: 10 
},
  subtitle: { 
    fontSize: 16, 
    color: '#9CA3AF', 
    textAlign: 'center', 
    lineHeight: 22, 
    marginBottom: 40 
},
  inputContainer: {
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: '#F8F9FE',
    borderRadius: 12, 
    paddingHorizontal: 20, 
    height: 60,
    borderWidth: 1.5, 
    borderColor: 'transparent', 
    marginBottom: 10, 
    width: '100%',
  },
  input: { 
    flex: 1, 
    fontSize: 16, 
    color: '#374151', 
    fontWeight: '500', 
    marginLeft: 10 
},
  activeBorder: {
    borderColor: '#4475F2',
    backgroundColor: '#fff',
  },
  errorBorder: {
    borderColor: '#ef4444',
    backgroundColor: '#fff5f5',
  },
  errorText: {
    color: '#ef4444', 
    fontSize: 12, 
    alignSelf: 'flex-start', 
    marginBottom: 10, 
    marginLeft: 5,
  },
  actionContainer: { 
    width: '100%', 
    marginTop: 20, 
    alignItems: 'center' 
},
  resetButton: {
    backgroundColor: '#4475F2', 
    width: '100%', 
    paddingVertical: 18,
    borderRadius: 25, 
    alignItems: 'center', 
    marginBottom: 15,
    elevation: 8, 
    shadowColor: '#4475F2', 
    shadowOpacity: 0.3,
  },
  resetButtonText: { 
    color: '#fff', 
    fontSize: 18, 
    fontWeight: '600' },
  backText: { 
    color: '#9CA3AF', 
    fontSize: 16, 
    fontWeight: '500' 
},
});