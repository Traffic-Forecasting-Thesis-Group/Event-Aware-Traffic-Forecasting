import React, { useRef, useState } from 'react';
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

const { width } = Dimensions.get('window');

export default function VerificationCodeScreen({ navigation }: any) {
  const [code, setCode] = useState(['', '', '', '', '']);
  const [focusedIndex, setFocusedIndex] = useState<number | null>(null);
  const inputs = useRef<TextInput[]>([]);

  const handleChange = (text: string, index: number) => {
    const newCode = [...code];
    newCode[index] = text;
    setCode(newCode);

    if (text && index < 4) {
      inputs.current[index + 1]?.focus();
    }
  };

  const handleBackspace = (text: string, index: number) => {
    if (!text && index > 0) {
      inputs.current[index - 1]?.focus();
    }
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
              <Text style={styles.title}>Verification Code</Text>
              <Text style={styles.subtitle}>
                We have sent a code to your email
              </Text>

              <View style={styles.codeContainer}>
                {code.map((digit, index) => (
                  <TextInput
                    key={index}
                    ref={(ref) => {
                      if (ref) inputs.current[index] = ref;
                    }}
                    style={[
                      styles.codeInput,
                      focusedIndex === index && styles.activeInput 
                    ]}
                    keyboardType="number-pad"
                    maxLength={1}
                    value={digit}
                    onFocus={() => setFocusedIndex(index)}
                    onBlur={() => setFocusedIndex(null)}
                    onChangeText={(text) => handleChange(text, index)}
                    onKeyPress={({ nativeEvent }) =>
                      nativeEvent.key === 'Backspace' && handleBackspace(digit, index)
                    }
                  />
                ))}
              </View>

              <Text style={styles.resendText}>
                Haven’t got the email yet?{' '}
                <Text style={styles.resendLink} onPress={() => {}}>Resend code</Text>
              </Text>

              <View style={styles.actionContainer}>
                <TouchableOpacity 
                  style={styles.verifyButton} 
                  onPress={() => navigation.navigate('ResetPasswordScreen')}
                >
                  <Text style={styles.verifyButtonText}>Verify</Text>
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
    textAlign: 'center' 
},
  subtitle: { 
    fontSize: 16, 
    color: '#9CA3AF', 
    textAlign: 'center', 
    lineHeight: 22, 
    marginBottom: 40 
},
  codeContainer: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    width: '100%', 
    marginBottom: 20 
},
  codeInput: {
    width: 55, 
    height: 65, 
    borderRadius: 12, 
    borderWidth: 1.5,
    borderColor: '#E5E7EB', 
    backgroundColor: '#F8F9FE',
    textAlign: 'center', 
    fontSize: 24, 
    fontWeight: '600', 
    color: '#374151',
  },
  activeInput: {
    borderColor: '#4475F2', 
  },
  resendText: { 
    fontSize: 14, 
    color: '#9CA3AF', 
    marginBottom: 40 
},
  resendLink: { 
    color: '#4475F2', 
    fontWeight: '700' 
},
  actionContainer: { 
    width: '100%', 
    alignItems: 'center', 
    marginTop: 20 
},
  verifyButton: {
    backgroundColor: '#4475F2', 
    width: '100%', 
    paddingVertical: 18,
    borderRadius: 25, 
    alignItems: 'center', 
    marginBottom: 15,
    elevation: 8, 
    shadowColor: '#4475F2', 
    shadowOffset: { 
        width: 0, 
        height: 4 
    },
    shadowOpacity: 0.3, 
    shadowRadius: 5,
  },
  verifyButtonText: { 
    color: '#fff', 
    fontSize: 18, 
    fontWeight: '600' },
  backText: { 
    color: '#9CA3AF', 
    fontSize: 16, 
    fontWeight: '500' 
},
});