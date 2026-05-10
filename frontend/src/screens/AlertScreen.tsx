import React, { useState } from 'react';
import { useIsFocused } from '@react-navigation/native';
import { 
  View, 
  Text, 
  StyleSheet, 
  ScrollView, 
  SafeAreaView, 
  TouchableOpacity,
  StatusBar,
  Alert
} from 'react-native';
import { CarFront, Waves, Pickaxe, Info, Clock } from 'lucide-react-native';

const INITIAL_DATA = [
  {
    id: '1',
    type: 'Accident',
    location: 'EDSA Ortigas NB',
    date: new Date(), 
    time: '4 min ago',
    city: 'Pasig City',
    description: 'Multi-vehicle collision blocking 2 lanes. Heavy backup extending towards Shaw Blvd interchange.',
    status: 'High priority',
    statusColor: '#ef4444',
    isRead: false,
    icon: <CarFront size={24} color="#ef4444" strokeWidth={2.5} />
  },
  {
    id: '2',
    type: 'Flooding',
    location: 'España Blvd',
    date: new Date(), 
    time: '51 min ago',
    city: 'Manila',
    description: 'Unverified: report of flooding near UST gate. Awaiting corroboration from sources.',
    status: 'Pending review',
    statusColor: '#f59e0b',
    isRead: false,
    icon: <Waves size={24} color="#3b82f6" strokeWidth={2.5} />
  },
  {
    id: '3',
    type: 'Road Works',
    location: 'C5 near BGC',
    date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), 
    time: '2 days ago',
    city: 'Taguig',
    description: 'Lane closure for utility works. Single lane flowing, 15-20 min delays.',
    status: 'Verified',
    statusColor: '#10b981',
    isRead: false,
    icon: <Pickaxe size={24} color="#f59e0b" strokeWidth={2.5} />
  },
  {
    id: '4',
    type: 'Protest',
    location: 'Mendiola St',
    date: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000), 
    time: '10 days ago',
    city: 'Manila',
    description: 'Road closure due to rally. Expect heavy rerouting.',
    status: 'Verified',
    statusColor: '#10b981',
    isRead: false,
    icon: <Pickaxe size={24} color="#f59e0b" strokeWidth={2.5} />
  }
];

