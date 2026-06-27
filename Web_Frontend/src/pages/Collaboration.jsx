import React, { useState, useEffect } from 'react';
import { Search, UserPlus, UserMinus, ShieldAlert, Check, X, ShieldCheck, Quote, Edit2, Users, Compass, Ban } from 'lucide-react';
import apiRequest from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './Collaboration.css';

export const Collaboration = () => {
  const { user } = useAuth();
  
  const [activeTab, setActiveTab] = useState('friends');
  
  const [friendsList, setFriendsList] = useState([]);
  const [incomingRequests, setIncomingRequests] = useState([]);
  const [outgoingRequests, setOutgoingRequests] = useState([]);
  const [blockedUsers, setBlockedUsers] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  
  const [quote, setQuote] = useState(() => {
    return localStorage.getItem('eva_study_quote') || '"Study hard, for the well is deep and our brains are shallow."';
  });
  const [isEditingQuote, setIsEditingQuote] = useState(false);
  const [tempQuote, setTempQuote] = useState('');

  const FALLBACK_FRIENDS = [
    { friendship_id: 'f1', friend: { _id: 'u2', name: 'Zara Khan', username: 'zara_k', initials: 'ZK', color: '#F59E0B' }, since: '1h' },
    { friendship_id: 'f2', friend: { _id: 'u3', name: 'Bilal Mir', username: 'bilal_m', initials: 'BM', color: '#3B82F6' }, since: '3h' },
    { friendship_id: 'f3', friend: { _id: 'u4', name: 'Hina Farooq', username: 'hina_f', initials: 'HF', color: '#10B981' }, since: 'Yesterday' }
  ];

  const fetchFriends = async () => {
    try {
      const response = await apiRequest('/api/friends');
      if (response.status === 'success' && response.data?.friends) {
        setFriendsList(response.data.friends.map(f => ({
          ...f,
          friend: {
            ...f.friend,
            initials: getInitials(f.friend.name),
            color: getRandomColor(f.friend.username)
          }
        })));
      } else {
        setFriendsList(FALLBACK_FRIENDS);
      }
    } catch (err) {
      console.warn('Friends API error, using fallback data.', err);
      setFriendsList(FALLBACK_FRIENDS);
    }
  };

  const fetchRequests = async () => {
    try {
      const incomingRes = await apiRequest('/api/friends/requests?type=incoming');
      if (incomingRes.status === 'success' && incomingRes.data?.requests) {
        setIncomingRequests(incomingRes.data.requests);
      }
      const outgoingRes = await apiRequest('/api/friends/requests?type=outgoing');
      if (outgoingRes.status === 'success' && outgoingRes.data?.requests) {
        setOutgoingRequests(outgoingRes.data.requests);
      }
    } catch (err) {
      console.error('Failed to fetch requests:', err);
    }
  };

  const fetchBlocked = async () => {
    try {
      const response = await apiRequest('/api/friends/blocked');
      if (response.status === 'success' && response.data?.blocked) {
        setBlockedUsers(response.data.blocked);
      }
    } catch (err) {
      console.error('Failed to fetch blocked users:', err);
    }
  };

  useEffect(() => {
    fetchFriends();
    fetchRequests();
    fetchBlocked();
  }, []);

  const getInitials = (name) => {
    if (!name) return 'UN';
    const parts = name.split(' ');
    if (parts.length > 1) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  const getRandomColor = (username) => {
    const colors = ['#F59E0B', '#3B82F6', '#10B981', '#EC4899', '#8B5CF6', '#14B8A6', '#6366F1'];
    let hash = 0;
    for (let i = 0; i < (username || '').length; i++) {
      hash = (username || '').charCodeAt(i) + ((hash << 5) - hash);
    }
    const idx = Math.abs(hash % colors.length);
    return colors[idx];
  };

  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    if (searchQuery.trim().length < 2) {
      setSearchError('Search query must be at least 2 characters');
      return;
    }
    setSearchError('');
    setIsSearching(true);
    try {
      const response = await apiRequest(`/api/friends/search?q=${encodeURIComponent(searchQuery)}`);
      if (response.status === 'success' && response.data?.users) {
        setSearchResults(response.data.users);
      } else {
        setSearchResults([]);
      }
    } catch (err) {
      console.error('Search error:', err);
      setSearchError('Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const sendRequest = async (username) => {
    try {
      const response = await apiRequest('/api/friends/request', {
        method: 'POST',
        body: JSON.stringify({ username })
      });
      if (response.status === 'success') {
        alert('Friend request sent!');
        fetchRequests();
        setSearchResults(prev => prev.map(u => u.username === username ? { ...u, relationship_status: 'pending' } : u));
      }
    } catch (err) {
      alert(err.message || 'Failed to send request');
    }
  };

  const respondRequest = async (id, action) => {
    try {
      const response = await apiRequest(`/api/friends/${id}/respond`, {
        method: 'PATCH',
        body: JSON.stringify({ action })
      });
      if (response.status === 'success') {
        fetchRequests();
        fetchFriends();
      }
    } catch (err) {
      alert(err.message || 'Failed to respond to request');
    }
  };

  const handleUnfriend = async (id) => {
    if (!window.confirm('Are you sure you want to unfriend this user?')) return;
    try {
      const response = await apiRequest(`/api/friends/${id}`, {
        method: 'DELETE'
      });
      if (response.status === 'success') {
        fetchFriends();
      }
    } catch (err) {
      alert(err.message || 'Failed to unfriend');
    }
  };

  const handleBlockUser = async (userId) => {
    if (!window.confirm('Are you sure you want to block this user?')) return;
    try {
      const response = await apiRequest(`/api/friends/block/${userId}`, {
        method: 'POST'
      });
      if (response.status === 'success') {
        fetchFriends();
        fetchBlocked();
        fetchRequests();
      }
    } catch (err) {
      alert(err.message || 'Failed to block user');
    }
  };

  const handleUnblockUser = async (userId) => {
    try {
      const response = await apiRequest(`/api/friends/unblock/${userId}`, {
        method: 'POST'
      });
      if (response.status === 'success') {
        fetchBlocked();
      }
    } catch (err) {
      alert(err.message || 'Failed to unblock user');
    }
  };

  const startEditingQuote = () => {
    setTempQuote(quote.replace(/"/g, ''));
    setIsEditingQuote(true);
  };

  const saveQuote = () => {
    if (tempQuote.trim()) {
      const formatted = `"${tempQuote.trim()}"`;
      setQuote(formatted);
      localStorage.setItem('eva_study_quote', formatted);
    }
    setIsEditingQuote(false);
  };

  return (
    <div className="collaboration-workspace animate-fade-in">
      
      {/* Left Column pane: Profile Details & Quote Box & Tab toggles */}
      <div className="collab-left-pane">
        <div className="collab-profile-card">
          <div className="profile-details-top">
            <div className="profile-avatar-big">
              {getInitials(user?.name || 'Areej')}
            </div>
            <div className="profile-names">
              <h4>{user?.name || 'Areej'}</h4>
              <p>@{user?.username || 'username'}</p>
            </div>
          </div>

          {/* Quote of the Day container */}
          <div className="quote-saas-box" onClick={startEditingQuote}>
            <div className="quote-header-row">
              <span className="quote-lbl"><Quote size={12} style={{ display: 'inline', marginRight: '4px' }} /> Quote of the Day</span>
              <Edit2 size={12} className="quote-edit-pencil" />
            </div>
            {isEditingQuote ? (
              <div className="quote-editor-saas" onClick={(e) => e.stopPropagation()}>
                <textarea
                  value={tempQuote}
                  onChange={(e) => setTempQuote(e.target.value)}
                  maxLength={150}
                  className="quote-textarea-saas font-body"
                  autoFocus
                />
                <div className="quote-editor-buttons">
                  <button className="q-btn-saas cancel" onClick={() => setIsEditingQuote(false)}>Cancel</button>
                  <button className="q-btn-saas save" onClick={saveQuote}>Save</button>
                </div>
              </div>
            ) : (
              <p className="quote-text-val font-body">{quote}</p>
            )}
          </div>
        </div>

        {/* Vertical category selectors */}
        <div className="collab-navigation-vertical">
          <button 
            className={`collab-vertical-tab-btn ${activeTab === 'friends' ? 'active' : ''}`}
            onClick={() => setActiveTab('friends')}
          >
            <Users size={16} />
            <span>My Buddies</span>
            <span className="count-badge">{friendsList.length}</span>
          </button>
          
          <button 
            className={`collab-vertical-tab-btn ${activeTab === 'requests' ? 'active' : ''}`}
            onClick={() => { setActiveTab('requests'); fetchRequests(); }}
          >
            <Compass size={16} />
            <span>Pending Invites</span>
            <span className="count-badge">{incomingRequests.length + outgoingRequests.length}</span>
          </button>
          
          <button 
            className={`collab-vertical-tab-btn ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => setActiveTab('search')}
          >
            <UserPlus size={16} />
            <span>Add Buddies</span>
          </button>
          
          <button 
            className={`collab-vertical-tab-btn ${activeTab === 'blocked' ? 'active' : ''}`}
            onClick={() => { setActiveTab('blocked'); fetchBlocked(); }}
          >
            <Ban size={16} />
            <span>Blocked Users</span>
          </button>
        </div>
      </div>

      {/* Center/Right Main Directory pane */}
      <div className="collab-center-pane">
        
        {/* TAB 1: FRIENDS DIRECTORY */}
        {activeTab === 'friends' && (
          <div className="directory-panel-saas">
            <h2 className="directory-title font-logo">Buddies Directory</h2>
            {friendsList.length > 0 ? (
              <div className="bento-buddies-grid">
                {friendsList.map((item) => (
                  <div key={item.friendship_id || item.friend?._id} className="buddy-bento-card">
                    <div className="buddy-avatar-wrapper" style={{ '--avatar-color': item.friend?.color || '#3B82F6' }}>
                      {item.friend?.initials || getInitials(item.friend?.name)}
                    </div>
                    <h4 className="buddy-name font-logo">{item.friend?.name}</h4>
                    <span className="buddy-username">@{item.friend?.username}</span>
                    <span className="buddy-since">Connected recently</span>

                    <div className="buddy-actions-row">
                      <button 
                        className="buddy-btn block" 
                        onClick={() => handleBlockUser(item.friend?._id)}
                        title="Block User"
                      >
                        <ShieldAlert size={14} /> Block
                      </button>
                      <button 
                        className="buddy-btn remove" 
                        onClick={() => handleUnfriend(item.friendship_id)}
                        title="Remove Friend"
                      >
                        <UserMinus size={14} /> Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="collab-empty-state-saas">
                <p>No study buddies added yet.</p>
                <button className="goto-find-btn" onClick={() => setActiveTab('search')}>
                  Find people on EVA
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: PENDING INVITES */}
        {activeTab === 'requests' && (
          <div className="directory-panel-saas">
            <h2 className="directory-title font-logo">Pending Invites</h2>
            
            <div className="requests-columns-saas">
              {/* Incoming Section */}
              <div className="requests-col-section">
                <span className="requests-section-lbl">Incoming Requests</span>
                {incomingRequests.length > 0 ? (
                  <div className="requests-list-saas">
                    {incomingRequests.map((req) => (
                      <div key={req._id} className="collab-user-tile-saas">
                        <div className="tile-avatar font-body" style={{ backgroundColor: '#7F77DD' }}>
                          {getInitials(req.requester?.name)}
                        </div>
                        <div className="tile-text">
                          <h4 className="tile-display-name">{req.requester?.name}</h4>
                          <span className="tile-username">@{req.requester?.username}</span>
                        </div>
                        <div className="tile-actions">
                          <button 
                            className="tile-action-btn accept-btn"
                            onClick={() => respondRequest(req._id, 'accept')}
                            title="Accept Request"
                          >
                            <Check size={16} />
                          </button>
                          <button 
                            className="tile-action-btn reject-btn"
                            onClick={() => respondRequest(req._id, 'reject')}
                            title="Reject Request"
                          >
                            <X size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-requests-msg-saas">No incoming requests.</p>
                )}
              </div>

              {/* Outgoing Section */}
              <div className="requests-col-section">
                <span className="requests-section-lbl">Sent Requests</span>
                {outgoingRequests.length > 0 ? (
                  <div className="requests-list-saas">
                    {outgoingRequests.map((req) => (
                      <div key={req._id} className="collab-user-tile-saas">
                        <div className="tile-avatar font-body" style={{ backgroundColor: '#A0AEC0' }}>
                          {getInitials(req.recipient?.name)}
                        </div>
                        <div className="tile-text">
                          <h4 className="tile-display-name">{req.recipient?.name}</h4>
                          <span className="tile-username">@{req.recipient?.username}</span>
                        </div>
                        <div className="tile-status-badge-saas pending">
                          Pending
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-requests-msg-saas">No pending sent requests.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: SEARCH ADD FRIENDS */}
        {activeTab === 'search' && (
          <div className="directory-panel-saas">
            <h2 className="directory-title font-logo">Find Buddies</h2>
            
            <form onSubmit={handleSearchSubmit} className="collab-search-form-saas">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search friend by username..."
                className="collab-search-input-saas font-body"
              />
              <button type="submit" className="collab-search-submit-saas">
                <Search size={18} />
              </button>
            </form>

            {searchError && <p className="search-error-msg-saas">{searchError}</p>}
            {isSearching && <p className="search-loading-msg-saas">Searching directories...</p>}

            <div className="search-results-list-saas">
              {searchResults.length > 0 ? (
                searchResults.map((u) => (
                  <div key={u._id} className="collab-user-tile-saas">
                    <div className="tile-avatar font-body" style={{ backgroundColor: getRandomColor(u.username) }}>
                      {getInitials(u.name)}
                    </div>
                    <div className="tile-text">
                      <h4 className="tile-display-name">{u.name}</h4>
                      <span className="tile-username">@{u.username}</span>
                    </div>
                    <div className="tile-actions">
                      {u.relationship_status === 'none' && (
                        <button 
                          className="tile-action-btn add-btn"
                          onClick={() => sendRequest(u.username)}
                          title="Add Friend"
                        >
                          <UserPlus size={16} />
                        </button>
                      )}
                      {u.relationship_status === 'pending' && (
                        <span className="tile-status-badge-saas pending">Pending</span>
                      )}
                      {u.relationship_status === 'accepted' && (
                        <span className="tile-status-badge-saas friend"><ShieldCheck size={14} style={{ display: 'inline', marginRight: '4px' }} />Buddy</span>
                      )}
                      {u.relationship_status === 'blocked' && (
                        <span className="tile-status-badge-saas blocked">Blocked</span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                !isSearching && searchQuery.length >= 2 && <p className="no-results-msg-saas">No users found matching "{searchQuery}"</p>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: BLOCKED USERS */}
        {activeTab === 'blocked' && (
          <div className="directory-panel-saas">
            <h2 className="directory-title font-logo">Blocked Users</h2>
            {blockedUsers.length > 0 ? (
              <div className="requests-list-saas">
                {blockedUsers.map((item) => (
                  <div key={item.friendship_id || item.user?._id} className="collab-user-tile-saas">
                    <div className="tile-avatar font-body" style={{ backgroundColor: '#2D3748' }}>
                      {getInitials(item.user?.name)}
                    </div>
                    <div className="tile-text">
                      <h4 className="tile-display-name">{item.user?.name}</h4>
                      <span className="tile-username">@{item.user?.username}</span>
                    </div>
                    <div className="tile-actions">
                      <button 
                        className="unblock-action-btn-saas"
                        onClick={() => handleUnblockUser(item.user?._id)}
                      >
                        Unblock
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="collab-empty-state-saas">
                <p>No blocked users.</p>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
};

export default Collaboration;
