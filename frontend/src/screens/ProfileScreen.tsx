import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ScrollView,
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
  Edit3
} from 'lucide-react-native';

export default function ProfileScreen() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header Section with Edit Icon */}
        <View style={styles.profileHeader}>
          <View style={styles.headerTop}>
            <Text style={styles.headerTitle}>Profile</Text>
            <TouchableOpacity style={styles.editIconButton}>
              <Edit3 size={20} color="#0084FF" />
            </TouchableOpacity>
          </View>
          
          {/* Avatar and Name Section */}
          <View style={styles.avatarContainer}>
            <View style={styles.avatarCircle}>
              <Text style={styles.avatarText}>JD</Text>
              <View style={styles.cameraBadge}>
                <Edit3 size={10} color="#000" />
              </View>
            </View>
            <Text style={styles.userName}>Juan Dela Cruz</Text>
            <Text style={styles.userEmail}>juan.delacruz@email.com</Text>
            <View style={styles.verifiedBadge}>
              <ShieldCheck size={14} color="#0084FF" />
              <Text style={styles.verifiedText}>Verified reporter</Text>
            </View>
          </View>

          {/* Stats Section with Dividers */}
          <View style={styles.statsRow}>
            <View style={styles.statItem}>
              <Text style={styles.statNumber}>47</Text>
              <Text style={styles.statLabel}>Reports</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statNumber}>132</Text>
              <Text style={styles.statLabel}>Upvotes</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statNumber}>8</Text>
              <Text style={styles.statLabel}>Day streak</Text>
            </View>
          </View>
        </View>

        {/* Account & Preferences Menu */}
        <View style={styles.menuContainer}>
          <Text style={styles.sectionTitle}>ACCOUNT</Text>
          <MenuLink 
            icon={<User size={20} color="#0084FF" />} 
            label="Personal information" 
            sublabel="Name, email, phone" 
          />
          <MenuLink 
            icon={<Lock size={20} color="#0084FF" />} 
            label="Password & security" 
            sublabel="Last changed 3 months ago" 
          />
          <MenuLink 
            icon={<MapPin size={20} color="#0084FF" />} 
            label="Home & work locations" 
            sublabel="Quezon City, Makati" 
          />

          <Text style={[styles.sectionTitle, { marginTop: 24 }]}>PREFERENCES</Text>
          <MenuLink 
            icon={<Bell size={20} color="#0084FF" />} 
            label="Notification settings" 
            sublabel="Alerts, frequency, channels" 
          />
          <MenuLink 
            icon={<Eye size={20} color="#0084FF" />} 
            label="Appearance & accessibility" 
            sublabel="Theme, font size" 
          />
        </View>

        {/* Sign Out Button */}
        <TouchableOpacity style={styles.signOutButton}>
          <LogOut size={18} color="#ef4444" />
          <Text style={styles.signOutText}>Sign out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const MenuLink = ({ icon, label, sublabel }: any) => (
  <TouchableOpacity style={styles.menuItem}>
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

const styles = StyleSheet.create({
  safeArea: { 
    flex: 1, 
    backgroundColor: '#fff' 
  },
  profileHeader: { padding: 20 },
  headerTop: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    borderBottomWidth: 1, 
    borderBottomColor: '#E5E7EB', 
    paddingBottom: 15, 
    marginHorizontal: -20 
  },
  headerTitle: { 
    fontSize: 24, 
    fontWeight: 'bold', 
    marginHorizontal: 20, 
    color: '#111827' 
  },
  editIconButton: { 
    padding: 5, 
    borderRadius: 8, 
    marginHorizontal: 20, 
    backgroundColor: '#F3F4F6' },
  
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
    alignItems: 'center',
    position: 'relative'
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
    fontWeight: '500', 
    marginLeft: 4 
  },
  statsRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
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
    color: '#0084FF' },
  statLabel: { 
    fontSize: 12, 
    color: '#6B7280', 
    marginTop: 2 
  },
  statDivider: { 
    width: 1, 
    height: '80%', 
    backgroundColor: '#E5E7EB', 
    alignSelf: 'center' 
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
  menuItem: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'space-between', 
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F9FAFB'
  },
  menuLeft: { 
    flexDirection: 'row', 
    alignItems: 'center' 
  },
  iconCircle: { marginRight: 16 },
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
    alignItems: 'center', 
    justifyContent: 'center', 
    marginHorizontal: 20, 
    marginVertical: 40,
    padding: 16, 
    borderRadius: 12, 
    backgroundColor: '#FFF1F2'
  },
  signOutText: { 
    color: '#EF4444', 
    fontWeight: 'bold', 
    marginLeft: 8 }
});