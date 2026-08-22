import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  TextInput,
  ScrollView,
  ActivityIndicator,
  useWindowDimensions,
  Platform,
  Animated,
  Easing
} from 'react-native';

const getApiBaseUrl = () => {
  if (Platform.OS === 'web') {
    if (typeof window !== 'undefined' && window.location) {
      const { port } = window.location;
      if (port === '8000' || !port) return '';
      return process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
    }
    return '';
  } else {
    if (process.env.EXPO_PUBLIC_API_URL) return process.env.EXPO_PUBLIC_API_URL;
    return Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';
  }
};

const API_BASE_URL = getApiBaseUrl();

// ─────────────────────────────────────────────
//  Toast Notification Component
// ─────────────────────────────────────────────
const TOAST_TYPES = {
  success: { bg: 'rgba(16,185,129,0.15)', border: '#10B981', icon: '✅', label: 'Success' },
  error:   { bg: 'rgba(239,68,68,0.15)',  border: '#EF4444', icon: '❌', label: 'Error' },
  warning: { bg: 'rgba(245,158,11,0.15)', border: '#F59E0B', icon: '⚠️', label: 'Warning' },
  info:    { bg: 'rgba(59,130,246,0.15)', border: '#3B82F6', icon: 'ℹ️', label: 'Info' },
  redirect:{ bg: 'rgba(139,92,246,0.15)','border': '#8B5CF6', icon: '↗️', label: 'Redirect' },
};

function ToastItem({ toast, onDismiss }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(-20)).current;
  const progress = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    // Enter animation
    Animated.parallel([
      Animated.timing(opacity, { toValue: 1, duration: 300, useNativeDriver: true }),
      Animated.spring(translateY, { toValue: 0, tension: 80, friction: 10, useNativeDriver: true }),
    ]).start();

    // Progress bar shrink
    Animated.timing(progress, {
      toValue: 0,
      duration: toast.duration || 4000,
      easing: Easing.linear,
      useNativeDriver: false,
    }).start();

    // Auto-dismiss
    const timer = setTimeout(() => {
      Animated.parallel([
        Animated.timing(opacity, { toValue: 0, duration: 250, useNativeDriver: true }),
        Animated.timing(translateY, { toValue: -20, duration: 250, useNativeDriver: true }),
      ]).start(() => onDismiss(toast.id));
    }, toast.duration || 4000);

    return () => clearTimeout(timer);
  }, []);

  const t = TOAST_TYPES[toast.type] || TOAST_TYPES.info;

  return (
    <Animated.View style={[styles.toastItem, { opacity, transform: [{ translateY }], backgroundColor: t.bg, borderColor: t.border }]}>
      <View style={styles.toastInner}>
        <Text style={styles.toastIcon}>{t.icon}</Text>
        <View style={styles.toastContent}>
          <Text style={[styles.toastLabel, { color: t.border }]}>{t.label}</Text>
          <Text style={styles.toastMessage}>{toast.message}</Text>
        </View>
        <TouchableOpacity onPress={() => onDismiss(toast.id)} style={styles.toastClose}>
          <Text style={styles.toastCloseText}>✕</Text>
        </TouchableOpacity>
      </View>
      <View style={styles.toastProgressBar}>
        <Animated.View style={[styles.toastProgressFill, { backgroundColor: t.border, width: progress.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] }) }]} />
      </View>
    </Animated.View>
  );
}

function ToastContainer({ toasts, onDismiss }) {
  if (Platform.OS !== 'web') return null;
  return (
    <View style={styles.toastContainer}>
      {toasts.map(t => <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />)}
    </View>
  );
}

// ─────────────────────────────────────────────
//  Animated Pulse Dot (live status)
// ─────────────────────────────────────────────
function PulseDot({ color = '#10B981' }) {
  const scale = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(scale, { toValue: 1.6, duration: 800, useNativeDriver: true }),
        Animated.timing(scale, { toValue: 1, duration: 800, useNativeDriver: true }),
      ])
    ).start();
  }, []);
  return (
    <View style={{ width: 10, height: 10, alignItems: 'center', justifyContent: 'center', marginRight: 6 }}>
      <Animated.View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: color, opacity: 0.3, transform: [{ scale }], position: 'absolute' }} />
      <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: color }} />
    </View>
  );
}

// ─────────────────────────────────────────────
//  Status Step Bar
// ─────────────────────────────────────────────
const APP_STEPS = ['START', 'INFORMATION_COLLECTION', 'DOCUMENT_VALIDATION', 'PAYMENT', 'SUBMISSION', 'CERTIFICATE_GENERATION', 'COMPLETED'];
const STEP_LABELS = { START: 'Start', INFORMATION_COLLECTION: 'Info', DOCUMENT_VALIDATION: 'Docs', PAYMENT: 'Pay', SUBMISSION: 'Submit', CERTIFICATE_GENERATION: 'Cert', COMPLETED: 'Done' };

function StatusStepBar({ currentState }) {
  const idx = APP_STEPS.indexOf(currentState);
  return (
    <View style={styles.stepBarContainer}>
      {APP_STEPS.map((step, i) => {
        const done = i < idx;
        const active = i === idx;
        return (
          <React.Fragment key={step}>
            <View style={styles.stepItem}>
              <View style={[styles.stepDot, done && styles.stepDotDone, active && styles.stepDotActive]}>
                <Text style={[styles.stepDotText, (done || active) && { color: '#fff' }]}>
                  {done ? '✓' : i + 1}
                </Text>
              </View>
              <Text style={[styles.stepLabel, done && styles.stepLabelDone, active && styles.stepLabelActive]}>
                {STEP_LABELS[step]}
              </Text>
            </View>
            {i < APP_STEPS.length - 1 && (
              <View style={[styles.stepConnector, done && styles.stepConnectorDone]} />
            )}
          </React.Fragment>
        );
      })}
    </View>
  );
}

// ─────────────────────────────────────────────
//  KPI Card with animated value
// ─────────────────────────────────────────────
function KpiCard({ value, label, color = '#3B82F6', icon }) {
  return (
    <View style={[styles.kpiCard, { borderTopColor: color, borderTopWidth: 2 }]}>
      <Text style={styles.kpiIcon}>{icon}</Text>
      <Text style={[styles.kpiValue, { color }]}>{value}</Text>
      <Text style={styles.kpiLabel}>{label}</Text>
    </View>
  );
}

