import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ScrollView, 
  SafeAreaView 
} from 'react-native';
import { 
  ThumbsUp, 
  ThumbsDown, 
  CarFront,
  Construction,  
  Waves   
} from 'lucide-react-native';

const FEED_DATA = [
  {
    id: '1',
    type: 'Accident',
    location: 'EDSA Ortigas NB',
    time: 'Submitted 4 min ago',
    user: 'Pasig City',
    description: 'Multi-vehicle collision blocking 2 lanes. Heavy backup extending towards Shaw Blvd interchange.',
    upvotes: 47,
    downvotes: 3,
    status: 'RoBERTa Verified 94%',
    statusColor: '#10b981',
    icon: <CarFront size={24} color="#ef4444" />
  },
  {
    id: '2',
    type: 'Road works',
    location: 'C5 near BGC',
    time: 'Submitted 22 min ago',
    user: 'Taguig',
    description: 'Lane closure for utility works. Single lane moving slowly, expect 15-20 min delays.',
    upvotes: 21,
    downvotes: 8,
    status: 'DistilBERT Scored 78%',
    statusColor: '#f59e0b',
    icon: <Construction size={24} color="#f59e0b" />
  },
  {
    id: '3',
    type: 'Flooding',
    location: 'España Blvd',
    time: 'Submitted 51 min ago',
    user: 'Manila',
    description: 'Unverified: report of flooding near UST gate. Awaiting corroboration from additional sources.',
    upvotes: 4,
    downvotes: 19,
    status: 'Pending Review 41%',
    statusColor: '#ef4444',
    icon: <Waves size={24} color="#3b82f6" /> 
  }
];

export default function FeedScreen({ navigation }: any) {
  const [activeTab, setActiveTab] = useState('All');

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Event Reports</Text>
        <TouchableOpacity style={styles.filterIcon}>
          <Text style={styles.filterText}>Filter</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.tabContainer}>
        {['All', 'Verified', 'Nearby'].map((tab) => (
          <TouchableOpacity 
            key={tab} 
            onPress={() => setActiveTab(tab)}
            style={[styles.tab, activeTab === tab && styles.activeTab]}
          >
            <Text style={[styles.tabText, activeTab === tab && styles.activeTabText]}>{tab}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.feedList} contentContainerStyle={styles.scrollContent}>
        {FEED_DATA.map((item) => (
          <View key={item.id} style={styles.reportCard}>
            <View style={styles.cardHeader}>
              <View style={styles.headerLeft}>
                <Text style={styles.reportType}>{item.type} — {item.location}</Text>
                <Text style={styles.reportMeta}>{item.time} • {item.user}</Text>
              </View>
              {/* Dito lalabas ang specific icon */}
              <View style={styles.typeIcon}>{item.icon}</View>
            </View>
            
            <Text style={styles.description}>{item.description}</Text>
            
            <View style={styles.cardFooter}>
              <View style={styles.voteContainer}>
                <TouchableOpacity style={styles.voteBtn}>
                  <View style={styles.voteBox}><ThumbsUp size={14} color="#1f2937" /></View>
                  <Text style={styles.voteCount}>{item.upvotes}</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.voteBtn}>
                  <View style={styles.voteBox}><ThumbsDown size={14} color="#1f2937" /></View>
                  <Text style={styles.voteCount}>{item.downvotes}</Text>
                </TouchableOpacity>
              </View>
              
              <Text style={[styles.statusText, { color: item.statusColor }]}>{item.status}</Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { 
    flex: 1, 
    backgroundColor: '#fff' 
  },
  header: { 
    height: 60, 
    backgroundColor: '#FBC02D', 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'center' 
  },
  backIcon: { 
    position: 'absolute', 
    left: 15 
  },
  filterIcon: { 
    position: 'absolute', 
    right: 15 
  },
  filterText: { 
    color: '#3b82f6', 
    fontSize: 14, 
    fontWeight: '500' 
  },
  headerTitle: { 
    fontSize: 18, 
    fontWeight: 'bold', 
    color: '#1f2937' 
  },
  tabContainer: { 
    flexDirection: 'row', 
    borderBottomWidth: 1, 
    borderBottomColor: '#e5e7eb' 
  },
  tab: { 
    flex: 1, 
    paddingVertical: 15, 
    alignItems: 'center' 
  },
  activeTab: { 
    borderBottomWidth: 2, 
    borderBottomColor: '#3b82f6' 
  },
  tabText: { 
    fontSize: 16, 
    color: '#000' 
  },
  activeTabText: { 
    color: '#3b82f6', 
    fontWeight: 'bold' 
  },
  feedList: { flex: 1 },
  scrollContent: { padding: 16 },
  reportCard: { 
    backgroundColor: '#fff', 
    borderRadius: 12, 
    padding: 16, 
    marginBottom: 16, 
    borderWidth: 1.5, 
    borderColor: '#000' // Wireframe border style
  },
  cardHeader: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    marginBottom: 12 
  },
  headerLeft: { flex: 1 },
  reportType: { 
    fontSize: 15, 
    fontWeight: 'bold', 
    color: '#000' 
  },
  reportMeta: { 
    fontSize: 11, 
    color: '#6b7280', 
    marginTop: 2 
  },
  typeIcon: { marginLeft: 10 },
  description: { 
    fontSize: 13, 
    color: '#000', 
    lineHeight: 18, 
    marginBottom: 16 
  },
  cardFooter: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center' 
  },
  voteContainer: { flexDirection: 'row' },
  voteBtn: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginRight: 12 
  },
  voteBox: { 
    borderWidth: 1, 
    borderColor: '#000', 
    padding: 4, 
    borderRadius: 4, 
    marginRight: 6 
  },
  voteCount: { 
    fontSize: 13, 
    color: '#000', 
    fontWeight: '500' 
  },
  statusText: { 
    fontSize: 11, 
    fontWeight: 'bold', 
    textTransform: 'uppercase' 
  }
});