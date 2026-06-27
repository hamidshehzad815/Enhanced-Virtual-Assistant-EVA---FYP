import React, { createContext, useContext, useState, useEffect } from 'react';
import apiRequest from '../services/api';
import { useAuth } from './AuthContext';
import { useCalendar } from './CalendarContext';

const ChatContext = createContext(null);

export const ChatProvider = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  const { fetchDashboard } = useCalendar();
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [isEvaTyping, setIsEvaTyping] = useState(false);
  const [conversations, setConversations] = useState([
    {
      id: '1',
      title: 'NLP Exam Planning',
      lastMessage: 'Added exam for Monday 5pm',
      timeAgo: '20 min ago'
    },
    {
      id: '2',
      title: 'Python Roadmap',
      lastMessage: 'Learning plan ready — 5 topics',
      timeAgo: '2 hr ago'
    },
    {
      id: '3',
      title: 'Weekly Schedule',
      lastMessage: 'All classes added to calendar',
      timeAgo: '5 hr ago'
    }
  ]);

  // Load mock messages initially to preserve visual aesthetic
  const loadMockMessages = () => {
    setMessages([
      {
        id: '1',
        text: 'Hi there!',
        isEva: false,
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000)
      },
      {
        id: '2',
        text: 'Hello! How can I help you today? Ask me to schedule a task or make a study roadmap.',
        isEva: true,
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000 + 60 * 1000)
      }
    ]);
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadMockMessages();
      // Try to create/get a session ID
      getOrCreateSession();
    } else {
      setMessages([]);
      setSessionId(null);
    }
  }, [isAuthenticated]);

  const getOrCreateSession = async () => {
    let activeSession = localStorage.getItem('chat_session_id');
    if (activeSession) {
      setSessionId(activeSession);
      return activeSession;
    }
    
    try {
      const response = await apiRequest('/api/chat/session', {
        method: 'POST',
        body: JSON.stringify({ title: 'Workspace Chat' })
      });
      
      const newSessionId = response.data?.session_id || response.data?.session?._id || response.session_id;
      if (newSessionId) {
        localStorage.setItem('chat_session_id', newSessionId);
        setSessionId(newSessionId);
        return newSessionId;
      }
    } catch (err) {
      console.error('Failed to create chat session:', err);
    }
    return null;
  };

  const sendMessage = async (text, type = 'text') => {
    if (!text.trim()) return;
    
    const userMsg = {
      id: Date.now().toString(),
      text: text.trim(),
      isEva: false,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMsg]);
    setIsEvaTyping(true);
    
    try {
      // Ensure we have a session
      let activeSession = sessionId;
      if (!activeSession) {
        activeSession = await getOrCreateSession();
      }
      
      if (!activeSession) {
        throw new Error('Could not establish chat session');
      }

      const response = await apiRequest('/api/chat/process', {
        method: 'POST',
        body: JSON.stringify({
          message: text.trim(),
          session_id: activeSession,
          input_type: type
        })
      });

      const replyMsg = {
        id: (Date.now() + 1).toString(),
        text: response.response_text || response.message || 'I processed your command.',
        isEva: true,
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, replyMsg]);
      
      // If a task or goal was created, sync the dashboard data
      if (response.intent && response.intent !== 'general') {
        fetchDashboard();
      }
      
    } catch (err) {
      console.error('Failed to send message to AI:', err);
      const errMsg = {
        id: (Date.now() + 1).toString(),
        text: `Error: ${err.message || 'Could not communicate with AI server.'}`,
        isEva: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsEvaTyping(false);
    }
  };

  const clearChat = () => {
    loadMockMessages();
  };

  return (
    <ChatContext.Provider value={{
      messages,
      isEvaTyping,
      conversations,
      sessionId,
      sendMessage,
      clearChat
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => useContext(ChatContext);