// ─────────────────────────────────────────────
//  Main App
// ─────────────────────────────────────────────
export default function App() {
  const { width } = useWindowDimensions();
  const isLargeScreen = width >= 900;

  // Toast state
  const [toasts, setToasts] = useState([]);
  const toastIdRef = useRef(0);

  const showToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastIdRef.current;
    setToasts(prev => [...prev.slice(-4), { id, message, type, duration }]);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // App state
  const [currentChannel, setCurrentChannel] = useState('WhatsApp');
  const [sessionId, setSessionId] = useState(`session-${Math.floor(100000 + Math.random() * 900000)}`);
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [appStateData, setAppStateData] = useState({});
  const [appStatus, setAppStatus] = useState('START');
  const [applicationId, setApplicationId] = useState(null);
  const [missingFields, setMissingFields] = useState([]);
  const [isBlockedByOPA, setIsBlockedByOPA] = useState(false);
  const [opaBlockReason, setOpaBlockReason] = useState('');
  const [preferredLang, setPreferredLang] = useState('en');

  // Dashboard state
  const [metrics, setMetrics] = useState({
    total_applications: 0, applications_today: 0, completed_applications: 0,
    pending_applications: 0, failed_applications: 0, escalations: 0,
    avg_processing_time_hours: 0, avg_response_latency_ms: 185.0,
    payment_success_rate: 100.0, doc_validation_success_rate: 100.0, anomalies_detected: 0
  });
  const [charts, setCharts] = useState({ services: {}, languages: {}, channels: {}, statuses: {}, blocked_requests: 0 });
  const [auditLogs, setAuditLogs] = useState([]);
  const [pendingEscalations, setPendingEscalations] = useState([]);
  const prevEscCountRef = useRef(0);

  // Voice
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);

  // Loading
  const [isSending, setIsSending] = useState(false);

  // Dashboard tab
  const [dashTab, setDashTab] = useState('kpi'); // kpi | audit | queue

  const chatScrollRef = useRef();

  // ── Dashboard polling ──────────────────────
  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (chatScrollRef.current) chatScrollRef.current.scrollToEnd({ animated: true });
  }, [chatHistory]);

  // Alert on new escalations
  useEffect(() => {
    if (pendingEscalations.length > prevEscCountRef.current && prevEscCountRef.current !== 0) {
      showToast(`🚨 New escalation received — ${pendingEscalations.length} pending in queue`, 'warning', 6000);
    }
    prevEscCountRef.current = pendingEscalations.length;
  }, [pendingEscalations.length]);

  // Alert on anomalies
  const prevAnomalyRef = useRef(0);
  useEffect(() => {
    if (metrics.anomalies_detected > prevAnomalyRef.current) {
      showToast(`🛡️ Anomaly engine flagged ${metrics.anomalies_detected} suspicious submissions`, 'error', 7000);
    }
    prevAnomalyRef.current = metrics.anomalies_detected;
  }, [metrics.anomalies_detected]);

  const fetchDashboardData = async () => {
    try {
      const tokenRes = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=admin&password=admin123'
      });
      const tokenData = await tokenRes.json();
      const token = tokenData.access_token;

      const [mRes, cRes, aRes, appRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/dashboard/metrics`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE_URL}/api/v1/dashboard/charts`,  { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE_URL}/api/v1/dashboard/audit`,   { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE_URL}/api/v1/applications/`,     { headers: { Authorization: `Bearer ${token}` } }),
      ]);

      if (mRes.ok) setMetrics(await mRes.json());
      if (cRes.ok) setCharts(await cRes.json());
      if (aRes.ok) setAuditLogs(await aRes.json());
      if (appRes.ok) {
        const list = await appRes.json();
        setPendingEscalations(list.filter(a => a.status === 'REJECTED' || a.status === 'UNDER_REVIEW'));
      }
    } catch (err) {
      console.log('Dashboard fetch error:', err);
    }
  };

  const speakText = (text) => {
    if (Platform.OS === 'web' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const clean = text.replace(/\[Cloud Response\]/g, '').replace(/⚠️.*/g, '');
      const utt = new SpeechSynthesisUtterance(clean);
      utt.lang = preferredLang === 'hi' ? 'hi-IN' : preferredLang === 'mr' ? 'mr-IN' : 'en-IN';
      window.speechSynthesis.speak(utt);
    }
  };

  const resetFlow = () => {
    setSessionId(`session-${Math.floor(100000 + Math.random() * 900000)}`);
    setChatHistory([]);
    setAppStateData({});
    setAppStatus('START');
    setApplicationId(null);
    setMissingFields([]);
    setIsBlockedByOPA(false);
    setOpaBlockReason('');
    showToast('Session reset successfully', 'info');
  };

  const handleSendMessage = async (textToSend, sessionOverride) => {
    const inputMessage = textToSend || chatInput;
    if (!inputMessage.trim()) return;

    setIsSending(true);
    if (!textToSend) setChatInput('');

    setChatHistory(prev => [...prev, { role: 'user', content: inputMessage, classification: 'PENDING' }]);
    const activeSessionId = sessionOverride || sessionId;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/conversation/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: activeSessionId, text: inputMessage, channel: currentChannel, language: preferredLang })
      });

      if (response.ok) {
        const data = await response.json();

        if (data.redirect_to_service) {
          const svc = data.redirect_to_service;
          showToast(`↗️ Redirecting to ${svc.replace(/_/g, ' ').toUpperCase()} — missing prerequisite documents`, 'redirect', 6000);
          const newSid = `session-${Math.floor(100000 + Math.random() * 900000)}`;
          setSessionId(newSid); setChatHistory([]); setAppStateData({}); setAppStatus('START');
          setApplicationId(null); setMissingFields([]); setIsBlockedByOPA(false);
          if (Platform.OS === 'web' && 'speechSynthesis' in window) window.speechSynthesis.cancel();
          setTimeout(() => handleSendMessage(`I want to apply for ${svc.replace(/_/g, ' ')}`, newSid), 300);
          return;
        }

        setAppStatus(data.state);
        setApplicationId(data.application_id);
        setAppStateData(data.extracted_data);
        setPreferredLang(data.language);
        setMissingFields(data.missing_fields);
        setIsBlockedByOPA(data.is_blocked);
        setOpaBlockReason(data.block_reason || '');

        if (data.is_blocked) showToast(`🔒 Request blocked: ${data.block_reason}`, 'error', 6000);

        fetchChatHistory();
        speakText(data.text);
        fetchDashboardData();
      } else {
        showToast('Failed to send message. Please try again.', 'error');
      }
    } catch (err) {
      showToast('Network error. Check if the backend is running.', 'error');
      console.error(err);
    } finally {
      setIsSending(false);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/conversation/${sessionId}/history`);
      if (res.ok) setChatHistory(await res.json());
    } catch (err) { console.error(err); }
  };

  const startRecording = async () => {
    if (Platform.OS !== 'web') {
      showToast('Voice recording is fully supported on browsers only', 'warning');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/wav' });
        setIsSending(true);
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('channel', currentChannel);
        formData.append('language', preferredLang);
        formData.append('audio', audioBlob, 'user_audio_upload.wav');

        try {
          const res = await fetch(`${API_BASE_URL}/api/v1/conversation/voice`, { method: 'POST', body: formData });
          if (res.ok) {
            const data = await res.json();
            setAppStatus(data.state); setApplicationId(data.application_id); setAppStateData(data.extracted_data);
            setPreferredLang(data.language); setMissingFields(data.missing_fields);
            setIsBlockedByOPA(data.is_blocked); setOpaBlockReason(data.block_reason || '');
            fetchChatHistory(); speakText(data.text); fetchDashboardData();
            showToast('Voice message processed successfully', 'success', 3000);
          }
        } catch (err) {
          showToast('Error processing voice. Please try again.', 'error');
        } finally { setIsSending(false); }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setAudioChunks(chunks);
      setIsRecording(true);
      showToast('Recording started… Release to send', 'info', 2000);
    } catch (err) {
      showToast('Microphone access denied. Please allow it in browser settings.', 'error');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) { mediaRecorder.stop(); setIsRecording(false); }
  };

  const handleDocumentUpload = async (docType, fileEvent) => {
    if (!applicationId) {
      showToast('Start the application flow by sending "hi" first', 'warning');
      return;
    }
    const file = fileEvent.target.files[0];
    if (!file) return;

    setIsSending(true);
    const formData = new FormData();
    formData.append('application_id', applicationId);
    formData.append('doc_type', docType);
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/applications/documents/upload`, { method: 'POST', body: formData });
      if (res.ok) {
        const data = await res.json();
        showToast(`${docType.replace(/_/g, ' ').toUpperCase()} validated ✓ — OCR Confidence: ${Math.round(data.confidence * 100)}%`, 'success', 5000);
        fetchChatHistory();
        handleSendMessage('Document validation progress check');
      } else {
        const errData = await res.json();
        showToast(`Document verification failed: ${errData.detail}`, 'error', 6000);
      }
    } catch (err) {
      showToast('Upload failed. Check network and try again.', 'error');
    } finally { setIsSending(false); }
  };

  const handleInitiatePayment = async () => {
    if (!applicationId || !appStateData.fee) return;
    setIsSending(true);
    try {
      const initRes = await fetch(`${API_BASE_URL}/api/v1/adapters/payment/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ application_id: applicationId, amount: appStateData.fee, payment_method: 'UPI' })
      });
      if (initRes.ok) {
        const payObj = await initRes.json();
        const confirmRes = await fetch(`${API_BASE_URL}/api/v1/adapters/payment/${payObj.id}/confirm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'SUCCESS' })
        });
        if (confirmRes.ok) {
          showToast(`💳 Payment of ₹${appStateData.fee} via UPI completed successfully!`, 'success', 6000);
          handleSendMessage('Payment confirmation check');
        }
      }
    } catch (err) {
      showToast('Payment gateway error. Please retry.', 'error');
    } finally { setIsSending(false); }
  };

  const handleOfficerAction = async (appId, action, reason) => {
    try {
      const tokenRes = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=officer&password=officer123'
      });
      const tokenData = await tokenRes.json();
      const formData = new FormData();
      formData.append('action', action);
      formData.append('reason', reason);

      const res = await fetch(`${API_BASE_URL}/api/v1/applications/${appId}/officer-action`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${tokenData.access_token}` },
        body: formData
      });
      if (res.ok) {
        const typeMap = { APPROVE: 'success', REJECT: 'error', REQUEST_CORRECTION: 'warning' };
        showToast(`Officer action: Application #${appId} ${action.toLowerCase()}d`, typeMap[action] || 'info', 5000);
        fetchDashboardData();
        fetchChatHistory();
      }
    } catch (err) {
      showToast('Officer action failed. Please retry.', 'error');
    }
  };

  const triggerDialectVoiceCommand = async (dialectCode) => {
    const audioMap = {
      hi: 'mere_bete_ke_college_admission_ke_liye_ncl_certificate_chahiye.wav',
      mr: 'mazya_mulachya_admission_sathi_ncl_dakhla_hawa.mp3',
      lack_proof: 'utpannacha_dakhla_nahiye.mp3',
      start_income: 'ho_suru_kara.wav',
    };
    const audioName = audioMap[dialectCode];
    if (!audioName) return;

    setIsSending(true);
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('channel', currentChannel);
    formData.append('language', preferredLang);
    formData.append('audio', new Blob([''], { type: 'audio/wav' }), audioName);

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/conversation/voice`, { method: 'POST', body: formData });
      if (res.ok) {
        const data = await res.json();
        if (data.redirect_to_service) {
          const svc = data.redirect_to_service;
          showToast(`↗️ Redirecting to ${svc.replace(/_/g, ' ').toUpperCase()} service`, 'redirect', 5000);
          const newSid = `session-${Math.floor(100000 + Math.random() * 900000)}`;
          setSessionId(newSid); setChatHistory([]); setAppStateData({}); setAppStatus('START');
          setApplicationId(null); setMissingFields([]); setIsBlockedByOPA(false);
          if (Platform.OS === 'web' && 'speechSynthesis' in window) window.speechSynthesis.cancel();
          setTimeout(() => handleSendMessage(`I want to apply for ${svc.replace(/_/g, ' ')}`, newSid), 300);
          return;
        }
        setAppStatus(data.state); setApplicationId(data.application_id); setAppStateData(data.extracted_data);
        setPreferredLang(data.language); setMissingFields(data.missing_fields);
        setIsBlockedByOPA(data.is_blocked); setOpaBlockReason(data.block_reason || '');
        fetchChatHistory(); speakText(data.text); fetchDashboardData();
        showToast(`Dialect simulation processed (${dialectCode.toUpperCase()})`, 'info', 3000);
      }
    } catch (err) {
      showToast('Dialect simulation error', 'error');
    } finally { setIsSending(false); }
  };

  const getReadinessProgress = () => appStateData.readiness_score || 0;

  const getDocStatusStyle = (status) => {
    if (!status || status === 'Awaiting Upload') return { color: '#64748B' };
    if (status.includes('VALIDATED')) return { color: '#10B981' };
    if (status.includes('MISMATCH') || status.includes('FAILED')) return { color: '#EF4444' };
    return { color: '#64748B' };
  };

  const getProgressColor = (score) => {
    if (score >= 100) return '#10B981';
    if (score >= 70)  return '#3B82F6';
    if (score >= 40)  return '#F59E0B';
    return '#EF4444';
  };

  const getLangFlag = (lang) => ({ en: '🇬🇧', hi: '🇮🇳', mr: '🌐' }[lang] || '🌐');

  // ─────────────── RENDER ───────────────
  return (
    <View style={styles.appContainer}>

      {/* ── Toast Notification Layer ── */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* ── Header ── */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.crestIcon}>🏛️</Text>
          <View>
            <Text style={styles.headerTitle}>MAHA-REVENUE SERVICES</Text>
            <View style={styles.headerSubRow}>
              <PulseDot color="#10B981" />
              <Text style={styles.headerSubtitle}>Government of Maharashtra • AI-Powered • Live</Text>
            </View>
          </View>
        </View>
        <View style={styles.headerRight}>
          <View style={styles.sessionChip}>
            <Text style={styles.sessionChipDot}>●</Text>
            <Text style={styles.sessionChipText}>{sessionId.split('-').slice(-1)[0]}</Text>
          </View>
          <View style={styles.langChip}>
            <Text style={styles.langChipText}>{getLangFlag(preferredLang)} {preferredLang.toUpperCase()}</Text>
          </View>
          <TouchableOpacity style={styles.resetBtn} onPress={resetFlow} id="reset-flow-btn">
            <Text style={styles.resetBtnText}>⟳ Reset</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ── OPA Block Alert Banner ── */}
      {isBlockedByOPA && (
        <View style={styles.opaBanner}>
          <Text style={styles.opaBannerIcon}>🔒</Text>
          <Text style={styles.opaBannerText}>Policy Engine Block: {opaBlockReason}</Text>
        </View>
      )}

      {/* ── Progress Bar ── */}
      {appStatus !== 'START' && (
        <View style={styles.progressStepWrap}>
          <StatusStepBar currentState={appStatus} />
        </View>
      )}

      {/* ── Main Layout ── */}
      <View style={[styles.mainLayout, { flexDirection: isLargeScreen ? 'row' : 'column' }]}>

        {/* ════ LEFT — Channel Simulator ════ */}
        <View style={[styles.panel, { flex: isLargeScreen ? 1.2 : 0 }]}>
          <View style={styles.panelHeader}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Text style={styles.panelTitle}>Omnichannel Simulator</Text>
              {applicationId && (
                <View style={styles.appIdBadge}>
                  <Text style={styles.appIdBadgeText}>#{applicationId}</Text>
                </View>
              )}
            </View>
            <View style={styles.channelTabs}>
              {[
                { id: 'WhatsApp', icon: '💬', label: 'WhatsApp' },
                { id: 'IVR', icon: '📞', label: 'IVR' },
                { id: 'WebPortal', icon: '🌐', label: 'Portal' },
              ].map(ch => (
                <TouchableOpacity
                  key={ch.id}
                  id={`channel-tab-${ch.id.toLowerCase()}`}
                  style={[styles.channelTab, currentChannel === ch.id && styles.channelTabActive]}
                  onPress={() => {
                    setCurrentChannel(ch.id);
                    if (applicationId) handleSendMessage(`Switching channel to ${ch.id}`);
                    showToast(`Switched to ${ch.label} channel`, 'info', 2000);
                  }}
                >
                  <Text style={[styles.channelTabText, currentChannel === ch.id && styles.channelTabTextActive]}>
                    {ch.icon} {ch.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.simulatorBody}>

            {/* ── WhatsApp Channel ── */}
            {currentChannel === 'WhatsApp' && (
              <View style={styles.waWrapper}>
                <View style={styles.waHeader}>
                  <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                    <View style={styles.waAvatar}><Text style={{ fontSize: 14 }}>🤖</Text></View>
                    <View>
                      <Text style={styles.waName}>Maha-Revenue Bot</Text>
                      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        <PulseDot color="#4ade80" />
                        <Text style={styles.waStatus}>Online</Text>
                      </View>
                    </View>
                  </View>
                  <Text style={styles.waLang}>{getLangFlag(preferredLang)} {preferredLang.toUpperCase()}</Text>
                </View>

                <ScrollView style={styles.chatThread} ref={chatScrollRef} contentContainerStyle={{ padding: 12 }}>
                  {chatHistory.length === 0 ? (
                    <View style={styles.emptyChatWrap}>
                      <Text style={styles.emptyChatEmoji}>💬</Text>
                      <Text style={styles.emptyChatTitle}>Start a Conversation</Text>
                      <Text style={styles.emptyChatSub}>Type "hi" or use a dialect preset below</Text>
                    </View>
                  ) : (
                    chatHistory.map((msg, i) => (
                      <View key={i} style={[styles.msgBubble, msg.role === 'user' ? styles.msgUser : styles.msgBot]}>
                        {msg.role !== 'user' && <Text style={styles.msgBotLabel}>🤖 Bot</Text>}
                        <Text style={styles.msgText}>{msg.content}</Text>
                        <View style={styles.msgMeta}>
                          {msg.classification && msg.classification !== 'PENDING' && (
                            <Text style={[styles.classTag, msg.classification === 'SENSITIVE' ? styles.tagSensitive : msg.classification === 'RESTRICTED' ? styles.tagRestricted : styles.tagPublic]}>
                              {msg.classification}
                            </Text>
                          )}
                          <Text style={styles.msgTime}>
                            {new Date(msg.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </Text>
                        </View>
                      </View>
                    ))
                  )}
                  {isSending && (
                    <View style={styles.typingIndicator}>
                      <ActivityIndicator size="small" color="#3B82F6" />
                      <Text style={styles.typingText}>Bot is typing…</Text>
                    </View>
                  )}
                </ScrollView>

                {/* Dialect presets */}
                <View style={styles.presetsBar}>
                  <Text style={styles.presetsBarLabel}>🗣️ Dialect Presets</Text>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                    <TouchableOpacity id="preset-hindi" style={styles.presetChip} onPress={() => triggerDialectVoiceCommand('hi')}>
                      <Text style={styles.presetChipText}>🇮🇳 Hindi: "Mere bete ke admission…"</Text>
                    </TouchableOpacity>
                    <TouchableOpacity id="preset-marathi" style={styles.presetChip} onPress={() => triggerDialectVoiceCommand('mr')}>
                      <Text style={styles.presetChipText}>🌐 Marathi: "NCL दाखला हवा आहे"</Text>
                    </TouchableOpacity>
                  </ScrollView>
                </View>

                {/* Input */}
                <View style={styles.inputBar}>
                  <TouchableOpacity
                    id="mic-btn"
                    style={[styles.micBtn, isRecording && styles.micBtnActive]}
                    onPressIn={startRecording}
                    onPressOut={stopRecording}
                  >
                    <Text style={styles.micBtnText}>{isRecording ? '⏹' : '🎤'}</Text>
                  </TouchableOpacity>
                  <TextInput
                    id="chat-input"
                    style={styles.chatInput}
                    placeholder="Type in मराठी, हिंदी or English…"
                    placeholderTextColor="#475569"
                    value={chatInput}
                    onChangeText={setChatInput}
                    onSubmitEditing={() => handleSendMessage()}
                  />
                  <TouchableOpacity
                    id="send-btn"
                    style={[styles.sendBtn, (!chatInput.trim() && !isSending) && styles.sendBtnDisabled]}
                    onPress={() => handleSendMessage()}
                    disabled={isSending}
                  >
                    {isSending ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <Text style={styles.sendBtnText}>Send ➤</Text>
                    )}
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {/* ── IVR Channel ── */}
            {currentChannel === 'IVR' && (
              <View style={styles.ivrWrapper}>
                <View style={styles.ivrCard}>
                  <View style={[styles.ivrStatusRing, isRecording && styles.ivrStatusRingActive]}>
                    <Text style={styles.ivrPhoneIcon}>📞</Text>
                  </View>
                  <Text style={styles.ivrStatusText}>
                    {isRecording ? '🔴 RECORDING…' : 'ACTIVE VOICE CHANNEL'}
                  </Text>
                  <Text style={styles.ivrLang}>Language: {preferredLang.toUpperCase()} {getLangFlag(preferredLang)}</Text>

                  <View style={styles.ivrNarration}>
                    <Text style={styles.ivrNarrationTitle}>🔊 Current TTS Output</Text>
                    <Text style={styles.ivrNarrationText}>
                      {chatHistory.filter(m => m.role === 'assistant').slice(-1)[0]?.content || 'Press 1 for English, 2 for Hindi, or speak your query.'}
                    </Text>
                  </View>

                  <View style={styles.ivrActions}>
                    <TouchableOpacity id="ivr-record-btn" style={[styles.ivrRecordBtn, isRecording && styles.ivrRecordBtnActive]} onPress={isRecording ? stopRecording : startRecording}>
                      <Text style={styles.ivrRecordBtnText}>{isRecording ? '⏹ Stop' : '🎤 Speak'}</Text>
                    </TouchableOpacity>
                    <TouchableOpacity id="ivr-dial-1" style={styles.ivrDialBtn} onPress={() => handleSendMessage('1')}>
                      <Text style={styles.ivrDialBtnText}>1</Text>
                    </TouchableOpacity>
                    <TouchableOpacity id="ivr-dial-2" style={styles.ivrDialBtn} onPress={() => handleSendMessage('2')}>
                      <Text style={styles.ivrDialBtnText}>2</Text>
                    </TouchableOpacity>
                    <TouchableOpacity id="ivr-dial-hash" style={styles.ivrDialBtn} onPress={() => handleSendMessage('#')}>
                      <Text style={styles.ivrDialBtnText}>#</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              </View>
            )}

            {/* ── Web Portal Channel ── */}
            {currentChannel === 'WebPortal' && (
              <ScrollView style={styles.portalWrapper} contentContainerStyle={{ padding: 16 }}>
                <Text style={styles.portalTitle}>🏛️ Department of Revenue & Forest</Text>
                <Text style={styles.portalSubtitle}>Online Self-Service Portal — Synced with AI Chatbot</Text>

                {/* Readiness Score */}
                <View style={styles.readinessCard}>
                  <View style={styles.readinessRow}>
                    <Text style={styles.readinessLabel}>Application Readiness</Text>
                    <Text style={[styles.readinessScore, { color: getProgressColor(getReadinessProgress()) }]}>
                      {getReadinessProgress()}<Text style={{ fontSize: 12 }}>/100</Text>
                    </Text>
                  </View>
                  <View style={styles.progressBg}>
                    <View style={[styles.progressFill, {
                      width: `${getReadinessProgress()}%`,
                      backgroundColor: getProgressColor(getReadinessProgress())
                    }]} />
                  </View>
                  {getReadinessProgress() >= 100 && (
                    <Text style={styles.readinessComplete}>✅ All fields collected — ready to submit</Text>
                  )}
                </View>

                {/* Form Fields */}
                <View style={styles.formCard}>
                  <Text style={styles.formCardTitle}>📋 Applicant Information</Text>
                  <View style={styles.formGrid}>
                    {[
                      { label: 'Full Name', value: appStateData.full_name },
                      { label: 'District', value: appStateData.district },
                      { label: 'Annual Income (₹)', value: appStateData.annual_income ? `₹${Number(appStateData.annual_income).toLocaleString('en-IN')}` : '' },
                      { label: 'Aadhaar e-Consent', value: appStateData.consent ? '✅ Authenticated' : '❌ Pending' },
                    ].map(f => (
                      <View key={f.label} style={styles.formField}>
                        <Text style={styles.fieldLabel}>{f.label}</Text>
                        <View style={[styles.fieldValue, f.value && styles.fieldValueFilled]}>
                          <Text style={[styles.fieldValueText, !f.value && styles.fieldValueEmpty]}>
                            {f.value || '— Awaiting extraction…'}
                          </Text>
                        </View>
                      </View>
                    ))}
                  </View>
                </View>

                {/* Prerequisite Alert */}
                {appStateData.lacks_income_proof && !appStateData.prerequisite_completed && (
                  <View style={styles.alertBanner}>
                    <Text style={styles.alertBannerIcon}>⚠️</Text>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.alertBannerTitle}>Missing Income Proof</Text>
                      <Text style={styles.alertBannerBody}>System initialized a nested Income Certificate application. Please complete it to proceed.</Text>
                    </View>
                    <TouchableOpacity id="simulate-income-btn" style={styles.alertBannerBtn} onPress={() => triggerDialectVoiceCommand('start_income')}>
                      <Text style={styles.alertBannerBtnText}>Simulate</Text>
                    </TouchableOpacity>
                  </View>
                )}

                {/* OCR Mismatch Alert */}
                {appStateData.dob_mismatch_detected && !appStateData.dob_mismatch_resolved && (
                  <View style={[styles.alertBanner, { borderColor: '#EF4444', backgroundColor: 'rgba(239,68,68,0.08)' }]}>
                    <Text style={styles.alertBannerIcon}>🚨</Text>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.alertBannerTitle, { color: '#EF4444' }]}>OCR Mismatch Detected</Text>
                      <Text style={styles.alertBannerBody}>Aadhaar DOB (12-05-2002) ≠ Caste Proof DOB (12-05-2003). Please confirm the correct date.</Text>
                    </View>
                    <TouchableOpacity id="resolve-dob-btn" style={[styles.alertBannerBtn, { backgroundColor: '#EF4444' }]} onPress={() => handleSendMessage('12-05-2002')}>
                      <Text style={styles.alertBannerBtnText}>Confirm 2002</Text>
                    </TouchableOpacity>
                  </View>
                )}

                {/* Documents */}
                <View style={styles.docsCard}>
                  <Text style={styles.formCardTitle}>📁 Required Documents</Text>
                  {[
                    { type: 'identity_proof', label: 'Identity Proof', sub: 'Aadhaar Card / Passport' },
                    { type: 'address_proof',  label: 'Address Proof',  sub: 'Utility Bill / Rent Agreement' },
                    { type: 'caste_proof',    label: 'Caste Proof',    sub: 'Community / School Leaving Certificate' },
                    { type: 'income_proof',   label: 'Income Proof',   sub: 'Form 16 / Salary Slip', disabled: appStateData.lacks_income_proof },
                  ].map(doc => {
                    const status = appStateData.documents_uploaded?.[doc.type];
                    const isValidated = status?.includes('VALIDATED');
                    const isFailed = status?.includes('FAILED') || status?.includes('MISMATCH');
                    return (
                      <View key={doc.type} style={[styles.docRow, isValidated && styles.docRowValidated, isFailed && styles.docRowFailed]}>
                        <View style={styles.docIcon}>
                          <Text style={{ fontSize: 18 }}>{isValidated ? '✅' : isFailed ? '❌' : '📄'}</Text>
                        </View>
                        <View style={styles.docInfo}>
                          <Text style={styles.docLabel}>{doc.label}</Text>
                          <Text style={styles.docSub}>{doc.sub}</Text>
                          {status && (
                            <Text style={[styles.docStatus, getDocStatusStyle(status)]}>{status}</Text>
                          )}
                        </View>
                        <View style={styles.docUploadArea}>
                          {Platform.OS === 'web' && (
                            <label style={{ cursor: doc.disabled ? 'not-allowed' : 'pointer' }}>
                              <View style={[styles.uploadBtn, doc.disabled && styles.uploadBtnDisabled, isValidated && styles.uploadBtnDone]}>
                                <Text style={styles.uploadBtnText}>{isValidated ? '✓ Re-upload' : doc.disabled ? '🔒 Locked' : '↑ Upload'}</Text>
                              </View>
                              <input
                                type="file"
                                accept="image/*,application/pdf"
                                disabled={doc.disabled}
                                style={{ display: 'none' }}
                                onChange={(e) => handleDocumentUpload(doc.type, e)}
                              />
                            </label>
                          )}
                        </View>
                      </View>
                    );
                  })}
                </View>

                {/* Payment */}
                {appStatus === 'PAYMENT' && (
                  <View style={styles.payCard}>
                    <Text style={styles.payTitle}>💳 Government Fee Payment</Text>
                    <View style={styles.payAmountRow}>
                      <Text style={styles.payAmountLabel}>Processing Fee</Text>
                      <Text style={styles.payAmountValue}>₹{appStateData.fee || 50}</Text>
                    </View>
                    <Text style={styles.payMethod}>Payment Method: UPI</Text>
                    <TouchableOpacity id="pay-btn" style={styles.payBtn} onPress={handleInitiatePayment} disabled={isSending}>
                      {isSending ? <ActivityIndicator color="#fff" /> : <Text style={styles.payBtnText}>🔒 Authorize UPI Payment</Text>}
                    </TouchableOpacity>
                  </View>
                )}

                {/* Certificate */}
                {appStatus === 'CERTIFICATE_GENERATION' && (
                  <View style={styles.certCard}>
                    <Text style={styles.certEmoji}>🎉</Text>
                    <Text style={styles.certTitle}>Application Approved!</Text>
                    <Text style={styles.certSub}>Your certificate is ready for download.</Text>
                    <TouchableOpacity
                      id="download-cert-btn"
                      style={styles.certBtn}
                      onPress={() => {
                        window.open(`${API_BASE_URL}/api/v1/applications/${applicationId}/certificate`);
                        showToast('Certificate download started', 'success');
                      }}
                    >
                      <Text style={styles.certBtnText}>📄 Download Certificate</Text>
                    </TouchableOpacity>
                  </View>
                )}
              </ScrollView>
            )}
          </View>
        </View>

        {/* ════ RIGHT — Officer Dashboard ════ */}
        <View style={[styles.panel, { flex: isLargeScreen ? 1 : 0 }]}>
          <View style={styles.panelHeader}>
            <Text style={styles.panelTitle}>Officer Dashboard</Text>
            <View style={styles.dashTabs}>
              {[
                { id: 'kpi', label: '📊 KPIs' },
                { id: 'audit', label: '🔍 Audit' },
                { id: 'queue', label: `⚡ Queue ${pendingEscalations.length > 0 ? `(${pendingEscalations.length})` : ''}` },
              ].map(tab => (
                <TouchableOpacity
                  key={tab.id}
                  id={`dash-tab-${tab.id}`}
                  style={[styles.dashTab, dashTab === tab.id && styles.dashTabActive]}
                  onPress={() => setDashTab(tab.id)}
                >
                  <Text style={[styles.dashTabText, dashTab === tab.id && styles.dashTabTextActive]}>{tab.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <ScrollView contentContainerStyle={{ padding: 14 }}>

            {/* KPI Tab */}
            {dashTab === 'kpi' && (
              <>
                {metrics.anomalies_detected > 0 && (
                  <View style={styles.anomalyBanner}>
                    <Text style={styles.anomalyBannerIcon}>🛡️</Text>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.anomalyBannerTitle}>Anomaly Engine Alert</Text>
                      <Text style={styles.anomalyBannerBody}>{metrics.anomalies_detected} submissions flagged by IsolationForest ML model</Text>
                    </View>
                  </View>
                )}
                <View style={styles.kpiGrid}>
                  <KpiCard icon="📋" value={metrics.total_applications} label="Total Submissions" color="#3B82F6" />
                  <KpiCard icon="📅" value={metrics.applications_today} label="Today" color="#8B5CF6" />
                  <KpiCard icon="✅" value={metrics.completed_applications} label="Completed" color="#10B981" />
                  <KpiCard icon="⏳" value={metrics.pending_applications} label="Pending" color="#F59E0B" />
                  <KpiCard icon="⚡" value={`${metrics.avg_response_latency_ms}ms`} label="Avg Latency" color="#06B6D4" />
                  <KpiCard icon="⏱" value={`${metrics.avg_processing_time_hours}h`} label="Avg Process Time" color="#EC4899" />
                  <KpiCard icon="💳" value={`${metrics.payment_success_rate}%`} label="Payment Success" color="#10B981" />
                  <KpiCard icon="📑" value={`${metrics.doc_validation_success_rate}%`} label="OCR Pass Rate" color="#3B82F6" />
                </View>

                {/* Service distribution */}
                {Object.keys(charts.services || {}).length > 0 && (
                  <View style={styles.chartCard}>
                    <Text style={styles.chartTitle}>Services Distribution</Text>
                    {Object.entries(charts.services).map(([k, v]) => (
                      <View key={k} style={styles.chartRow}>
                        <Text style={styles.chartKey}>{k.replace(/_/g, ' ')}</Text>
                        <View style={styles.chartBarBg}>
                          <View style={[styles.chartBarFill, { width: `${Math.min(100, (v / (metrics.total_applications || 1)) * 100)}%` }]} />
                        </View>
                        <Text style={styles.chartVal}>{v}</Text>
                      </View>
                    ))}
                  </View>
                )}
              </>
            )}

            {/* Audit Tab */}
            {dashTab === 'audit' && (
              <>
                <Text style={styles.tabSectionTitle}>Data Sovereignty Guard Logs</Text>
                {auditLogs.length === 0 ? (
                  <View style={styles.emptyState}>
                    <Text style={styles.emptyStateIcon}>📭</Text>
                    <Text style={styles.emptyStateText}>Awaiting events…</Text>
                  </View>
                ) : (
                  auditLogs.map((log, i) => (
                    <View key={i} style={styles.auditCard}>
                      <View style={styles.auditTop}>
                        <Text style={styles.auditActor}>{log.actor.toUpperCase()}</Text>
                        <Text style={styles.auditAction}>{log.action}</Text>
                        <View style={[styles.auditResultBadge, log.result === 'BLOCKED' ? styles.resultBadgeBlocked : log.result === 'FAILED' ? styles.resultBadgeFailed : styles.resultBadgeSuccess]}>
                          <Text style={styles.auditResultText}>{log.result}</Text>
                        </View>
                      </View>
                      {log.metadata_json?.reasons && (
                        <Text style={styles.auditViolation}>⚠ {log.metadata_json.reasons.join(' • ')}</Text>
                      )}
                      <Text style={styles.auditTime}>{new Date(log.timestamp || Date.now()).toLocaleTimeString()}</Text>
                    </View>
                  ))
                )}
              </>
            )}

            {/* Escalation Queue Tab */}
            {dashTab === 'queue' && (
              <>
                <Text style={styles.tabSectionTitle}>Officer Verification Queue</Text>
                {pendingEscalations.length === 0 ? (
                  <View style={styles.emptyState}>
                    <Text style={styles.emptyStateIcon}>✅</Text>
                    <Text style={styles.emptyStateText}>No pending escalations</Text>
                    <Text style={styles.emptyStateSub}>All applications are within automated processing limits</Text>
                  </View>
                ) : (
                  pendingEscalations.map(app => (
                    <View key={app.id} style={styles.escalCard}>
                      <View style={styles.escalHeader}>
                        <Text style={styles.escalAppNo}>{app.application_no}</Text>
                        <View style={[styles.escalStatusBadge, app.status === 'REJECTED' ? styles.statusRejected : styles.statusReview]}>
                          <Text style={styles.escalStatusText}>{app.status}</Text>
                        </View>
                      </View>
                      <Text style={styles.escalDetails}>
                        {app.service_id?.replace(/_/g, ' ').toUpperCase()} • {app.channel} • {app.language?.toUpperCase()}
                      </Text>
                      <Text style={styles.escalTime}>
                        Filed: {new Date(app.created_at || Date.now()).toLocaleDateString('en-IN')}
                      </Text>
                      <View style={styles.escalActions}>
                        <TouchableOpacity
                          id={`approve-${app.id}`}
                          style={styles.escalApproveBtn}
                          onPress={() => handleOfficerAction(app.id, 'APPROVE', 'Passed manual audit.')}
                        >
                          <Text style={styles.escalBtnText}>✓ Approve</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          id={`reject-${app.id}`}
                          style={styles.escalRejectBtn}
                          onPress={() => handleOfficerAction(app.id, 'REJECT', 'Rejected by officer review.')}
                        >
                          <Text style={styles.escalBtnText}>✕ Reject</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          id={`correction-${app.id}`}
                          style={styles.escalCorrectionBtn}
                          onPress={() => handleOfficerAction(app.id, 'REQUEST_CORRECTION', 'Correction required.')}
                        >
                          <Text style={styles.escalBtnText}>↩ Correction</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  ))
                )}
              </>
            )}

          </ScrollView>
        </View>
      </View>
    </View>
  );
}

// ─────────────────────────────────────────────
//  Styles
// ─────────────────────────────────────────────
const C = {
  bg:       '#080E1C',
  surface:  '#0F172A',
  card:     '#141E33',
  border:   '#1E2D45',
  border2:  '#253350',
  text:     '#E2E8F0',
  textSub:  '#64748B',
  textMuted:'#3E5070',
  blue:     '#3B82F6',
  green:    '#10B981',
  red:      '#EF4444',
  orange:   '#F59E0B',
  purple:   '#8B5CF6',
  cyan:     '#06B6D4',
};

const styles = StyleSheet.create({
  appContainer: { flex: 1, backgroundColor: C.bg },

  // ── Toast ──
  toastContainer: {
    position: 'fixed', top: 70, right: 16, zIndex: 9999,
    width: 340, pointerEvents: 'box-none',
  },
  toastItem: {
    borderRadius: 10, borderWidth: 1, marginBottom: 8,
    overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.5,
    shadowRadius: 12, elevation: 10,
  },
  toastInner: { flexDirection: 'row', alignItems: 'flex-start', padding: 12 },
  toastIcon: { fontSize: 18, marginRight: 10, marginTop: 1 },
  toastContent: { flex: 1 },
  toastLabel: { fontSize: 10, fontWeight: 'bold', letterSpacing: 0.5, marginBottom: 2, textTransform: 'uppercase' },
  toastMessage: { color: C.text, fontSize: 12, lineHeight: 18 },
  toastClose: { padding: 4, marginLeft: 8 },
  toastCloseText: { color: C.textSub, fontSize: 12 },
  toastProgressBar: { height: 3, backgroundColor: 'rgba(255,255,255,0.05)' },
  toastProgressFill: { height: 3 },

  // ── Header ──
  header: {
    backgroundColor: C.surface,
    paddingVertical: 12, paddingHorizontal: 20,
    borderBottomWidth: 1, borderBottomColor: C.border,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap',
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center' },
  crestIcon: { fontSize: 28, marginRight: 12 },
  headerTitle: { color: '#F1F5F9', fontSize: 15, fontWeight: 'bold', letterSpacing: 1.5 },
  headerSubRow: { flexDirection: 'row', alignItems: 'center', marginTop: 3 },
  headerSubtitle: { color: C.textSub, fontSize: 11 },
  headerRight: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4, flexWrap: 'wrap' },
  sessionChip: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(59,130,246,0.1)', borderWidth: 1, borderColor: 'rgba(59,130,246,0.2)',
    paddingVertical: 4, paddingHorizontal: 10, borderRadius: 20,
  },
  sessionChipDot: { color: C.blue, fontSize: 8, marginRight: 5 },
  sessionChipText: { color: C.blue, fontSize: 11, fontWeight: '600' },
  langChip: {
    backgroundColor: 'rgba(139,92,246,0.1)', borderWidth: 1, borderColor: 'rgba(139,92,246,0.2)',
    paddingVertical: 4, paddingHorizontal: 10, borderRadius: 20,
  },
  langChipText: { color: C.purple, fontSize: 11, fontWeight: '600' },
  resetBtn: {
    backgroundColor: 'rgba(239,68,68,0.1)', borderWidth: 1, borderColor: 'rgba(239,68,68,0.3)',
    paddingVertical: 5, paddingHorizontal: 12, borderRadius: 20,
  },
  resetBtnText: { color: '#FDA4AF', fontSize: 12, fontWeight: '600' },

  // ── OPA Banner ──
  opaBanner: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(239,68,68,0.12)', borderBottomWidth: 1, borderBottomColor: '#EF4444',
    paddingVertical: 8, paddingHorizontal: 20,
  },
  opaBannerIcon: { fontSize: 16, marginRight: 10 },
  opaBannerText: { color: '#FCA5A5', fontSize: 12, fontWeight: '600' },

  // ── Progress Step Bar ──
  progressStepWrap: {
    backgroundColor: C.surface, borderBottomWidth: 1, borderBottomColor: C.border,
    paddingVertical: 10, paddingHorizontal: 20,
  },
  stepBarContainer: { flexDirection: 'row', alignItems: 'center' },
  stepItem: { alignItems: 'center' },
  stepDot: {
    width: 22, height: 22, borderRadius: 11, borderWidth: 1.5, borderColor: C.border2,
    backgroundColor: C.card, alignItems: 'center', justifyContent: 'center',
  },
  stepDotDone: { backgroundColor: C.green, borderColor: C.green },
  stepDotActive: { backgroundColor: C.blue, borderColor: C.blue },
  stepDotText: { fontSize: 9, color: C.textSub, fontWeight: 'bold' },
  stepLabel: { fontSize: 8, color: C.textSub, marginTop: 3 },
  stepLabelDone: { color: C.green },
  stepLabelActive: { color: C.blue, fontWeight: 'bold' },
  stepConnector: { flex: 1, height: 1.5, backgroundColor: C.border2, marginBottom: 12 },
  stepConnectorDone: { backgroundColor: C.green },

  // ── Layout ──
  mainLayout: { flex: 1, backgroundColor: C.bg },
  panel: {
    margin: 8, backgroundColor: C.card, borderRadius: 14,
    borderWidth: 1, borderColor: C.border, overflow: 'hidden', flex: 1,
  },
  panelHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 14, backgroundColor: C.surface, borderBottomWidth: 1, borderBottomColor: C.border, flexWrap: 'wrap', gap: 8,
  },
  panelTitle: { color: '#F1F5F9', fontSize: 14, fontWeight: 'bold' },
  appIdBadge: {
    backgroundColor: 'rgba(59,130,246,0.15)', borderWidth: 1, borderColor: 'rgba(59,130,246,0.3)',
    borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2, marginLeft: 8,
  },
  appIdBadgeText: { color: C.blue, fontSize: 10, fontWeight: 'bold' },

  // ── Channel Tabs ──
  channelTabs: { flexDirection: 'row', backgroundColor: C.bg, borderRadius: 8, padding: 3 },
  channelTab: { paddingVertical: 5, paddingHorizontal: 10, borderRadius: 6 },
  channelTabActive: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border2 },
  channelTabText: { color: C.textSub, fontSize: 11, fontWeight: '600' },
  channelTabTextActive: { color: C.blue },

  // ── WhatsApp ──
  simulatorBody: { flex: 1, minHeight: 400 },
  waWrapper: { flex: 1, flexDirection: 'column', height: '100%' },
  waHeader: {
    backgroundColor: '#064E3B', paddingVertical: 10, paddingHorizontal: 14,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  waAvatar: {
    width: 32, height: 32, borderRadius: 16, backgroundColor: '#065F46',
    alignItems: 'center', justifyContent: 'center', marginRight: 10,
  },
  waName: { color: '#fff', fontWeight: 'bold', fontSize: 13 },
  waStatus: { color: '#6EE7B7', fontSize: 10 },
  waLang: { color: '#A7F3D0', fontSize: 11, fontWeight: '600' },
  chatThread: { flex: 1, backgroundColor: '#060D1B', paddingHorizontal: 12 },
  emptyChatWrap: { alignItems: 'center', paddingVertical: 50 },
  emptyChatEmoji: { fontSize: 36, marginBottom: 12 },
  emptyChatTitle: { color: C.text, fontSize: 15, fontWeight: 'bold', marginBottom: 6 },
  emptyChatSub: { color: C.textSub, fontSize: 12 },
  msgBubble: { maxWidth: '80%', borderRadius: 12, marginVertical: 4, padding: 10 },
  msgUser: { backgroundColor: '#1E3A8A', alignSelf: 'flex-end', borderBottomRightRadius: 2 },
  msgBot: { backgroundColor: '#1A2540', alignSelf: 'flex-start', borderBottomLeftRadius: 2, borderWidth: 1, borderColor: C.border },
  msgBotLabel: { color: C.blue, fontSize: 9, fontWeight: 'bold', marginBottom: 4 },
  msgText: { color: C.text, fontSize: 13, lineHeight: 19 },
  msgMeta: { flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', marginTop: 5, gap: 6 },
  classTag: { fontSize: 8, fontWeight: 'bold', paddingVertical: 1, paddingHorizontal: 5, borderRadius: 4 },
  tagSensitive: { backgroundColor: 'rgba(239,68,68,0.2)', color: '#EF4444' },
  tagRestricted: { backgroundColor: 'rgba(245,158,11,0.2)', color: '#F59E0B' },
  tagPublic: { backgroundColor: 'rgba(16,185,129,0.2)', color: '#10B981' },
  msgTime: { color: C.textSub, fontSize: 9 },
  typingIndicator: { flexDirection: 'row', alignItems: 'center', padding: 8 },
  typingText: { color: C.textSub, fontSize: 11, marginLeft: 8 },
  presetsBar: { padding: 10, backgroundColor: C.surface, borderTopWidth: 1, borderTopColor: C.border },
  presetsBarLabel: { color: C.textSub, fontSize: 10, marginBottom: 6 },
  presetChip: {
    backgroundColor: 'rgba(59,130,246,0.08)', borderWidth: 1, borderColor: 'rgba(59,130,246,0.2)',
    borderRadius: 20, paddingVertical: 5, paddingHorizontal: 12, marginRight: 8,
  },
  presetChipText: { color: C.blue, fontSize: 11 },
  inputBar: {
    flexDirection: 'row', padding: 10, backgroundColor: C.surface,
    alignItems: 'center', borderTopWidth: 1, borderTopColor: C.border, gap: 8,
  },
  micBtn: {
    width: 38, height: 38, borderRadius: 19, backgroundColor: C.card,
    borderWidth: 1, borderColor: C.border2, alignItems: 'center', justifyContent: 'center',
  },
  micBtnActive: { backgroundColor: 'rgba(239,68,68,0.2)', borderColor: C.red },
  micBtnText: { fontSize: 16 },
  chatInput: {
    flex: 1, backgroundColor: C.bg, borderRadius: 20, paddingHorizontal: 16,
    paddingVertical: 8, color: C.text, borderWidth: 1, borderColor: C.border2, fontSize: 13,
  },
  sendBtn: {
    backgroundColor: C.blue, borderRadius: 20, paddingVertical: 9,
    paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center',
  },
  sendBtnDisabled: { opacity: 0.5 },
  sendBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 12 },

  // ── IVR ──
  ivrWrapper: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 20, backgroundColor: '#060D1B' },
  ivrCard: { width: '100%', backgroundColor: C.surface, borderRadius: 16, padding: 24, alignItems: 'center', borderWidth: 1, borderColor: C.border },
  ivrStatusRing: {
    width: 80, height: 80, borderRadius: 40, alignItems: 'center', justifyContent: 'center',
    borderWidth: 2, borderColor: C.green, backgroundColor: 'rgba(16,185,129,0.1)', marginBottom: 14,
  },
  ivrStatusRingActive: { borderColor: C.red, backgroundColor: 'rgba(239,68,68,0.1)' },
  ivrPhoneIcon: { fontSize: 36 },
  ivrStatusText: { color: C.green, fontWeight: 'bold', fontSize: 12, letterSpacing: 1, marginBottom: 4 },
  ivrLang: { color: C.textSub, fontSize: 11, marginBottom: 20 },
  ivrNarration: {
    backgroundColor: C.bg, width: '100%', padding: 14, borderRadius: 10,
    borderWidth: 1, borderColor: C.border, marginBottom: 20,
  },
  ivrNarrationTitle: { color: C.blue, fontWeight: 'bold', fontSize: 11, marginBottom: 6 },
  ivrNarrationText: { color: C.text, fontSize: 12, lineHeight: 18 },
  ivrActions: { flexDirection: 'row', gap: 10, flexWrap: 'wrap', justifyContent: 'center' },
  ivrRecordBtn: { backgroundColor: C.red, paddingVertical: 10, paddingHorizontal: 20, borderRadius: 24 },
  ivrRecordBtnActive: { backgroundColor: C.green },
  ivrRecordBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 13 },
  ivrDialBtn: {
    width: 44, height: 44, borderRadius: 22, backgroundColor: C.card,
    borderWidth: 1, borderColor: C.border2, alignItems: 'center', justifyContent: 'center',
  },
  ivrDialBtnText: { color: C.text, fontWeight: 'bold', fontSize: 16 },

  // ── Portal ──
  portalWrapper: { flex: 1, backgroundColor: '#060D1B' },
  portalTitle: { color: '#F1F5F9', fontSize: 16, fontWeight: 'bold', marginBottom: 4 },
  portalSubtitle: { color: C.textSub, fontSize: 11, marginBottom: 16 },
  readinessCard: { backgroundColor: C.surface, borderRadius: 10, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: C.border },
  readinessRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  readinessLabel: { color: C.text, fontSize: 12, fontWeight: '600' },
  readinessScore: { fontSize: 22, fontWeight: 'bold' },
  progressBg: { backgroundColor: C.bg, height: 6, borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: 6, borderRadius: 3 },
  readinessComplete: { color: C.green, fontSize: 11, marginTop: 8, fontWeight: '600' },
  formCard: { backgroundColor: C.surface, borderRadius: 10, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: C.border },
  formCardTitle: { color: C.text, fontWeight: 'bold', fontSize: 13, marginBottom: 12 },
  formGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  formField: { width: '48%' },
  fieldLabel: { color: C.textSub, fontSize: 10, marginBottom: 5, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  fieldValue: { backgroundColor: C.bg, borderRadius: 6, padding: 8, borderWidth: 1, borderColor: C.border },
  fieldValueFilled: { borderColor: 'rgba(59,130,246,0.3)', backgroundColor: 'rgba(59,130,246,0.05)' },
  fieldValueText: { color: C.text, fontSize: 12 },
  fieldValueEmpty: { color: C.textMuted, fontStyle: 'italic' },

  // Alert banners
  alertBanner: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(245,158,11,0.08)', borderWidth: 1, borderColor: '#F59E0B',
    borderRadius: 8, padding: 12, marginBottom: 12, gap: 10,
  },
  alertBannerIcon: { fontSize: 20 },
  alertBannerTitle: { color: '#F59E0B', fontWeight: 'bold', fontSize: 12, marginBottom: 3 },
  alertBannerBody: { color: C.textSub, fontSize: 11, lineHeight: 15 },
  alertBannerBtn: {
    backgroundColor: '#F59E0B', paddingVertical: 6, paddingHorizontal: 12, borderRadius: 6,
  },
  alertBannerBtnText: { color: '#0F172A', fontWeight: 'bold', fontSize: 11 },

  // Docs
  docsCard: { backgroundColor: C.surface, borderRadius: 10, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: C.border },
  docRow: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: C.bg,
    borderRadius: 8, padding: 10, marginBottom: 8, borderWidth: 1, borderColor: C.border, gap: 10,
  },
  docRowValidated: { borderColor: 'rgba(16,185,129,0.3)', backgroundColor: 'rgba(16,185,129,0.04)' },
  docRowFailed: { borderColor: 'rgba(239,68,68,0.3)', backgroundColor: 'rgba(239,68,68,0.04)' },
  docIcon: { width: 30, alignItems: 'center' },
  docInfo: { flex: 1 },
  docLabel: { color: C.text, fontSize: 12, fontWeight: '600' },
  docSub: { color: C.textSub, fontSize: 10, marginTop: 2 },
  docStatus: { fontSize: 10, fontWeight: 'bold', marginTop: 3 },
  docUploadArea: {},
  uploadBtn: {
    backgroundColor: 'rgba(59,130,246,0.1)', borderWidth: 1, borderColor: 'rgba(59,130,246,0.3)',
    borderRadius: 6, paddingVertical: 5, paddingHorizontal: 10,
  },
  uploadBtnDisabled: { opacity: 0.4 },
  uploadBtnDone: { backgroundColor: 'rgba(16,185,129,0.1)', borderColor: 'rgba(16,185,129,0.3)' },
  uploadBtnText: { color: C.blue, fontSize: 11, fontWeight: '600' },

  // Payment
  payCard: {
    backgroundColor: 'rgba(16,185,129,0.06)', borderWidth: 1, borderColor: 'rgba(16,185,129,0.3)',
    borderRadius: 10, padding: 16, marginBottom: 14,
  },
  payTitle: { color: C.green, fontWeight: 'bold', fontSize: 14, marginBottom: 12 },
  payAmountRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  payAmountLabel: { color: C.textSub, fontSize: 12 },
  payAmountValue: { color: C.text, fontSize: 22, fontWeight: 'bold' },
  payMethod: { color: C.textSub, fontSize: 11, marginBottom: 14 },
  payBtn: {
    backgroundColor: C.green, borderRadius: 8, paddingVertical: 12, alignItems: 'center',
  },
  payBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 13 },

  // Certificate
  certCard: {
    backgroundColor: 'rgba(59,130,246,0.06)', borderWidth: 1, borderColor: 'rgba(59,130,246,0.3)',
    borderRadius: 10, padding: 20, marginBottom: 14, alignItems: 'center',
  },
  certEmoji: { fontSize: 36, marginBottom: 10 },
  certTitle: { color: C.text, fontSize: 16, fontWeight: 'bold', marginBottom: 6 },
  certSub: { color: C.textSub, fontSize: 12, marginBottom: 16 },
  certBtn: { backgroundColor: C.blue, borderRadius: 8, paddingVertical: 10, paddingHorizontal: 20 },
  certBtnText: { color: '#fff', fontWeight: 'bold', fontSize: 13 },

  // ── Dashboard ──
  dashTabs: { flexDirection: 'row', backgroundColor: C.bg, borderRadius: 8, padding: 3 },
  dashTab: { paddingVertical: 5, paddingHorizontal: 10, borderRadius: 6 },
  dashTabActive: { backgroundColor: C.surface, borderWidth: 1, borderColor: C.border2 },
  dashTabText: { color: C.textSub, fontSize: 11, fontWeight: '600' },
  dashTabTextActive: { color: C.blue },
  tabSectionTitle: { color: C.textSub, fontSize: 10, fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12 },

  anomalyBanner: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(239,68,68,0.1)', borderWidth: 1, borderColor: 'rgba(239,68,68,0.3)',
    borderRadius: 8, padding: 12, marginBottom: 14, gap: 10,
  },
  anomalyBannerIcon: { fontSize: 20 },
  anomalyBannerTitle: { color: C.red, fontWeight: 'bold', fontSize: 12, marginBottom: 2 },
  anomalyBannerBody: { color: C.textSub, fontSize: 11 },

  kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 16 },
  kpiCard: {
    backgroundColor: C.surface, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.border,
    width: '47.5%',
  },
  kpiIcon: { fontSize: 18, marginBottom: 6 },
  kpiValue: { fontSize: 18, fontWeight: 'bold', marginBottom: 2 },
  kpiLabel: { color: C.textSub, fontSize: 10 },

  chartCard: { backgroundColor: C.surface, borderRadius: 10, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: C.border },
  chartTitle: { color: C.text, fontWeight: 'bold', fontSize: 12, marginBottom: 12 },
  chartRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 },
  chartKey: { color: C.textSub, fontSize: 10, width: 100 },
  chartBarBg: { flex: 1, height: 6, backgroundColor: C.bg, borderRadius: 3, overflow: 'hidden' },
  chartBarFill: { height: 6, backgroundColor: C.blue, borderRadius: 3 },
  chartVal: { color: C.text, fontSize: 10, fontWeight: 'bold', width: 24, textAlign: 'right' },

  auditCard: { backgroundColor: C.surface, borderRadius: 8, padding: 10, marginBottom: 8, borderWidth: 1, borderColor: C.border },
  auditTop: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 },
  auditActor: { color: C.blue, fontWeight: 'bold', fontSize: 10 },
  auditAction: { color: C.text, fontSize: 10, flex: 1 },
  auditResultBadge: { paddingVertical: 2, paddingHorizontal: 6, borderRadius: 4 },
  resultBadgeSuccess: { backgroundColor: 'rgba(16,185,129,0.15)' },
  resultBadgeFailed:  { backgroundColor: 'rgba(239,68,68,0.15)' },
  resultBadgeBlocked: { backgroundColor: 'rgba(239,68,68,0.25)' },
  auditResultText: { fontSize: 9, fontWeight: 'bold', color: C.text },
  auditViolation: { color: '#F87171', fontSize: 9, marginBottom: 2 },
  auditTime: { color: C.textMuted, fontSize: 9 },

  emptyState: { alignItems: 'center', paddingVertical: 40 },
  emptyStateIcon: { fontSize: 32, marginBottom: 10 },
  emptyStateText: { color: C.text, fontSize: 14, fontWeight: '600', marginBottom: 6 },
  emptyStateSub: { color: C.textSub, fontSize: 12, textAlign: 'center' },

  escalCard: { backgroundColor: C.surface, borderRadius: 10, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(239,68,68,0.3)' },
  escalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  escalAppNo: { color: C.text, fontWeight: 'bold', fontSize: 13 },
  escalStatusBadge: { paddingVertical: 3, paddingHorizontal: 8, borderRadius: 20 },
  statusRejected: { backgroundColor: 'rgba(239,68,68,0.15)' },
  statusReview: { backgroundColor: 'rgba(245,158,11,0.15)' },
  escalStatusText: { fontSize: 10, fontWeight: 'bold', color: C.text },
  escalDetails: { color: C.textSub, fontSize: 11, marginBottom: 4 },
  escalTime: { color: C.textMuted, fontSize: 10, marginBottom: 10 },
  escalActions: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  escalApproveBtn: { backgroundColor: 'rgba(16,185,129,0.15)', borderWidth: 1, borderColor: C.green, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 6 },
  escalRejectBtn:  { backgroundColor: 'rgba(239,68,68,0.15)', borderWidth: 1, borderColor: C.red, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 6 },
  escalCorrectionBtn: { backgroundColor: 'rgba(245,158,11,0.15)', borderWidth: 1, borderColor: C.orange, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 6 },
  escalBtnText: { color: C.text, fontWeight: 'bold', fontSize: 11 },
});
