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
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [isEvaTyping, setIsEvaTyping] = useState(false);
  const [conversations, setConversations] = useState([]);

  const CHAT_CONVERSATIONS_KEY = 'eva_chat_conversations';
  const getStoredConversations = () => {
    try {
      const raw = localStorage.getItem(CHAT_CONVERSATIONS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  };

  const saveStoredConversations = (items) => {
    try {
      localStorage.setItem(CHAT_CONVERSATIONS_KEY, JSON.stringify(items));
    } catch (err) {
      console.error('Unable to save chat conversations:', err);
    }
  };

  const getSessionMessages = (sessionId) => {
    try {
      const raw = localStorage.getItem(`eva_chat_messages_${sessionId}`);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  };

  const saveSessionMessages = (sessionId, items) => {
    try {
      localStorage.setItem(`eva_chat_messages_${sessionId}`, JSON.stringify(items));
    } catch (err) {
      console.error('Unable to save session messages:', err);
    }
  };

  const buildTitleFromMessage = (text) => {
    if (!text) return 'EVA Chat';
    return text.length > 26 ? `${text.slice(0, 24).trim()}...` : text;
  };

  const mapBackendSession = (session) => ({
    id: session.session_id || session.id || session._id,
    title: session.title || 'EVA Chat',
    lastMessage: session.last_message_preview || 'Continue the conversation',
    updated_at: session.last_message_at || session.updated_at || session.created_at,
  });

  const mapBackendMessages = (history = []) => history.map((item) => ({
    id: item.id || item._id || `${item.role}-${item.created_at || Date.now()}`,
    text: item.text || item.content || '',
    role: item.role || 'user',
    isEva: item.role === 'eva',
    timestamp: item.timestamp || item.created_at || new Date().toISOString(),
    input_type: item.input_type || 'text',
    intent: item.intent || null,
  }));

  const loadChatSessions = async () => {
    try {
      const response = await apiRequest('/api/chat/sessions');
      const sessions = response.data?.sessions || [];
      const mappedSessions = sessions.map(mapBackendSession);
      setConversations(mappedSessions);
      saveStoredConversations(mappedSessions);
      return mappedSessions;
    } catch (err) {
      console.warn('Could not load backend chat sessions, falling back to local history.', err);
      const stored = getStoredConversations();
      setConversations(stored);
      return stored;
    }
  };

  const loadSessionHistory = async (sessionId) => {
    if (!sessionId) return null;
    try {
      const response = await apiRequest(`/api/chat/sessions/${sessionId}/history`);
      const history = response.data?.messages || [];
      const mapped = mapBackendMessages(history);
      if (mapped.length > 0) {
        setMessages(mapped);
        saveSessionMessages(sessionId, mapped);
        return mapped;
      }
    } catch (err) {
      console.warn('Failed to load chat history from backend, using local cache.', err);
    }
    const storedMessages = getSessionMessages(sessionId);
    if (storedMessages && storedMessages.length > 0) {
      setMessages(storedMessages);
      return storedMessages;
    }
    loadMockMessages();
    return null;
  };

  const createChatSession = async (title = 'New Conversation') => {
    try {
      const response = await apiRequest('/api/chat/session', {
        method: 'POST',
        body: JSON.stringify({ title }),
      });
      const newSessionId = response.data?.session_id || response.data?.session?._id || response.session_id;
      if (newSessionId) {
        localStorage.setItem('chat_session_id', newSessionId);
        setSessionId(newSessionId);
        setSelectedSessionId(newSessionId);
        const nextConversations = [{ id: newSessionId, title, lastMessage: 'Start your chat with EVA', updated_at: new Date().toISOString() }, ...getStoredConversations().filter((item) => item.id !== newSessionId)];
        setConversations(nextConversations);
        saveStoredConversations(nextConversations);
        await loadChatSessions();
        return newSessionId;
      }
    } catch (err) {
      console.error('Failed to create chat session:', err);
    }
    return null;
  };

  const getOrCreateSession = async () => {
    let activeSession = selectedSessionId || localStorage.getItem('chat_session_id');
    const sessions = await loadChatSessions();
    if (activeSession && !sessions.find((item) => item.id === activeSession)) {
      activeSession = null;
      localStorage.removeItem('chat_session_id');
    }
    if (!activeSession && sessions.length > 0) {
      activeSession = sessions[0].id;
    }
    if (activeSession) {
      setSessionId(activeSession);
      setSelectedSessionId(activeSession);
      localStorage.setItem('chat_session_id', activeSession);
      await loadSessionHistory(activeSession);
      return activeSession;
    }
    return createChatSession();
  };

  const upsertConversation = (id, title, lastMessageText) => {
    if (!id) return;
    const existing = getStoredConversations();
    const now = new Date().toISOString();
    const updated = existing.filter((item) => item.id !== id);
    updated.unshift({
      id,
      title: title || `EVA Chat ${updated.length + 1}`,
      lastMessage: lastMessageText || 'Continue the conversation',
      updated_at: now,
    });
    setConversations(updated);
    saveStoredConversations(updated);
  };

  const loadConversation = (id) => {
    if (!id) return;
    const storedMessages = getSessionMessages(id);
    if (storedMessages && storedMessages.length > 0) {
      setMessages(storedMessages);
    } else {
      loadMockMessages();
    }
    setSessionId(id);
    setSelectedSessionId(id);
  };

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
    const initializeChat = async () => {
      if (!isAuthenticated) {
        setMessages([]);
        setSessionId(null);
        setConversations([]);
        setSelectedSessionId(null);
        return;
      }

      const sessions = await loadChatSessions();
      if (sessions.length > 0) {
        const savedId = localStorage.getItem('chat_session_id');
        const activeSession = sessions.find((item) => item.id === savedId)
          ? savedId
          : sessions[0].id;

        if (activeSession) {
          setSessionId(activeSession);
          setSelectedSessionId(activeSession);
          localStorage.setItem('chat_session_id', activeSession);
          await loadSessionHistory(activeSession);
          return;
        }
      }

      await createChatSession('Workspace Chat');
    };

    initializeChat();
  }, [isAuthenticated]);

  const selectConversation = async (id) => {
    if (!id) return;
    setSelectedSessionId(id);
    setSessionId(id);
    localStorage.setItem('chat_session_id', id);
    await loadSessionHistory(id);
  };

  const sendMessage = async (text, type = 'text') => {
    if (!text.trim()) return;
    
    const userMsg = {
      id: Date.now().toString(),
      text: text.trim(),
      role: 'user',
      isEva: false,
      timestamp: new Date().toISOString(),
    };
    
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    if (sessionId) saveSessionMessages(sessionId, nextMessages);
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

      let response;
      try {
        response = await apiRequest('/api/chat/process', {
          method: 'POST',
          body: JSON.stringify({
            message: text.trim(),
            session_id: activeSession,
            input_type: type
          })
        });
      } catch (err) {
        // If session was not found on server (stale local id), attempt to create a new session and retry once
        const msg = String(err.message || '').toLowerCase();
        if (err.status === 404 || msg.includes('chat session not found')) {
          try {
            const createRes = await apiRequest('/api/chat/session', {
              method: 'POST',
              body: JSON.stringify({ title: 'Workspace Chat' })
            });
            const newSessionId = createRes.data?.session_id || createRes.data?.session?._id || createRes.session_id;
            if (newSessionId) {
              localStorage.setItem('chat_session_id', newSessionId);
              setSessionId(newSessionId);
              activeSession = newSessionId;
              response = await apiRequest('/api/chat/process', {
                method: 'POST',
                body: JSON.stringify({
                  message: text.trim(),
                  session_id: activeSession,
                  input_type: type
                })
              });
            } else {
              throw err;
            }
          } catch (createErr) {
            throw createErr;
          }
        } else {
          throw err;
        }
      }

      const replyMsg = {
        id: (Date.now() + 1).toString(),
        text: response.response_text || response.message || 'I processed your command.',
        role: 'eva',
        isEva: true,
        timestamp: new Date().toISOString(),
      };

      const nextMessages = [...messages, replyMsg];
      setMessages(nextMessages);
      if (activeSession) saveSessionMessages(activeSession, nextMessages);
      upsertConversation(activeSession, buildTitleFromMessage(text), replyMsg.text);
      
      if (response.intent && response.intent !== 'general') {
        fetchDashboard();
      }
      
    } catch (err) {
      console.error('Failed to send message to AI:', err);
      const errMsg = {
        id: (Date.now() + 1).toString(),
        text: `Error: ${err.message || 'Could not communicate with AI server.'}`,
        role: 'eva',
        isEva: true,
        timestamp: new Date().toISOString(),
      };
      const nextMessages = [...messages, errMsg];
      setMessages(nextMessages);
      if (activeSession) saveSessionMessages(activeSession, nextMessages);
      if (activeSession) upsertConversation(activeSession, buildTitleFromMessage(text), errMsg.text);
    } finally {
      setIsEvaTyping(false);
    }
  };

  const clearChat = async () => {
    const newSessionId = await getOrCreateSession();
    if (newSessionId) {
      loadConversation(newSessionId);
      saveStoredConversations(getStoredConversations());
    } else {
      loadMockMessages();
    }
  };

  return (
    <ChatContext.Provider value={{
      messages,
      isEvaTyping,
      conversations,
      sessionId,
      selectedSessionId,
      selectConversation,
      sendMessage,
      clearChat
    }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => useContext(ChatContext);
