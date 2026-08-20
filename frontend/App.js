import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  TextInput,
  ScrollView,
  ActivityIndicator,
  useWindowDimensions,
  Platform
} from 'react-native';

const API_BASE_URL = Platform.OS === 'web' ? '' : 'http://localhost:8000';

export default function App() {
  const { width } = useWindowDimensions();
  const isLargeScreen = width >= 900;

  // App state variables
  const [currentChannel, setCurrentChannel] = useState('WhatsApp'); // WhatsApp, IVR, WebPortal
  const [sessionId, setSessionId] = useState(`session-${Math.floor(100000 + Math.random() * 900000)}`);
  
  // Conversational state
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [appStateData, setAppStateData] = useState({});
  const [appStatus, setAppStatus] = useState('START');
  const [applicationId, setApplicationId] = useState(null);
  const [missingFields, setMissingFields] = useState([]);
  const [isBlockedByOPA, setIsBlockedByOPA] = useState(false);
  const [opaBlockReason, setOpaBlockReason] = useState('');
  const [preferredLang, setPreferredLang] = useState('en');

  // Dashboard state variables
  const [metrics, setMetrics] = useState({
    total_applications: 0,
    applications_today: 0,
    completed_applications: 0,
    pending_applications: 0,
    failed_applications: 0,
    escalations: 0,
    avg_processing_time_hours: 0,
    avg_response_latency_ms: 185.0,
    payment_success_rate: 100.0,
    doc_validation_success_rate: 100.0,
    anomalies_detected: 0
  });
  const [charts, setCharts] = useState({
    services: {},
    languages: {},
    channels: {},
    statuses: {},
    blocked_requests: 0
  });
  const [auditLogs, setAuditLogs] = useState([]);
  const [pendingEscalations, setPendingEscalations] = useState([]);

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);
  const [voicePlaybackUrl, setVoicePlaybackUrl] = useState(null);

  // Loading indicator states
  const [isSending, setIsSending] = useState(false);
  const [isDashboardLoading, setIsDashboardLoading] = useState(false);

  // Scroll ref for chat threads
  const chatScrollRef = useRef();

  // Load dashboard metrics and chat history
  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000); // refresh dashboard data every 5 seconds
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollToEnd({ animated: true });
    }
  }, [chatHistory]);

  const fetchDashboardData = async () => {
    try {
      // For POC simplicity, authenticate using a seed username
      const tokenResponse = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=admin&password=admin123'
      });
      const tokenData = await tokenResponse.json();
      const token = tokenData.access_token;

      // 1. Fetch metrics
      const mRes = await fetch(`${API_BASE_URL}/api/v1/dashboard/metrics`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (mRes.ok) {
        const mData = await mRes.json();
        setMetrics(mData);
      }

      // 2. Fetch chart aggregation counts
      const cRes = await fetch(`${API_BASE_URL}/api/v1/dashboard/charts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (cRes.ok) {
        const cData = await cRes.json();
        setCharts(cData);
      }

      // 3. Fetch audit logs
      const aRes = await fetch(`${API_BASE_URL}/api/v1/dashboard/audit`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (aRes.ok) {
        const aData = await aRes.json();
        setAuditLogs(aData);
      }

      // 4. Fetch all applications to find pending escalations
      const appRes = await fetch(`${API_BASE_URL}/api/v1/applications/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (appRes.ok) {
        const appList = await appRes.json();
        const escalations = appList.filter(a => a.status === 'REJECTED' || a.status === 'UNDER_REVIEW');
        setPendingEscalations(escalations);
      }
    } catch (err) {
      console.log('Error fetching dashboard metrics:', err);
    }
  };

  const speakText = (text) => {
    if (Platform.OS === 'web' && 'speechSynthesis' in window) {
      // Cancel ongoing synthesis
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/\[Cloud Response\]/g, '').replace(/⚠️.*/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      // Select appropriate language model voice if available
      if (preferredLang === 'hi') {
        utterance.lang = 'hi-IN';
      } else if (preferredLang === 'mr') {
        utterance.lang = 'mr-IN';
      } else {
        utterance.lang = 'en-IN';
      }
      window.speechSynthesis.speak(utterance);
    }
  };

  const handleSendMessage = async (textToSend) => {
    const inputMessage = textToSend || chatInput;
    if (!inputMessage.trim()) return;

    setIsSending(true);
    setChatInput('');

    // Append to local history first
    const tempHistory = [...chatHistory, { role: 'user', content: inputMessage, classification: 'PENDING' }];
    setChatHistory(tempHistory);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/conversation/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          text: inputMessage,
          channel: currentChannel,
          language: preferredLang
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        // Update states
        setAppStatus(data.state);
        setApplicationId(data.application_id);
        setAppStateData(data.extracted_data);
        setPreferredLang(data.language);
        setMissingFields(data.missing_fields);
        setIsBlockedByOPA(data.is_blocked);
        setOpaBlockReason(data.block_reason || '');

        // Fetch refreshed history
        fetchChatHistory();
        speakText(data.text);
        fetchDashboardData();
      }
    } catch (err) {
      console.error('Error sending message:', err);
    } finally {
      setIsSending(false);
    }
  };

  const fetchChatHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/conversation/${sessionId}/history`);
      if (response.ok) {
        const history = await response.json();
        setChatHistory(history);
      }
    } catch (err) {
      console.error('Error fetching chat history:', err);
    }
  };

  // Recording Web mic simulation
  const startRecording = async () => {
    if (Platform.OS !== 'web') {
      alert('Native voice recording placeholder - Voice recording is supported fully on browsers.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/wav' });
        const playbackUrl = URL.createObjectURL(audioBlob);
        setVoicePlaybackUrl(playbackUrl);

        // Upload voice wav to backend ASR Adapter
        setIsSending(true);
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('channel', currentChannel);
        formData.append('language', preferredLang);
        formData.append('audio', audioBlob, 'user_audio_upload.wav');

        try {
          const res = await fetch(`${API_BASE_URL}/api/v1/conversation/voice`, {
            method: 'POST',
            body: formData
          });
          if (res.ok) {
            const data = await res.json();
            setAppStatus(data.state);
            setApplicationId(data.application_id);
            setAppStateData(data.extracted_data);
            setPreferredLang(data.language);
            setMissingFields(data.missing_fields);
            setIsBlockedByOPA(data.is_blocked);
            setOpaBlockReason(data.block_reason || '');

            fetchChatHistory();
            speakText(data.text);
            fetchDashboardData();
          }
        } catch (err) {
          console.error('Error processing voice message:', err);
        } finally {
          setIsSending(false);
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setAudioChunks(chunks);
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleDocumentUpload = async (docType, fileEvent) => {
    if (!applicationId) {
      alert('Start the application flow by saying hi first before uploading documents.');
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
      const res = await fetch(`${API_BASE_URL}/api/v1/applications/documents/upload`, {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        alert(`${docType.replace('_', ' ').toUpperCase()} uploaded and validated successfully! OCR Confidence: ${Math.round(data.confidence * 100)}%`);
        
        // Refresh conversation history to read any status changes
        fetchChatHistory();
        // Send a blank post to state machine to refresh steps
        handleSendMessage('Document validation progress check');
      } else {
        const errData = await res.json();
        alert(`Document verification failed: ${errData.detail}`);
      }
    } catch (err) {
      console.error('Error uploading document:', err);
    } finally {
      setIsSending(false);
    }
  };

  const handleInitiatePayment = async () => {
    if (!applicationId || !appStateData.fee) return;

    setIsSending(true);
    try {
      const initRes = await fetch(`${API_BASE_URL}/api/v1/adapters/payment/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          application_id: applicationId,
          amount: appStateData.fee,
          payment_method: 'UPI'
        })
      });

      if (initRes.ok) {
        const paymentObj = await initRes.json();
        
        // Confirm payment outcome directly using Success outcome
        const confirmRes = await fetch(`${API_BASE_URL}/api/v1/adapters/payment/${paymentObj.id}/confirm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'SUCCESS' })
        });

        if (confirmRes.ok) {
          alert('Payment completed successfully!');
          handleSendMessage('Payment confirmation check');
        }
      }
    } catch (err) {
      console.error('Payment flow error:', err);
    } finally {
      setIsSending(false);
    }
  };

  const handleOfficerAction = async (appId, action, reason) => {
    try {
      const tokenResponse = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: 'username=officer&password=officer123'
      });
      const tokenData = await tokenResponse.json();
      
      const formData = new FormData();
      formData.append('action', action);
      formData.append('reason', reason);

      const res = await fetch(`${API_BASE_URL}/api/v1/applications/${appId}/officer-action`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${tokenData.access_token}` },
        body: formData
      });

      if (res.ok) {
        alert(`Application successfully ${action.toLowerCase()}ed by Officer.`);
        fetchDashboardData();
        fetchChatHistory();
      }
    } catch (err) {
      console.error('Error resolving escalated application:', err);
    }
  };

  // Helper template button actions
  const triggerDialectVoiceCommand = async (dialectCode) => {
    let audioName = '';
    if (dialectCode === 'hi') {
      audioName = 'mere_bete_ke_college_admission_ke_liye_ncl_certificate_chahiye.wav';
    } else if (dialectCode === 'mr') {
      audioName = 'mazya_mulachya_admission_sathi_ncl_dakhla_hawa.mp3';
    } else if (dialectCode === 'lack_proof') {
      audioName = 'utpannacha_dakhla_nahiye.mp3';
    } else if (dialectCode === 'start_income') {
      audioName = 'ho_suru_kara.wav';
    }

    setIsSending(true);
    // Submit mock audio filename to test simulated indic ASR dialect transcription
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('channel', currentChannel);
    formData.append('language', preferredLang);
    
    // We send an empty audio blob with standard dialect filenames to trigger local IndicASR mapping rules
    const emptyBlob = new Blob([''], { type: 'audio/wav' });
    formData.append('audio', emptyBlob, audioName);

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/conversation/voice`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setAppStatus(data.state);
        setApplicationId(data.application_id);
        setAppStateData(data.extracted_data);
        setPreferredLang(data.language);
        setMissingFields(data.missing_fields);
        setIsBlockedByOPA(data.is_blocked);
        setOpaBlockReason(data.block_reason || '');

        fetchChatHistory();
        speakText(data.text);
        fetchDashboardData();
      }
    } catch (err) {
      console.error('Error processing dialect voice simulation:', err);
    } finally {
      setIsSending(false);
    }
  };

  // Calculate dynamic progress values
  const getReadinessProgress = () => {
    return appStateData.readiness_score || 0;
  };

  const getProgressColor = (score) => {
    if (score >= 100) return '#10B981'; // Green
    if (score >= 90) return '#3B82F6'; // Blue
    if (score >= 80) return '#F59E0B'; // Orange
    return '#EF4444'; // Red
  };

  return (
    <View style={styles.appContainer}>
      {/* Header Banner */}
      <View style={styles.header}>
        <View style={styles.headerTitleRow}>
          <Text style={styles.crestIcon}>🏛️</Text>
          <View>
            <Text style={styles.headerTitle}>MAHA-REVENUE SERVICES PLATFORM</Text>
            <Text style={styles.headerSubtitle}>Government of Maharashtra • Channel-Agnostic AI POC</Text>
          </View>
        </View>
        <View style={styles.headerControls}>
          <Text style={styles.sessionBadge}>Session: {sessionId}</Text>
          <TouchableOpacity style={styles.resetButton} onPress={() => {
            setSessionId(`session-${Math.floor(100000 + Math.random() * 900000)}`);
            setChatHistory([]);
            setAppStateData({});
            setAppStatus('START');
            setApplicationId(null);
            setMissingFields([]);
            setIsBlockedByOPA(false);
          }}>
            <Text style={styles.resetButtonText}>🔄 Reset Flow</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Main Grid Content */}
      <View style={[styles.mainLayout, { flexDirection: isLargeScreen ? 'row' : 'column' }]}>
        
        {/* Left Section - Citizen Channel Simulator */}
        <View style={[styles.sectionContainer, { flex: isLargeScreen ? 1.2 : 0 }]}>
          <View style={styles.sectionHeaderRow}>
            <Text style={styles.sectionTitle}>Omnichannel simulator</Text>
            <View style={styles.channelTabs}>
              {['WhatsApp', 'IVR', 'WebPortal'].map((ch) => (
                <TouchableOpacity
                  key={ch}
                  style={[styles.channelTabButton, currentChannel === ch && styles.channelTabActive]}
                  onPress={() => {
                    setCurrentChannel(ch);
                    // Sync active channel to state machine if session is active
                    if (applicationId) {
                      handleSendMessage(`Switching channel simulation to ${ch}`);
                    }
                  }}
                >
                  <Text style={[styles.channelTabText, currentChannel === ch && styles.channelTabTextActive]}>
                    {ch === 'WhatsApp' ? '💬 WhatsApp' : ch === 'IVR' ? '📞 IVR Voice' : '🌐 Web Portal'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {/* Render Active Channel Simulator */}
          <View style={styles.simulatorBody}>
            {currentChannel === 'WhatsApp' && (
              <View style={styles.whatsappWrapper}>
                <View style={styles.whatsappHeader}>
                  <Text style={styles.whatsappHeaderTitle}>🟢 Maha-Revenue Bot (Online)</Text>
                  <Text style={styles.whatsappHeaderLanguage}>Lang: {preferredLang.toUpperCase()}</Text>
                </View>

                {/* WhatsApp Chat Thread */}
                <ScrollView 
                  style={styles.chatThread} 
                  ref={chatScrollRef}
                  contentContainerStyle={{ paddingVertical: 10 }}
                >
                  {chatHistory.length === 0 ? (
                    <Text style={styles.emptyChatText}>Send a message (e.g. "hi" or "NCL Certificate") to begin.</Text>
                  ) : (
                    chatHistory.map((msg, index) => (
                      <View 
                        key={index} 
                        style={[
                          styles.messageBubble, 
                          msg.role === 'user' ? styles.userBubble : styles.assistantBubble
                        ]}
                      >
                        <Text style={styles.messageText}>{msg.content}</Text>
                        <View style={styles.messageMetaRow}>
                          <Text style={styles.messageTime}>
                            {msg.classification && (
                              <Text style={[
                                styles.classificationBadge,
                                msg.classification === 'SENSITIVE' ? styles.badgeSensitive : 
                                msg.classification === 'RESTRICTED' ? styles.badgeRestricted : styles.badgePublic
                              ]}>
                                {msg.classification} • 
                              </Text>
                            )}
                            {new Date(msg.timestamp || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </Text>
                        </View>
                      </View>
                    ))
                  )}
                  {isSending && (
                    <ActivityIndicator size="small" color="#6B7280" style={{ marginVertical: 10 }} />
                  )}
                </ScrollView>

                {/* Dialect Voice Command Presets */}
                <View style={styles.presetsContainer}>
                  <Text style={styles.presetsLabel}>Simulate Dialect Audio Inputs:</Text>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.presetsScroll}>
                    <TouchableOpacity style={styles.presetButton} onPress={() => triggerDialectVoiceCommand('hi')}>
                      <Text style={styles.presetButtonText}>🗣️ Hindi rural: "Mere bete ke admission ke..."</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={styles.presetButton} onPress={() => triggerDialectVoiceCommand('mr')}>
                      <Text style={styles.presetButtonText}>🗣️ Marathi Vidarbha: "NCL दाखला हवा आहे"</Text>
                    </TouchableOpacity>
                  </ScrollView>
                </View>

                {/* Input Area */}
                <View style={styles.inputArea}>
                  <TouchableOpacity
                    style={[styles.micButton, isRecording && styles.micButtonActive]}
                    onPressIn={startRecording}
                    onPressOut={stopRecording}
                  >
                    <Text style={styles.micButtonText}>{isRecording ? '🔴' : '🎤'}</Text>
                  </TouchableOpacity>
                  
                  <TextInput
                    style={styles.chatTextInput}
                    placeholder="Type in Marathi (मराठी), Hindi (हिंदी) or English..."
                    placeholderTextColor="#9CA3AF"
                    value={chatInput}
                    onChangeText={setChatInput}
                    onSubmitEditing={() => handleSendMessage()}
                  />
                  
                  <TouchableOpacity style={styles.sendButton} onPress={() => handleSendMessage()}>
                    <Text style={styles.sendButtonText}>Send</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {currentChannel === 'IVR' && (
              <View style={styles.ivrWrapper}>
                <View style={styles.ivrVisualizer}>
                  <Text style={styles.ivrPhoneIcon}>📞</Text>
                  <Text style={styles.ivrStatusText}>ACTIVE VOICE CHANNEL CONNECTION</Text>
                  <Text style={styles.ivrLanguageText}>Assigned Language: {preferredLang.toUpperCase()}</Text>

                  {/* Speakback Narration Box */}
                  <View style={styles.ivrNarrationBox}>
                    <Text style={styles.ivrNarrationTitle}>🔊 Current Audio Output (TTS):</Text>
                    <Text style={styles.ivrNarrationText}>
                      {chatHistory.filter(m => m.role === 'assistant').slice(-1)[0]?.content || "Please press 1 for English, 2 for Hindi, or say your query."}
                    </Text>
                  </View>
                </View>

                {/* ASR Voice simulator */}
                <View style={styles.ivrControlRow}>
                  <TouchableOpacity 
                    style={[styles.ivrRecordBtn, isRecording && styles.ivrRecordBtnActive]}
                    onPress={isRecording ? stopRecording : startRecording}
                  >
                    <Text style={styles.ivrRecordBtnText}>
                      {isRecording ? '⏹️ Stop Speaking' : '🎤 Speak (IndicASR)'}
                    </Text>
                  </TouchableOpacity>
                  
                  <TouchableOpacity style={styles.ivrKeypadBtn} onPress={() => handleSendMessage('1')}>
                    <Text style={styles.ivrKeypadBtnText}>Dial [1]</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.ivrKeypadBtn} onPress={() => handleSendMessage('2')}>
                    <Text style={styles.ivrKeypadBtnText}>Dial [2]</Text>
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {currentChannel === 'WebPortal' && (
              <View style={styles.portalWrapper}>
                <ScrollView contentContainerStyle={{ padding: 15 }}>
                  <Text style={styles.portalTitle}>Department of Revenue & Forest</Text>
                  <Text style={styles.portalSubtitle}>Online Form Submission (Self-Reflecting Sync)</Text>

                  {/* Readiness Indicator Banner */}
                  <View style={styles.readinessContainer}>
                    <View style={styles.readinessHeader}>
                      <Text style={styles.readinessLabel}>Form Submission Readiness Score:</Text>
                      <Text style={[styles.readinessScoreVal, { color: getProgressColor(getReadinessProgress()) }]}>
                        {getReadinessProgress()}/100
                      </Text>
                    </View>
                    <View style={styles.progressBarBackground}>
                      <View style={[
                        styles.progressBarFill, 
                        { width: `${getReadinessProgress()}%`, backgroundColor: getProgressColor(getReadinessProgress()) }
                      ]} />
                    </View>
                  </View>

                  {/* Form fields synced with chatbot extracted entities */}
                  <View style={styles.formGrid}>
                    <View style={styles.formGroup}>
                      <Text style={styles.fieldLabel}>Applicant Full Name</Text>
                      <TextInput 
                        style={styles.fieldInput} 
                        value={appStateData.full_name || ''} 
                        placeholder="Pending extract..."
                        editable={false}
                      />
                    </View>

                    <View style={styles.formGroup}>
                      <Text style={styles.fieldLabel}>District Resident</Text>
                      <TextInput 
                        style={styles.fieldInput} 
                        value={appStateData.district || ''} 
                        placeholder="Pending extract..."
                        editable={false}
                      />
                    </View>

                    <View style={styles.formGroup}>
                      <Text style={styles.fieldLabel}>Certified Annual Income (INR)</Text>
                      <TextInput 
                        style={styles.fieldInput} 
                        value={appStateData.annual_income ? String(appStateData.annual_income) : ''} 
                        placeholder="Pending extract..."
                        editable={false}
                      />
                    </View>

                    <View style={styles.formGroup}>
                      <Text style={styles.fieldLabel}>Citizen Content & Aadhaar e-Consent</Text>
                      <Text style={styles.consentStatusText}>
                        {appStateData.consent ? '✅ Given (Authenticated)' : '❌ Awaiting Consent'}
                      </Text>
                    </View>
                  </View>

                  {/* Document upload fields */}
                  <View style={styles.documentUploadSection}>
                    <Text style={styles.docSectionTitle}>Required Verification Evidence</Text>
                    
                    {/* Prerequisite loop self-recovering trigger */}
                    {appStateData.lacks_income_proof && !appStateData.prerequisite_completed && (
                      <View style={styles.prerequisiteAlert}>
                        <Text style={styles.prerequisiteAlertText}>
                          ⚠️ Lacking Income Proof! System initialized a nested **Income Certificate** application.
                        </Text>
                        <TouchableOpacity style={styles.simulatePrerequisiteBtn} onPress={() => triggerDialectVoiceCommand('start_income')}>
                          <Text style={styles.simulatePrerequisiteBtnText}>Simulate: "Haan, start karo"</Text>
                        </TouchableOpacity>
                      </View>
                    )}

                    <View style={styles.docRow}>
                      <View style={styles.docInfo}>
                        <Text style={styles.docName}>Identity Proof (Aadhaar Card)</Text>
                        <Text style={styles.docStatusBadge}>
                          {appStateData.documents_uploaded?.identity_proof || 'Awaiting Upload'}
                        </Text>
                      </View>
                      {Platform.OS === 'web' && (
                        <input 
                          type="file" 
                          accept="image/*,application/pdf" 
                          onChange={(e) => handleDocumentUpload('identity_proof', e)} 
                        />
                      )}
                    </View>

                    <View style={styles.docRow}>
                      <View style={styles.docInfo}>
                        <Text style={styles.docName}>Caste Proof (Community/School Leaving)</Text>
                        <Text style={styles.docStatusBadge}>
                          {appStateData.documents_uploaded?.caste_proof || 'Awaiting Upload'}
                        </Text>
                      </View>
                      {Platform.OS === 'web' && (
                        <input 
                          type="file" 
                          accept="image/*,application/pdf" 
                          onChange={(e) => handleDocumentUpload('caste_proof', e)} 
                        />
                      )}
                    </View>

                    <View style={styles.docRow}>
                      <View style={styles.docInfo}>
                        <Text style={styles.docName}>Income Proof (Form 16 or Salary Slip)</Text>
                        <Text style={styles.docStatusBadge}>
                          {appStateData.documents_uploaded?.income_proof || 'Awaiting Upload'}
                        </Text>
                      </View>
                      {Platform.OS === 'web' && (
                        <input 
                          type="file" 
                          accept="image/*,application/pdf" 
                          disabled={appStateData.lacks_income_proof}
                          onChange={(e) => handleDocumentUpload('income_proof', e)} 
                        />
                      )}
                    </View>
                  </View>

                  {/* DOB Correction Flow (Image 1 check) */}
                  {appStateData.dob_mismatch_detected && !appStateData.dob_mismatch_resolved && (
                    <View style={styles.mismatchAlertBox}>
                      <Text style={styles.mismatchText}>
                        🚨 **OCR Conflict Mismatch Flagged:** Aadhaar DOB (12-05-2002) does not match Caste Proof DOB (12-05-2003).
                      </Text>
                      <TouchableOpacity style={styles.mismatchResolveBtn} onPress={() => handleSendMessage('12-05-2002')}>
                        <Text style={styles.mismatchResolveBtnText}>Confirm correct DOB is 12-05-2002</Text>
                      </TouchableOpacity>
                    </View>
                  )}

                  {/* Payment stage */}
                  {appStatus === 'PAYMENT' && (
                    <View style={styles.paymentSection}>
                      <Text style={styles.paymentTitle}>Government Fee Payment Portal</Text>
                      <Text style={styles.paymentText}>Required Application Processing Fee: **Rs. {appStateData.fee || 50.0}**</Text>
                      <TouchableOpacity style={styles.payBtn} onPress={handleInitiatePayment}>
                        <Text style={styles.payBtnText}>🔒 Authorize UPI Payment Transaction</Text>
                      </TouchableOpacity>
                    </View>
                  )}

                  {/* Download certificate */}
                  {appStatus === 'CERTIFICATE_GENERATION' && (
                    <View style={styles.certificateReadyBox}>
                      <Text style={styles.certReadyText}>🎉 CONGRATULATIONS! Your application was approved.</Text>
                      <TouchableOpacity 
                        style={styles.downloadBtn} 
                        onPress={() => window.open(`${API_BASE_URL}/api/v1/applications/${applicationId}/certificate`)}
                      >
                        <Text style={styles.downloadBtnText}>📄 Download Generated Certificate</Text>
                      </TouchableOpacity>
                    </View>
                  )}
                </ScrollView>
              </View>
            )}
          </View>
        </View>

        {/* Right Section - Auditor/Officer Dashboard & Data sovereignty */}
        <View style={[styles.sectionContainer, { flex: isLargeScreen ? 1 : 0 }]}>
          <Text style={styles.sectionTitle}>Officer Analytics & Governance Dashboard</Text>
          
          <ScrollView contentContainerStyle={{ padding: 15 }}>
            {/* KPI Metrics */}
            <Text style={styles.subSectionTitle}>System Key Performance Indicators</Text>
            <View style={styles.kpiGrid}>
              <View style={styles.kpiCard}>
                <Text style={styles.kpiValue}>{metrics.total_applications}</Text>
                <Text style={styles.kpiLabel}>Total Submissions</Text>
              </View>
              <View style={styles.kpiCard}>
                <Text style={styles.kpiValue}>{metrics.avg_processing_time_hours} hrs</Text>
                <Text style={styles.kpiLabel}>Avg Process Time</Text>
              </View>
              <View style={styles.kpiCard}>
                <Text style={styles.kpiValue}>{metrics.payment_success_rate}%</Text>
                <Text style={styles.kpiLabel}>Payment Success</Text>
              </View>
              <View style={styles.kpiCard}>
                <Text style={styles.kpiValue}>{metrics.doc_validation_success_rate}%</Text>
                <Text style={styles.kpiLabel}>OCR Pass Rate</Text>
              </View>
            </View>

            {/* ML Anomaly Alert */}
            {metrics.anomalies_detected > 0 && (
              <View style={styles.anomalyAlert}>
                <Text style={styles.anomalyTitle}>🛡️ Anomaly Engine Flag (IsolationForest)</Text>
                <Text style={styles.anomalyBody}>
                  {metrics.anomalies_detected} submissions flagged for suspicious profiles (excessive income limits / repeated workflow failures).
                </Text>
              </View>
            )}

            {/* Live Data Sovereignty Audits */}
            <Text style={styles.subSectionTitle}>Local Data Sovereignty Guard logs</Text>
            <View style={styles.auditLogWrapper}>
              {auditLogs.length === 0 ? (
                <Text style={styles.noAuditsText}>Awaiting events...</Text>
              ) : (
                auditLogs.map((log, idx) => (
                  <View key={idx} style={styles.auditRow}>
                    <View style={styles.auditRowHeader}>
                      <Text style={styles.auditActor}>{log.actor.toUpperCase()}</Text>
                      <Text style={styles.auditAction}>{log.action}</Text>
                      <Text style={[
                        styles.auditResult, 
                        log.result === 'BLOCKED' ? styles.resultBlocked : styles.resultSuccess
                      ]}>
                        {log.result}
                      </Text>
                    </View>
                    {log.metadata_json?.reasons && (
                      <Text style={styles.auditReason}>
                        Violation: {log.metadata_json.reasons.join(', ')}
                      </Text>
                    )}
                  </View>
                ))
              )}
            </View>

            {/* Officer Escalation queue */}
            <Text style={styles.subSectionTitle}>Officer Verification Queue ({pendingEscalations.length})</Text>
            <View style={styles.escalationWrapper}>
              {pendingEscalations.length === 0 ? (
                <Text style={styles.noEscalationsText}>No pending escalated applications.</Text>
              ) : (
                pendingEscalations.map((app) => (
                  <View key={app.id} style={styles.escalationCard}>
                    <Text style={styles.escAppNo}>{app.application_no} (ID: {app.id})</Text>
                    <Text style={styles.escDetails}>Service: {app.service_id.toUpperCase()} • Status: {app.status}</Text>
                    <View style={styles.escActions}>
                      <TouchableOpacity 
                        style={[styles.escBtn, styles.escApproveBtn]}
                        onPress={() => handleOfficerAction(app.id, 'APPROVE', 'Passed manual audit.')}
                      >
                        <Text style={styles.escBtnText}>Approve</Text>
                      </TouchableOpacity>
                      <TouchableOpacity 
                        style={[styles.escBtn, styles.escRejectBtn]}
                        onPress={() => handleOfficerAction(app.id, 'REJECT', 'Rejected by officer check.')}
                      >
                        <Text style={styles.escBtnText}>Reject</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ))
              )}
            </View>
          </ScrollView>
        </View>

      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  appContainer: {
    flex: 1,
    backgroundColor: '#0F172A', // Navy/slate background
    color: '#F8FAFC'
  },
  header: {
    backgroundColor: '#1E293B',
    paddingVertical: 15,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap'
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center'
  },
  crestIcon: {
    fontSize: 28,
    marginRight: 10
  },
  headerTitle: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: 'bold',
    letterSpacing: 1
  },
  headerSubtitle: {
    color: '#94A3B8',
    fontSize: 12
  },
  headerControls: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 5
  },
  sessionBadge: {
    color: '#3B82F6',
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6,
    fontSize: 12,
    marginRight: 10
  },
  resetButton: {
    backgroundColor: '#334155',
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 6
  },
  resetButtonText: {
    color: '#F8FAFC',
    fontSize: 12
  },
  mainLayout: {
    flex: 1,
    backgroundColor: '#0F172A'
  },
  sectionContainer: {
    backgroundColor: 'rgba(30, 41, 59, 0.5)',
    borderColor: '#334155',
    borderWidth: 1,
    margin: 10,
    borderRadius: 12,
    overflow: 'hidden'
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
    backgroundColor: '#1E293B',
    borderBottomColor: '#334155',
    borderBottomWidth: 1,
    flexWrap: 'wrap'
  },
  sectionTitle: {
    color: '#F8FAFC',
    fontSize: 16,
    fontWeight: 'bold',
    padding: 15
  },
  channelTabs: {
    flexDirection: 'row',
    backgroundColor: '#0F172A',
    borderRadius: 8,
    padding: 2
  },
  channelTabButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6
  },
  channelTabActive: {
    backgroundColor: '#1E293B'
  },
  channelTabText: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '600'
  },
  channelTabTextActive: {
    color: '#3B82F6'
  },
  simulatorBody: {
    flex: 1,
    minHeight: 400
  },
  whatsappWrapper: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100%'
  },
  whatsappHeader: {
    backgroundColor: '#075E54',
    padding: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  whatsappHeaderTitle: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 13
  },
  whatsappHeaderLanguage: {
    color: '#D1FAE5',
    fontSize: 11
  },
  chatThread: {
    flex: 1,
    backgroundColor: '#070D19',
    paddingHorizontal: 15
  },
  emptyChatText: {
    color: '#6B7280',
    textAlign: 'center',
    marginVertical: 40,
    fontSize: 13
  },
  messageBubble: {
    maxWidth: '80%',
    padding: 10,
    borderRadius: 8,
    marginVertical: 5
  },
  userBubble: {
    backgroundColor: '#1E3A8A',
    alignSelf: 'flex-end',
    borderBottomRightRadius: 0
  },
  assistantBubble: {
    backgroundColor: '#334155',
    alignSelf: 'flex-start',
    borderBottomLeftRadius: 0
  },
  messageText: {
    color: '#F8FAFC',
    fontSize: 13
  },
  messageMetaRow: {
    marginTop: 4,
    alignItems: 'flex-end'
  },
  messageTime: {
    color: '#94A3B8',
    fontSize: 9
  },
  classificationBadge: {
    fontSize: 8,
    fontWeight: 'bold'
  },
  badgeSensitive: {
    color: '#EF4444' // Red
  },
  badgeRestricted: {
    color: '#F59E0B' // Orange
  },
  badgePublic: {
    color: '#10B981' // Green
  },
  presetsContainer: {
    padding: 8,
    backgroundColor: '#1E293B',
    borderTopWidth: 1,
    borderTopColor: '#334155'
  },
  presetsLabel: {
    color: '#94A3B8',
    fontSize: 11,
    marginBottom: 4
  },
  presetsScroll: {
    flexDirection: 'row'
  },
  presetButton: {
    backgroundColor: '#0F172A',
    borderRadius: 6,
    paddingVertical: 5,
    paddingHorizontal: 10,
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#475569'
  },
  presetButtonText: {
    color: '#3B82F6',
    fontSize: 11
  },
  inputArea: {
    flexDirection: 'row',
    padding: 10,
    backgroundColor: '#1E293B',
    alignItems: 'center'
  },
  micButton: {
    backgroundColor: '#334155',
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10
  },
  micButtonActive: {
    backgroundColor: '#EF4444'
  },
  micButtonText: {
    fontSize: 16
  },
  chatTextInput: {
    flex: 1,
    backgroundColor: '#0F172A',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 8,
    color: '#F8FAFC',
    borderWidth: 1,
    borderColor: '#475569',
    fontSize: 13
  },
  sendButton: {
    marginLeft: 10,
    backgroundColor: '#3B82F6',
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 15
  },
  sendButtonText: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 13
  },
  ivrWrapper: {
    flex: 1,
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#070D19'
  },
  ivrVisualizer: {
    width: '100%',
    backgroundColor: '#1E293B',
    borderRadius: 12,
    padding: 25,
    alignItems: 'center',
    borderColor: '#334155',
    borderWidth: 1
  },
  ivrPhoneIcon: {
    fontSize: 48,
    marginBottom: 10
  },
  ivrStatusText: {
    color: '#10B981',
    fontWeight: 'bold',
    fontSize: 13,
    marginBottom: 5
  },
  ivrLanguageText: {
    color: '#94A3B8',
    fontSize: 11,
    marginBottom: 20
  },
  ivrNarrationBox: {
    backgroundColor: '#0F172A',
    width: '100%',
    padding: 15,
    borderRadius: 8,
    borderColor: '#334155',
    borderWidth: 1
  },
  ivrNarrationTitle: {
    color: '#3B82F6',
    fontWeight: 'bold',
    fontSize: 12,
    marginBottom: 5
  },
  ivrNarrationText: {
    color: '#F8FAFC',
    fontSize: 13,
    lineHeight: 18
  },
  ivrControlRow: {
    flexDirection: 'row',
    marginTop: 20,
    alignItems: 'center'
  },
  ivrRecordBtn: {
    backgroundColor: '#EF4444',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 24,
    marginRight: 10
  },
  ivrRecordBtnActive: {
    backgroundColor: '#10B981'
  },
  ivrRecordBtnText: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 13
  },
  ivrKeypadBtn: {
    backgroundColor: '#334155',
    paddingVertical: 12,
    paddingHorizontal: 15,
    borderRadius: 8,
    marginRight: 8
  },
  ivrKeypadBtnText: {
    color: '#F8FAFC',
    fontWeight: '600',
    fontSize: 13
  },
  portalWrapper: {
    flex: 1,
    backgroundColor: '#070D19'
  },
  portalTitle: {
    color: '#F8FAFC',
    fontSize: 15,
    fontWeight: 'bold'
  },
  portalSubtitle: {
    color: '#94A3B8',
    fontSize: 12,
    marginBottom: 15
  },
  readinessContainer: {
    backgroundColor: '#1E293B',
    padding: 15,
    borderRadius: 8,
    borderColor: '#334155',
    borderWidth: 1,
    marginBottom: 20
  },
  readinessHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8
  },
  readinessLabel: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '600'
  },
  readinessScoreVal: {
    fontSize: 14,
    fontWeight: 'bold'
  },
  progressBarBackground: {
    backgroundColor: '#0F172A',
    height: 8,
    borderRadius: 4,
    overflow: 'hidden'
  },
  progressBarFill: {
    height: 8
  },
  formGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between'
  },
  formGroup: {
    width: '48%',
    marginBottom: 15
  },
  fieldLabel: {
    color: '#94A3B8',
    fontSize: 11,
    marginBottom: 5
  },
  fieldInput: {
    backgroundColor: '#1E293B',
    borderColor: '#334155',
    borderWidth: 1,
    borderRadius: 6,
    padding: 8,
    color: '#F8FAFC',
    fontSize: 12
  },
  consentStatusText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 5
  },
  documentUploadSection: {
    marginTop: 15,
    borderTopWidth: 1,
    borderTopColor: '#334155',
    paddingTop: 15
  },
  docSectionTitle: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 13,
    marginBottom: 10
  },
  prerequisiteAlert: {
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    borderColor: '#F59E0B',
    borderWidth: 1,
    borderRadius: 6,
    padding: 10,
    marginBottom: 15
  },
  prerequisiteAlertText: {
    color: '#F59E0B',
    fontSize: 11,
    lineHeight: 16
  },
  simulatePrerequisiteBtn: {
    backgroundColor: '#F59E0B',
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 4,
    marginTop: 8,
    alignSelf: 'flex-start'
  },
  simulatePrerequisiteBtnText: {
    color: '#0F172A',
    fontWeight: 'bold',
    fontSize: 11
  },
  docRow: {
    backgroundColor: '#1E293B',
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap'
  },
  docInfo: {
    flex: 1,
    marginRight: 10
  },
  docName: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '600'
  },
  docStatusBadge: {
    color: '#94A3B8',
    fontSize: 10
  },
  mismatchAlertBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderColor: '#EF4444',
    borderWidth: 1,
    padding: 12,
    borderRadius: 8,
    marginVertical: 15
  },
  mismatchText: {
    color: '#EF4444',
    fontSize: 11,
    lineHeight: 16
  },
  mismatchResolveBtn: {
    backgroundColor: '#EF4444',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    marginTop: 8,
    alignSelf: 'flex-start'
  },
  mismatchResolveBtnText: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 11
  },
  paymentSection: {
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderColor: '#10B981',
    borderWidth: 1,
    padding: 15,
    borderRadius: 8,
    marginTop: 20
  },
  paymentTitle: {
    color: '#10B981',
    fontWeight: 'bold',
    fontSize: 13,
    marginBottom: 5
  },
  paymentText: {
    color: '#F8FAFC',
    fontSize: 12,
    marginBottom: 12
  },
  payBtn: {
    backgroundColor: '#10B981',
    paddingVertical: 8,
    paddingHorizontal: 15,
    borderRadius: 6,
    alignItems: 'center'
  },
  payBtnText: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 12
  },
  certificateReadyBox: {
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    borderColor: '#3B82F6',
    borderWidth: 1,
    padding: 15,
    borderRadius: 8,
    marginTop: 20
  },
  certReadyText: {
    color: '#3B82F6',
    fontWeight: 'bold',
    fontSize: 13,
    marginBottom: 10
  },
  downloadBtn: {
    backgroundColor: '#3B82F6',
    paddingVertical: 8,
    paddingHorizontal: 15,
    borderRadius: 6,
    alignItems: 'center'
  },
  downloadBtnText: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 12
  },
  subSectionTitle: {
    color: '#3B82F6',
    fontWeight: 'bold',
    fontSize: 12,
    marginTop: 20,
    marginBottom: 10,
    textTransform: 'uppercase',
    letterSpacing: 1
  },
  kpiGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between'
  },
  kpiCard: {
    backgroundColor: '#1E293B',
    width: '48%',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
    borderColor: '#334155',
    borderWidth: 1
  },
  kpiValue: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: 'bold'
  },
  kpiLabel: {
    color: '#94A3B8',
    fontSize: 10
  },
  anomalyAlert: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderColor: '#EF4444',
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginVertical: 10
  },
  anomalyTitle: {
    color: '#EF4444',
    fontWeight: 'bold',
    fontSize: 12,
    marginBottom: 4
  },
  anomalyBody: {
    color: '#F8FAFC',
    fontSize: 11,
    lineHeight: 16
  },
  auditLogWrapper: {
    backgroundColor: '#070D19',
    borderRadius: 8,
    padding: 10,
    maxHeight: 250,
    overflow: 'scroll',
    borderColor: '#334155',
    borderWidth: 1
  },
  noAuditsText: {
    color: '#6B7280',
    fontSize: 11,
    textAlign: 'center',
    marginVertical: 20
  },
  auditRow: {
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
    paddingVertical: 8
  },
  auditRowHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  auditActor: {
    color: '#3B82F6',
    fontWeight: 'bold',
    fontSize: 10
  },
  auditAction: {
    color: '#FFF',
    fontSize: 10
  },
  auditResult: {
    fontWeight: 'bold',
    fontSize: 9,
    paddingVertical: 1,
    paddingHorizontal: 4,
    borderRadius: 4
  },
  resultBlocked: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    color: '#EF4444'
  },
  resultSuccess: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    color: '#10B981'
  },
  auditReason: {
    color: '#EF4444',
    fontSize: 9,
    marginTop: 2
  },
  escalationWrapper: {
    marginTop: 5
  },
  noEscalationsText: {
    color: '#6B7280',
    fontSize: 11,
    textAlign: 'center',
    marginVertical: 20
  },
  escalationCard: {
    backgroundColor: '#1E293B',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
    borderColor: '#EF4444',
    borderWidth: 1
  },
  escAppNo: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: 'bold'
  },
  escDetails: {
    color: '#94A3B8',
    fontSize: 11,
    marginVertical: 4
  },
  escActions: {
    flexDirection: 'row',
    marginTop: 8
  },
  escBtn: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 4,
    marginRight: 8
  },
  escApproveBtn: {
    backgroundColor: '#10B981'
  },
  escRejectBtn: {
    backgroundColor: '#EF4444'
  },
  escBtnText: {
    color: '#FFF',
    fontWeight: 'bold',
    fontSize: 11
  }
});
