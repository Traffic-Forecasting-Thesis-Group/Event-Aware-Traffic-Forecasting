import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  SafeAreaView,
  StatusBar,
  Dimensions,
  Keyboard,
  TouchableWithoutFeedback,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

export default function ForgotPasswordScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const handleContinue = () => {
    setError('');
    if (!email.trim()) {
      setError('Email is required');
      return;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Enter a valid email');
      return;
    }
    navigation.navigate('VerificationCodeScreen');
  };

  return (
    <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
      <View style={styles.container}>
        <StatusBar barStyle="light-content" translucent backgroundColor="transparent" />

        <View style={styles.blueHeader}>
          <View style={styles.notchCircle} />
        </View>

        <View style={styles.mainCard}>
          <SafeAreaView style={{ flex: 1 }}>
            <View style={styles.content}>
              <Text style={styles.title}>Forgot Password</Text>
              <Text style={styles.subtitle}>
                Please enter your email to reset the password
              </Text>

              <View style={styles.inputWrapper}>
                <View style={[
                  styles.inputContainer, 
                  error ? styles.errorBorder : (isFocused && styles.activeBorder)
                ]}>
                  <MaterialCommunityIcons
                    name="email-outline"
                    size={22}
                    color={error ? '#ef4444' : (isFocused ? '#4475F2' : '#9CA3AF')}
                    style={{ marginRight: 15 }}
                  />
                  <TextInput
                    style={styles.input}
                    placeholder="Email Address"
                    placeholderTextColor="#9ca3af"
                    value={email}
                    onChangeText={(text) => {
                      setEmail(text);
                      setError('');
                    }}
          
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />
                </View>
                {error ? <Text style={styles.errorText}>{error}</Text> : null}
              </View>

              <View style={styles.footer}>
                <TouchableOpacity 
                  style={styles.continueButton} 
                  onPress={handleContinue}
                >
                  <Text style={styles.continueButtonText}>Continue</Text>
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
		marginBottom: 10, 
		textAlign: 'center' },
  subtitle: { 
		fontSize: 16, 
		color: '#9CA3AF', 
		textAlign: 'center', 
		lineHeight: 22, 
		marginBottom: 40 
	},
  inputWrapper: { 
		width: '100%', 
		marginBottom: 20 },
  inputContainer: {
    flexDirection: 'row', 
		alignItems: 'center', 
		backgroundColor: '#F8F9FE',
    borderRadius: 12, 
		paddingHorizontal: 20, 
		height: 60, 
		borderWidth: 1.5,
    borderColor: 'transparent',
  },

  activeBorder: {
    borderColor: '#4475F2',
    backgroundColor: '#fff', 
  },
  errorBorder: {
    borderColor: '#ef4444',
    backgroundColor: '#fff5f5',
  },
  input: { 
		flex: 1, 
		fontSize: 16, 
		color: '#374151', 
		fontWeight: '500' 
	},
  errorText: { 
		color: '#ef4444', 
		fontSize: 12, 
		marginTop: 5, 
		marginLeft: 5 
	},
  footer: { 
		width: '100%', 
		marginTop: 'auto', 
		paddingBottom: 40, 
		alignItems: 'center' 
	},
  continueButton: {
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
  continueButtonText: { 
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