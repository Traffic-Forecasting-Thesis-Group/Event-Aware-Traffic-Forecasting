import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, TextInput,
  ImageBackground, Dimensions, ScrollView, StatusBar,
  Image, ActivityIndicator,
} from 'react-native';
import { Ionicons, FontAwesome } from '@expo/vector-icons';
import { signIn } from '../api/authService'; 

const { height, width } = Dimensions.get('window');

export default function SignInScreen({ navigation }: any) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [focusedInput, setFocusedInput] = useState<string | null>(null);
  const [errors, setErrors] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);

  const handleSignIn = async () => {
    let tempErrors = { email: '', password: '' };
    let isValid = true;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim()) {
      tempErrors.email = 'Email is required';
      isValid = false;
    } else if (!emailRegex.test(email)) {
      tempErrors.email = 'Please enter a valid email';
      isValid = false;
    }

    if (!password.trim()) {
      tempErrors.password = 'Password is required';
      isValid = false;
    }

    setErrors(tempErrors);
    if (!isValid) return;

    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      //replace the above line with the actual sign-in call once backend is ready
      //const tokens = await signIn({ email: email.trim(), password });
      //console.log("Sign-in Success, tokens generated:", tokens);
      
      navigation.navigate('Main');
    } catch (err: any) {
      const msg = err?.response?.data?.message ?? 'Invalid email or password.';
      setErrors(prev => ({ ...prev, email: msg }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" translucent backgroundColor="transparent" />
      
      <ImageBackground
        source={require('../../assets/splash-landing-bg.png')}
        style={styles.backgroundImage}
        resizeMode="cover"
      />

      <View style={styles.contentWrapper}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.navigate('Landing')} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="white" />
          </TouchableOpacity>
        </View>

        <View style={styles.outerBorder}>
          <View style={styles.middleBorder}>
            <View style={styles.whiteCard}>
              <ScrollView 
                showsVerticalScrollIndicator={false} 
                contentContainerStyle={styles.scrollContent}
                keyboardShouldPersistTaps="handled"
              >
                <Text style={styles.welcomeTitle}>Welcome Back</Text>
                <Text style={styles.subtitle}>Sign in to access your account</Text>

                {/* Email Input Section */}
                <View style={styles.inputWrapper}>
                  <View style={[
                    styles.inputContainer, 
                    errors.email ? styles.inputErrorBorder : (focusedInput === 'email' ? styles.inputActiveBorder : null)
                  ]}>
                    <Ionicons 
                      name="mail" 
                      size={20} 
                      color={errors.email ? "#ef4444" : (focusedInput === 'email' ? "#4475F2" : "#9ca3af")} 
                      style={styles.inputIcon} 
                    />
                    <TextInput
                      style={styles.input}
                      placeholder="Email"
                      placeholderTextColor="#9ca3af"
                      value={email}
                      selectionColor="#4475F2"
                      onFocus={() => setFocusedInput('email')}
                      onBlur={() => setFocusedInput(null)}
                      onChangeText={(text) => { setEmail(text); setErrors(p => ({ ...p, email: '' })); }}
                      keyboardType="email-address"
                      autoCapitalize="none"
                      autoCorrect={false}
                      editable={!loading}
                    />
                  </View>
                  {errors.email ? <Text style={styles.errorText}>{errors.email}</Text> : null}
                </View>

                {/* Password Input Section */}
                <View style={styles.inputWrapper}>
                  <View style={[
                    styles.inputContainer, 
                    errors.password ? styles.inputErrorBorder : (focusedInput === 'password' ? styles.inputActiveBorder : null)
                  ]}>
                    <Ionicons 
                      name="lock-closed" 
                      size={20} 
                      color={errors.password ? "#ef4444" : (focusedInput === 'password' ? "#4475F2" : "#9ca3af")} 
                      style={styles.inputIcon} 
                    />
                    <TextInput
                      style={styles.input}
                      placeholder="Password"
                      placeholderTextColor="#9ca3af"
                      value={password}
                      selectionColor="#4475F2"
                      onFocus={() => setFocusedInput('password')}
                      onBlur={() => setFocusedInput(null)}
                      onChangeText={(text) => { setPassword(text); setErrors(p => ({ ...p, password: '' })); }}
                      secureTextEntry={!isPasswordVisible}
                      editable={!loading}
                    />
                    <TouchableOpacity onPress={() => setIsPasswordVisible(!isPasswordVisible)} disabled={loading}>
                      <Ionicons 
                        name={isPasswordVisible ? "eye" : "eye-off"} 
                        size={20} 
                        color={focusedInput === 'password' ? "#4475F2" : "#9ca3af"} 
                      />
                    </TouchableOpacity>
                  </View>
                  {errors.password ? <Text style={styles.errorText}>{errors.password}</Text> : null}
                </View>

                <TouchableOpacity style={styles.footerContainer} onPress={() => navigation.navigate('ForgotPasswordScreen')} disabled={loading}>
                  <Text style={styles.forgotText}>Forgot Password? <Text style={styles.linkText}>Click Here</Text></Text>
                </TouchableOpacity>

                <TouchableOpacity 
                  style={[styles.signInButton, loading && { opacity: 0.7 }]} 
                  activeOpacity={0.7} 
                  onPress={handleSignIn}
                  disabled={loading}
                >
                  {loading 
                    ? <ActivityIndicator color="#fff" /> 
                    : <Text style={styles.buttonText}>Sign in</Text>}
                </TouchableOpacity>

                <View style={styles.orContainer}>
                  <View style={styles.line} /><Text style={styles.orText}>or continue with</Text><View style={styles.line} />
                </View>

                <View style={styles.socialRow}>
                  <TouchableOpacity style={[styles.socialBox, styles.shadow]} disabled={loading}>
                    <FontAwesome name="facebook" size={28} color="#1877F2" />
                  </TouchableOpacity>
                  <TouchableOpacity style={[styles.socialBox, styles.shadow]} disabled={loading}>
                    <Image 
                      source={require('../../assets/google-logo-icon.png')} 
                      style={{ width: 28, height: 28 }} 
                      resizeMode="contain"
                    />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity style={styles.footerContainer} onPress={() => navigation.navigate('SignUpScreen')} disabled={loading}>
                  <Text style={styles.footerText}>Don't have an account? <Text style={styles.linkText}>Sign up</Text></Text>
                </TouchableOpacity>
              </ScrollView>
            </View>
          </View>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#4475F2' 
  },
  backgroundImage: { ...StyleSheet.absoluteFillObject },
  contentWrapper: { flex: 1 },
  header: { 
    paddingLeft: 20, 
    paddingTop: StatusBar.currentHeight ? StatusBar.currentHeight + 10 : 45 
  },
  backButton: { 
    width: 40, 
    height: 40 
  },
  outerBorder: { 
    flex: 1, 
    marginTop: height * 0.12, 
    backgroundColor: '#FFF4D2', 
    borderTopLeftRadius: 50, 
    borderTopRightRadius: 50, 
    paddingTop: 8 
  },
  middleBorder: { 
    flex: 1, 
    backgroundColor: '#D1E0FF', 
    borderTopLeftRadius: 45, 
    borderTopRightRadius: 45, 
    paddingTop: 8 
  },
  whiteCard: { 
    flex: 1, 
    backgroundColor: '#ffffff', 
    borderTopLeftRadius: 40, 
    borderTopRightRadius: 40, 
    overflow: 'hidden' 
  },
  scrollContent: { 
    flexGrow: 1, 
    alignItems: 'center', 
    paddingHorizontal: 35, 
    paddingTop: 35, 
    paddingBottom: 40 
  },
  welcomeTitle: { 
    fontSize: 34, 
    fontWeight: 'bold', 
    color: '#4475F2', 
    marginBottom: 5 
  },
  subtitle: { 
    fontSize: 15, 
    color: '#6b7280',
    marginBottom: 30, 
    textAlign: 'center' 
  },
  inputWrapper: { 
    width: '100%', 
    marginBottom: 18 
  },
  inputContainer: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: '#F8F9FA', 
    borderRadius: 18, 
    paddingHorizontal: 20, 
    width: '100%', 
    height: 65, 
    borderWidth: 1.5, 
    borderColor: 'transparent' 
  },
  inputActiveBorder: { 
    borderColor: '#4475F2', 
    backgroundColor: '#fff' 
  },
  inputErrorBorder: { 
    borderColor: '#ef4444', 
    backgroundColor: '#fff5f5' 
  },
  errorText: { 
    color: '#ef4444', 
    fontSize: 12, 
    marginTop: 5, 
    marginLeft: 10, 
    fontWeight: '600' 
  },
  inputIcon: { marginRight: 15 },
  input: { 
    flex: 1, 
    fontSize: 16, 
    color: '#374151', 
    fontWeight: '500' 
  },
  forgotText: { 
    fontSize: 13, 
    color: '#6b7280' 
  },
  signInButton: { 
    backgroundColor: '#4871E0', 
    width: '100%', 
    height: 60, 
    borderRadius: 30, 
    justifyContent: 'center', 
    alignItems: 'center', 
    marginBottom: 25, 
    elevation: 4, 
    shadowColor: '#4475F2', 
    shadowOffset: { 
      width: 0, 
      height: 4 
    }, 
    shadowOpacity: 0.3, 
    shadowRadius: 5 
  },
  buttonText: { 
    color: '#ffffff', 
    fontSize: 18, 
    fontWeight: 'bold', 
    letterSpacing: 0.5 
  },
  orContainer: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginBottom: 25, width: '100%' 
  },
  line: { 
    flex: 1, 
    height: 1, 
    backgroundColor: '#E5E7EB' 
  },
  orText: { 
    marginHorizontal: 15, 
    fontSize: 14, 
    color: '#9ca3af', 
    fontWeight: '500' 
  },
  socialRow: { 
    flexDirection: 'row', 
    justifyContent: 'center', 
    gap: 20, 
    marginBottom: 25 
  },
  socialBox: { 
    width: width * 0.22, 
    height: 60, 
    borderWidth: 1, 
    borderColor: '#F3F4F6', 
    borderRadius: 18, 
    justifyContent: 'center', 
    alignItems: 'center', 
    backgroundColor: '#fff' 
  },
  shadow: { 
    elevation: 2, 
    shadowColor: '#000', 
    shadowOffset: { width: 0, height: 2 }, 
    shadowOpacity: 0.05, 
    shadowRadius: 3 
  },
  footerContainer: { 
    marginTop: 10, 
    marginBottom: 20 
  },
  footerText: { 
    fontSize: 14, 
    color: '#6b7280' 
  },
  linkText: { 
    color: '#4475F2', 
    fontWeight: '800' 
  },
});