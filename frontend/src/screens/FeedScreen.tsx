import React, { useState, useMemo } from 'react';
import { useIsFocused } from '@react-navigation/native';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ScrollView, 
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { ThumbsUp, ThumbsDown, CarFront,Construction, Waves, AlertTriangle } from 'lucide-react-native';

// Sample data only
// Replace with actual API data fetching and state management logic when integrating with backend
const INITIAL_FEED = [
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
    isVerified: true,
    isNearby: true,
    // User-specific vote tracking state
    userVote: null as 'up' | 'down' | null 
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
    isVerified: true,
    isNearby: false,
    userVote: null as 'up' | 'down' | null
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
    isVerified: false,
    isNearby: true,
    userVote: null as 'up' | 'down' | null
  }
];

export default function FeedScreen() {
  const isFocused = useIsFocused();
  const [activeTab, setActiveTab] = useState('All');
  const [feedData, setFeedData] = useState(INITIAL_FEED);

  const filteredFeed = useMemo(() => {
    return feedData.filter(item => {
      if (activeTab === 'Verified') return item.isVerified;
      if (activeTab === 'Nearby') return item.isNearby;
      return true;
    });
  }, [activeTab, feedData]);

  // Exclusive single-choice tracking handler integration block
  const handleVote = (id: string, voteType: 'up' | 'down') => {
    const updatedFeed = feedData.map(item => {
      if (item.id === id) {
        let newUpvotes = item.upvotes;
        let newDownvotes = item.downvotes;
        let newVoteState: 'up' | 'down' | null = voteType;

        if (item.userVote === voteType) {
          if (voteType === 'up') newUpvotes--;
          else newDownvotes--;
          newVoteState = null;
        } else {
          if (item.userVote === 'up') newUpvotes--;
          if (item.userVote === 'down') newDownvotes--;

          if (voteType === 'up') newUpvotes++;
          if (voteType === 'down') newDownvotes++;
        }

        return {
          ...item,
          upvotes: newUpvotes,
          downvotes: newDownvotes,
          userVote: newVoteState
        };
      }
      return item;
    });
    setFeedData(updatedFeed);
  };

  const renderTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'accident': return <CarFront size={24} color="#ef4444" />;
      case 'road works': return <Construction size={24} color="#f59e0b" />;
      case 'flooding': return <Waves size={24} color="#3b82f6" />;
      default: return <AlertTriangle size={24} color="#6b7280" />;
    }
  };

  return (
    <View style={styles.container}>
      {isFocused && <StatusBar barStyle="dark-content" backgroundColor="#FBC02D" />}

      <View style={styles.topHeaderBackground}>
        <SafeAreaView>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Event Reports</Text>
          </View>
        </SafeAreaView>
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
        {filteredFeed.map((item) => (
          <View key={item.id} style={styles.reportCard}>
            <View style={styles.cardHeader}>
              <View style={styles.headerLeft}>
                <Text style={styles.reportType}>{item.type} — {item.location}</Text>
                <Text style={styles.reportMeta}>{item.time} • {item.user}</Text>
              </View>
              <View style={styles.typeIcon}>{renderTypeIcon(item.type)}</View>
            </View>
            
            <Text style={styles.description}>{item.description}</Text>
            
            <View style={styles.cardFooter}>
              <View style={styles.voteContainer}>
                
                {/* UPVOTE NODE COMPONENT */}
                <TouchableOpacity style={styles.voteBtn} onPress={() => handleVote(item.id, 'up')}>
                  <View style={[styles.voteBox, item.userVote === 'up' && styles.activeUpvoteBox]}>
                    <ThumbsUp size={14} color={item.userVote === 'up' ? '#fff' : '#000'} />
                  </View>
                  <Text style={[styles.voteCount, item.userVote === 'up' && styles.activeUpvoteText]}>
                    {item.upvotes}
                  </Text>
                </TouchableOpacity>

                {/* DOWNVOTE NODE COMPONENT */}
                <TouchableOpacity style={styles.voteBtn} onPress={() => handleVote(item.id, 'down')}>
                  <View style={[styles.voteBox, item.userVote === 'down' && styles.activeDownvoteBox]}>
                    <ThumbsDown size={14} color={item.userVote === 'down' ? '#fff' : '#000'} />
                  </View>
                  <Text style={[styles.voteCount, item.userVote === 'down' && styles.activeDownvoteText]}>
                    {item.downvotes}
                  </Text>
                </TouchableOpacity>

              </View>
              
              <Text style={[styles.statusText, { color: item.statusColor }]}>{item.status}</Text>
            </View>
          </View>
        ))}

        {filteredFeed.length === 0 && (
          <Text style={styles.emptyFeedText}>No event reports under this criteria yet.</Text>
        )}
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
    backgroundColor: '#FBC02D' 
  },
  header: { 
    height: 60, 
    flexDirection: 'row', 
    alignItems: 'center', 
    justifyContent: 'center', 
    paddingHorizontal: 15 
  },
  headerTitle: { 
    fontSize: 18, 
    fontWeight: 'bold', 
    color: '#1f2937' 
  },
  tabContainer: { 
    flexDirection: 'row', 
    borderBottomWidth: 1, 
    borderBottomColor: '#e5e7eb', 
    backgroundColor: '#fff' 
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
  feedList: { flex: 1 },
  scrollContent: { padding: 16 },
  reportCard: { 
    backgroundColor: '#fff', 
    borderRadius: 12, 
    padding: 16, 
    marginBottom: 16, 
    borderWidth: 1.5, 
    borderColor: '#000' 
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
    borderWidth: 1.5, 
    borderColor: '#000', 
    padding: 4, 
    borderRadius: 6, 
    marginRight: 6, 
    backgroundColor: '#fff' 
  },
  
  // Custom interactive tracking stylesheet layers
  activeUpvoteBox: { 
    backgroundColor: '#10b981', 
    borderColor: '#10b981' 
  },
  activeUpvoteText: { color: '#10b981' },
  activeDownvoteBox: { 
    backgroundColor: '#ef4444', 
    borderColor: '#ef4444' 
  },
  activeDownvoteText: { color: '#ef4444' },
  
  voteCount: { 
    fontSize: 13, 
    color: '#000', 
    fontWeight: 'bold' 
  },
  statusText: { 
    fontSize: 11, 
    fontWeight: 'bold', 
    textTransform: 'uppercase' 
  },
  emptyFeedText: { 
    textAlign: 'center', 
    color: '#9ca3af', 
    marginTop: 40, 
    fontSize: 14 
  }
});