export default function AlertScreen() {
  const isFocused = useIsFocused();
  const [alerts, setAlerts] = useState(INITIAL_DATA);
  const [activeTab, setActiveTab] = useState('All');

  const handleMarkAllRead = () => {
    const updatedAlerts = alerts.map(alert => ({ ...alert, isRead: true }));
    setAlerts(updatedAlerts);
    Alert.alert("Success", "All alerts marked as read.");
  };

  const isToday = (date: Date) => date.toDateString() === new Date().toDateString();

  const isPast7Days = (date: Date) => {
    const today = new Date();
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(today.getDate() - 7);
    return date < today && date >= sevenDaysAgo && !isToday(date);
  };

  const todayAlerts = alerts.filter(item => isToday(item.date));
  const earlierAlerts = alerts.filter(item => isPast7Days(item.date));

  const filteredData = activeTab === 'All' 
    ? alerts 
    : activeTab === 'Today' ? todayAlerts : earlierAlerts;

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0084FF" />
      {isFocused && <StatusBar barStyle="light-content" backgroundColor="#0084FF" />}
      
      <View style={styles.topHeaderBackground}>
        <SafeAreaView>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Alerts</Text>
            <TouchableOpacity onPress={handleMarkAllRead}>
              <Text style={styles.markReadText}>Mark all as read</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </View>

      {/* Tabs Section */}
      <View style={styles.tabContainer}>
        {['All', 'Today', 'Earlier'].map((tab) => (
          <TouchableOpacity 
            key={tab} 
            onPress={() => setActiveTab(tab)}
            style={[styles.tab, activeTab === tab && styles.activeTab]}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.activeTabText]}>{tab}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.alertList} contentContainerStyle={styles.scrollContent}>
        {activeTab === 'Today' && (
          <View style={[styles.banner, styles.blueBanner]}>
            <Info size={18} color="#0056b3" style={{ marginRight: 8 }} />
            <Text style={styles.blueBannerText}>
              {todayAlerts.length} {todayAlerts.length === 1 ? 'alert' : 'alerts'} within your area today
            </Text>
          </View>
        )}
        {activeTab === 'Earlier' && (
          <View style={[styles.banner, styles.grayBanner]}>
            <Clock size={18} color="#4b5563" style={{ marginRight: 8 }} />
            <Text style={styles.grayBannerText}>Showing alerts from the past 7 days</Text>
          </View>
        )}

        <Text style={styles.sectionHeader}>
          {activeTab === 'All' ? 'Recent Alerts' : activeTab}
        </Text>
        
        {filteredData.map((item) => (
          <View key={item.id} style={[styles.alertCard, item.isRead && { opacity: 0.6, borderColor: '#ccc' }]}>
            <View style={styles.cardHeader}>
              <View style={styles.iconWrapper}>{item.icon}</View>
              <View style={styles.headerText}>
                <Text style={styles.alertType}>{item.type} — {item.location}</Text>
                <Text style={styles.alertMeta}>{item.time} • {item.city}</Text>
              </View>
            </View>
            <Text style={styles.description}>{item.description}</Text>
            <View style={styles.badgeContainer}>
              <View style={[styles.statusBadge, { backgroundColor: item.statusColor + '15', borderColor: item.statusColor }]}>
                <Text style={[styles.statusText, { color: item.statusColor }]}>{item.status}</Text>
              </View>
            </View>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#fff' 
  },
  topHeaderBackground: { 
    backgroundColor: '#0084FF', 
  },
  header: { 
    height: 60, 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'space-between',
    paddingHorizontal: 20,
  },
  headerTitle: { 
    fontSize: 20, 
    fontWeight: 'bold', 
    color: '#fff' 
  },
  markReadText: { 
    color: '#fff', 
    fontSize: 14, 
    fontWeight: '500' 
  },
  tabContainer: { 
    flexDirection: 'row',  
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb', 
    backgroundColor: '#fff',
  },
  tab: { 
    flex: 1, 
    paddingVertical: 15, 
    alignItems: 'center' 
  },
  activeTab: { 
    borderBottomWidth: 3, 
    borderBottomColor: '#0084FF' 
  },
  tabText: { 
    fontSize: 16, 
    color: '#6b7280' 
  },
  activeTabText: { 
    color: '#0084FF', 
    fontWeight: 'bold' 
  },
  alertList: { flex: 1 },
  scrollContent: { padding: 16 },
  sectionHeader: { 
    fontSize: 12, 
    fontWeight: 'bold', 
    color: '#9ca3af', 
    marginBottom: 12, 
    textTransform: 'uppercase' 
  },
  alertCard: { 
    backgroundColor: '#fff', 
    borderRadius: 14, 
    padding: 16, 
    marginBottom: 16, 
    borderWidth: 1.5, 
    borderColor: '#000' 
  },
  cardHeader: { 
    flexDirection: 'row', 
    marginBottom: 10 
  },
  iconWrapper: { marginRight: 12 },
  headerText: { flex: 1 },
  alertType: { 
    fontSize: 14, 
    fontWeight: 'bold', 
    color: '#000' 
  },
  alertMeta: { 
    fontSize: 11, 
    color: '#6b7280' 
  },
  description: { 
    fontSize: 12, 
    color: '#1f2937', 
    lineHeight: 18, 
    marginBottom: 14 
  },
  badgeContainer: { alignItems: 'flex-end' },
  statusBadge: { 
    paddingHorizontal: 10, 
    paddingVertical: 3, 
    borderRadius: 20, 
    borderWidth: 1 
  },
  statusText: { 
    fontSize: 9, 
    fontWeight: 'bold', 
    textTransform: 'uppercase' 
  },
  banner: { 
    padding: 12, 
    borderRadius: 8, 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginBottom: 20 
  },
  blueBanner: { backgroundColor: '#e3f2fd' },
  grayBanner: { backgroundColor: '#f3f4f6' },
  blueBannerText: { 
    fontSize: 13, 
    color: '#0056b3', 
    fontWeight: '500' 
  },
  grayBannerText: { 
    fontSize: 13, 
    color: '#4b5563', 
    fontWeight: '500' 
  },
});