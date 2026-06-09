import React, { useState } from 'react';
import { useIsFocused } from '@react-navigation/native';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ScrollView,
  Modal,
  Platform,
  StatusBar,
  Alert,
} from 'react-native';

import {
  User,
  Lock,
  MapPin,
  Bell,
  Eye,
  LogOut,
  ChevronRight,
  ShieldCheck,
  Edit3,
} from 'lucide-react-native';

export default function ProfileScreen({ navigation }: any) {
  const [isAvatarVisible, setIsAvatarVisible] = useState(false);
  const isFocused = useIsFocused();

  const handleSignOut = () => {
    Alert.alert(
      "Sign Out",
      "Are you sure you want to sign out?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Sign Out", 
          style: "destructive",
          onPress: () => {
            navigation.reset({
              index: 0,
              routes: [{ name: 'Landing' }],
            });
          }
        }
      ]
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      {isFocused && (
        <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
      )}

      {/* HEADER */}
      <View style={styles.headerTop}>
        <Text style={styles.headerTitle}>Profile</Text>
        <TouchableOpacity
          style={styles.editIconButton}
          onPress={() => navigation.navigate('EditProfileScreen')}
        >
          <Edit3 size={20} color="#0084FF" />
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* PROFILE HEADER */}
        <View style={styles.profileHeader}>
          <View style={styles.avatarContainer}>
            <TouchableOpacity
              style={styles.avatarCircle}
              onPress={() => setIsAvatarVisible(true)}
              activeOpacity={0.8}
            >
              <Text style={styles.avatarText}>JD</Text>
              <View style={styles.cameraBadge}>
                <Edit3 size={10} color="#000" />
              </View>
            </TouchableOpacity>

            <Text style={styles.userName}>Juan Dela Cruz</Text>
            <Text style={styles.userEmail}>juan.delacruz@email.com</Text>

            <View style={styles.verifiedBadge}>
              <ShieldCheck size={14} color="#0084FF" />
              <Text style={styles.verifiedText}>Verified reporter</Text>
            </View>
          </View>

          {/* STATS */}
          <View style={styles.statsRow}>
            <StatItem number="47" label="Reports" />
            <View style={styles.statDivider} />
            <StatItem number="132" label="Upvotes" />
            <View style={styles.statDivider} />
            <StatItem number="8" label="Day streak" />
          </View>
        </View>

        {/* MENU */}
        <View style={styles.menuContainer}>
          <Text style={styles.sectionTitle}>ACCOUNT</Text>
          <MenuLink
            icon={<User size={20} color="#0084FF" />}
            label="Personal information"
            sublabel="Name, email, phone"
            onPress={() => navigation.navigate('EditProfileScreen')}
          />
          <MenuLink
            icon={<Lock size={20} color="#0084FF" />}
            label="Password & security"
            sublabel="Last changed 3 months ago"
            onPress={() => navigation.navigate('PasswordScreen')}
          />
          <MenuLink
            icon={<MapPin size={20} color="#0084FF" />}
            label="Home & work locations"
            sublabel="Quezon City, Makati"
          />

          <Text style={[styles.sectionTitle, styles.sectionSpacing]}>PREFERENCES</Text>
          <MenuLink
            icon={<Bell size={20} color="#0084FF" />}
            label="Notification Settings"
            sublabel="Alerts, frequency, channels"
            onPress={() => navigation.navigate('NotificationSettingsScreen')}
          />
          <MenuLink
            icon={<Eye size={20} color="#0084FF" />}
            label="Appearance & accessibility"
            sublabel="Theme, font size"
          />
        </View>

        {/* SIGN OUT BUTTON */}
        <TouchableOpacity 
          style={styles.signOutButton} 
          onPress={handleSignOut}
        >
          <LogOut size={18} color="#ef4444" />
          <Text style={styles.signOutText}>Sign out</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* AVATAR MODAL */}
      <Modal
        visible={isAvatarVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setIsAvatarVisible(false)}
      >
        <TouchableOpacity
          style={styles.fullScreenOverlay}
          activeOpacity={1}
          onPress={() => setIsAvatarVisible(false)}
        >
          <StatusBar barStyle="light-content" />
          <View style={styles.fullAvatarCircle}>
            <Text style={styles.fullAvatarText}>JD</Text>
          </View>
          <Text style={styles.closeInstruction}>Tap anywhere to close</Text>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
}

// Helper Components
const MenuLink = ({ icon, label, sublabel, onPress }: any) => (
  <TouchableOpacity style={styles.menuItem} onPress={onPress}>
    <View style={styles.menuLeft}>
      <View style={styles.iconCircle}>{icon}</View>
      <View>
        <Text style={styles.menuLabel}>{label}</Text>
        <Text style={styles.menuSublabel}>{sublabel}</Text>
      </View>
    </View>
    <ChevronRight size={18} color="#D1D5DB" />
  </TouchableOpacity>
);

const StatItem = ({ number, label }: any) => (
  <View style={styles.statItem}>
    <Text style={styles.statNumber}>{number}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </View>
);

const styles = StyleSheet.create({
  safeArea: { 
    flex: 1, 
    backgroundColor: '#fff' 
  },
  headerTop: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    borderBottomWidth: 1, 
    borderBottomColor: '#E5E7EB', 
    paddingHorizontal: 20, 
    paddingVertical: 12 
  },
  headerTitle: { 
    fontSize: 24, 
    fontWeight: 'bold', 
    color: '#111827' 
  },
  editIconButton: { 
    padding: 6, 
    borderRadius: 8, 
    backgroundColor: '#F3F4F6' 
  },
  profileHeader: { 
    paddingHorizontal: 20, 
    paddingTop: 10 
  },
  avatarContainer: { 
    alignItems: 'center', 
    marginTop: 10 
  },
  avatarCircle: { 
    width: 90, 
    height: 90, 
    borderRadius: 45, 
    backgroundColor: '#0084FF', 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  avatarText: { 
    color: '#fff', 
    fontSize: 32, 
    fontWeight: 'bold' 
  },
  cameraBadge: { 
    position: 'absolute', 
    bottom: 2, 
    right: 2, 
    backgroundColor: '#FFD700', 
    padding: 4, 
    borderRadius: 10, 
    borderWidth: 2, 
    borderColor: '#fff' 
  },
  userName: { 
    fontSize: 20, 
    fontWeight: 'bold', 
    marginTop: 12 
  },
  userEmail: { 
    fontSize: 14, 
    color: '#6B7280' 
  },
  verifiedBadge: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginTop: 6 
  },
  verifiedText: { 
    fontSize: 13, 
    color: '#0084FF', 
    marginLeft: 4, 
    fontWeight: '500' 
  },
  statsRow: { 
    flexDirection: 'row', 
    marginTop: 30, 
    paddingVertical: 15, 
    borderTopWidth: 1, 
    borderBottomWidth: 1, 
    borderColor: '#F3F4F6' 
  },
  statItem: { 
    flex: 1, 
    alignItems: 'center' 
  },
  statNumber: { 
    fontSize: 18, 
    fontWeight: 'bold', 
    color: '#0084FF' 
  },
  statLabel: { 
    fontSize: 12, 
    color: '#6B7280', 
    marginTop: 2 
  },
  statDivider: { 
    width: 1, 
    backgroundColor: '#E5E7EB' 
  },
  menuContainer: { 
    paddingHorizontal: 20, 
    marginTop: 20 
  },
  sectionTitle: { 
    fontSize: 12, 
    fontWeight: 'bold', 
    color: '#9CA3AF', 
    letterSpacing: 1 
  },
  sectionSpacing: { marginTop: 24 },
  menuItem: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    paddingVertical: 16, 
    borderBottomWidth: 1, 
    borderBottomColor: '#F9FAFB' 
  },
  menuLeft: { 
    flexDirection: 'row', 
    alignItems: 'center' 
  },
  iconCircle: { 
    marginRight: 16 
  },
  menuLabel: { 
    fontSize: 15, 
    fontWeight: '500', 
    color: '#111827' 
  },
  menuSublabel: { 
    fontSize: 12, 
    color: '#9CA3AF', 
    marginTop: 2 
  },
  signOutButton: { 
    flexDirection: 'row', 
    justifyContent: 'center', 
    alignItems: 'center', 
    marginHorizontal: 20, 
    marginVertical: 40, 
    padding: 16, 
    borderRadius: 12, 
    backgroundColor: '#FFF1F2' 
  },
  signOutText: { 
    color: '#EF4444', 
    fontWeight: 'bold', 
    marginLeft: 8 
  },
  fullScreenOverlay: { 
    flex: 1, 
    backgroundColor: 'rgba(0,0,0,0.9)', 
    justifyContent: 'center', 
    alignItems: 'center' 
  },
  fullAvatarCircle: { 
    width: 260, 
    height: 260, 
    borderRadius: 130, 
    backgroundColor: '#0084FF', 
    justifyContent: 'center', 
    alignItems: 'center', 
    ...Platform.select({ 
      ios: { 
        shadowColor: '#000', 
        shadowOffset: { 
          width: 0, 
          height: 10 }, 
        shadowOpacity: 0.3, 
        shadowRadius: 20 
      }, 
      android: { elevation: 10 } }) },
  fullAvatarText: { 
    color: '#fff', 
    fontSize: 90, 
    fontWeight: 'bold' 
  },
  closeInstruction: { 
    color: '#9CA3AF', 
    marginTop: 30, 
    fontSize: 14 
  },
});