import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import CallSetup from './components/CallSetup';
import LiveDashboard from './components/LiveDashboard';
import PostCallSummary from './components/PostCallSummary';
import ProductionScalePanel from './components/ProductionScalePanel';
import Sidebar from './components/Sidebar';
import ApiManagement from './components/ApiManagement';
import SessionLog from './components/SessionLog';

export default function App() {
  const [viewState, setViewState] = useState('setup'); // 'setup', 'live', 'summary'
  const [callMode, setCallMode] = useState(null); // 'mode_a_upload' or 'mode_b_live'
  const [sessionId, setSessionId] = useState(null);
  const [transactionContext, setTransactionContext] = useState('general');
  const [thresholds, setThresholds] = useState({ low_max: 40, high_min: 70 });
  const [noiseReductionActive, setNoiseReductionActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isScalePanelOpen, setIsScalePanelOpen] = useState(false);
  const [activePage, setActivePage] = useState('dashboard');

  // Live Call Streaming Telemetry
  const [liveMetrics, setLiveMetrics] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [summaryData, setSummaryData] = useState(null);

  // WebSockets and Media References
  const wsStreamRef = useRef(null);
  const pcRef = useRef(null);
  const signalingWsRef = useRef(null);
  const localStreamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const [remoteStream, setRemoteStream] = useState(null);

  // Fetch initial health check & thresholds
  useEffect(() => {
    fetch('/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.active_thresholds) {
          setThresholds({
            low_max: data.active_thresholds.low_max || 40,
            high_min: data.active_thresholds.high_min || 70
          });
        }
        setNoiseReductionActive(data.noise_reduction_enabled ?? true);
      })
      .catch((err) => {
        console.warn('Backend offline or health check failed:', err);
      });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupStreams();
    };
  }, []);

  const cleanupStreams = () => {
    if (wsStreamRef.current) {
      wsStreamRef.current.close();
      wsStreamRef.current = null;
    }
    if (signalingWsRef.current) {
      signalingWsRef.current.close();
      signalingWsRef.current = null;
    }
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(t => t.stop());
      localStreamRef.current = null;
    }
    setRemoteStream(null);
  };

  // --- MODE A: Upload & Simulated Replay ---
  const handleStartModeA = async (fileOrPreset) => {
    setLoading(true);
    setErrorMessage(null);
    setHistoryData([]);
    setLiveMetrics(null);

    try {
      let resp;
      if (typeof fileOrPreset === 'string') {
        const formData = new FormData();
        formData.append('preset_name', fileOrPreset);
        formData.append('transaction_context', transactionContext);
        resp = await fetch('/calls/upload-preset', {
          method: 'POST',
          body: formData
        });
      } else {
        const formData = new FormData();
        formData.append('file', fileOrPreset);
        formData.append('transaction_context', transactionContext);
        resp = await fetch('/calls/upload', {
          method: 'POST',
          body: formData
        });
      }

      if (!resp.ok) {
        throw new Error(`Upload failed: ${resp.statusText}`);
      }

      const data = await resp.json();
      const currentSessionId = data.session_id;
      setSessionId(currentSessionId);
      setCallMode('mode_a_upload');
      setViewState('live');
      setLoading(false);

      // Connect to WebSocket stream
      connectStreamWebSocket(currentSessionId, 'mode_a_upload');
    } catch (err) {
      setLoading(false);
      setErrorMessage(`Error starting Mode A replay: ${err.message}`);
    }
  };

  // --- MODE B: Live WebRTC ---
  const handleStartModeB = async (existingRoomId = null) => {
    setLoading(true);
    setErrorMessage(null);
    setHistoryData([]);
    setLiveMetrics(null);

    try {
      let currentSessionId = existingRoomId;
      let iceServers = [{ urls: "stun:stun.l.google.com:19302" }];

      if (!currentSessionId) {
        const resp = await fetch('/calls/start-live', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transaction_context: transactionContext })
        });
        if (!resp.ok) throw new Error("Failed to start live call");
        const data = await resp.json();
        currentSessionId = data.session_id;
        if (data.ice_servers) iceServers = data.ice_servers;
      }

      setSessionId(currentSessionId);
      setCallMode('mode_b_live');
      setViewState('live');

      // 1. Get Microphone
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      localStreamRef.current = stream;

      // 2. Setup RTCPeerConnection
      const pc = new RTCPeerConnection({ iceServers });
      pcRef.current = pc;
      
      stream.getTracks().forEach(track => pc.addTrack(track, stream));

      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          setRemoteStream(event.streams[0]);
        }
      };

      // 3. Connect Signaling
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const sigUrl = `${protocol}//${window.location.host}/calls/${currentSessionId}/signaling`;
      const sigWs = new WebSocket(sigUrl);
      signalingWsRef.current = sigWs;

      sigWs.onmessage = async (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'peer_joined') {
          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);
          sigWs.send(JSON.stringify({ type: 'offer', sdp: pc.localDescription }));
        } else if (msg.type === 'offer') {
          await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          sigWs.send(JSON.stringify({ type: 'answer', sdp: pc.localDescription }));
        } else if (msg.type === 'answer') {
          await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
        } else if (msg.type === 'candidate') {
          await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
        }
      };

      pc.onicecandidate = (event) => {
        if (event.candidate && sigWs.readyState === WebSocket.OPEN) {
          sigWs.send(JSON.stringify({ type: 'candidate', candidate: event.candidate }));
        }
      };

      // 4. Start Analysis Stream & MediaRecorder
      connectStreamWebSocket(currentSessionId, 'mode_b_live', stream);
      setLoading(false);

    } catch (err) {
      setLoading(false);
      setErrorMessage(`Error starting Mode B: ${err.message}`);
    }
  };

  // Connect unified WebSocket stream
  const connectStreamWebSocket = (currentSessionId, mode, stream = null) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const streamUrl = `${protocol}//${window.location.host}/calls/${currentSessionId}/stream`;

    const ws = new WebSocket(streamUrl);
    wsStreamRef.current = ws;

    let audioContext;
    let source;
    let processor;

    ws.onopen = () => {
      if (mode === 'mode_b_live' && stream) {
        // Use AudioContext to extract raw 16kHz PCM audio instead of MediaRecorder (WebM)
        // This ensures the backend can decode it natively via np.frombuffer without ffmpeg
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        source = audioContext.createMediaStreamSource(stream);
        processor = audioContext.createScriptProcessor(4096, 1, 1);

        let sampleBuffer = [];
        let totalSamples = 0;

        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN) return;
          
          const channelData = e.inputBuffer.getChannelData(0);
          
          // Convert Float32 to Int16
          const int16Data = new Int16Array(channelData.length);
          for (let i = 0; i < channelData.length; i++) {
            let s = Math.max(-1, Math.min(1, channelData[i]));
            int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }

          sampleBuffer.push(int16Data);
          totalSamples += int16Data.length;

          // Send when we accumulate 2.5 seconds at 16kHz = 40,000 samples
          if (totalSamples >= 40000) {
            const merged = new Int16Array(totalSamples);
            let offset = 0;
            for (let b of sampleBuffer) {
              merged.set(b, offset);
              offset += b.length;
            }
            ws.send(merged.buffer);
            sampleBuffer = [];
            totalSamples = 0;
          }
        };

        source.connect(processor);
        processor.connect(audioContext.destination);

        // Save reference for cleanup
        mediaRecorderRef.current = {
          stop: () => {
            // Flush remaining samples if any
            if (totalSamples > 0 && ws.readyState === WebSocket.OPEN) {
              const merged = new Int16Array(totalSamples);
              let offset = 0;
              for (let b of sampleBuffer) {
                merged.set(b, offset);
                offset += b.length;
              }
              ws.send(merged.buffer);
              sampleBuffer = [];
              totalSamples = 0;
            }

            if (processor && source) {
              processor.disconnect();
              source.disconnect();
            }
            if (audioContext && audioContext.state !== 'closed') {
              audioContext.close();
            }
          }
        };
      }
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        setErrorMessage(data.error);
        return;
      }

      setLiveMetrics(data);
      setHistoryData((prev) => [...prev, data]);

      if (data.is_complete) {
        handleEndCall();
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket Stream Error:', err);
    };

    ws.onclose = () => {
      console.log('WebSocket Stream Closed');
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
    };
  };

  // Dynamic context change during live call
  const handleChangeContext = async (newCtx) => {
    setTransactionContext(newCtx);
    if (sessionId) {
      try {
        await fetch(`/calls/${sessionId}/context`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ transaction_context: newCtx })
        });
        if (wsStreamRef.current && wsStreamRef.current.readyState === WebSocket.OPEN) {
          wsStreamRef.current.send(JSON.stringify({ action: 'update_context', context: newCtx }));
        }
      } catch (err) {
        console.error('Failed to update context:', err);
      }
    }
  };

  // End Call & Fetch Post-Call Forensic Summary
  const handleEndCall = async () => {
    cleanupStreams();

    if (sessionId) {
      try {
        const resp = await fetch(`/calls/${sessionId}/summary`);
        if (resp.ok) {
          const data = await resp.json();
          setSummaryData(data);
        }
      } catch (err) {
        console.error('Failed to load summary:', err);
      }
    }

    setViewState('summary');
  };

  const handleReset = () => {
    cleanupStreams();
    setViewState('setup');
    setSessionId(null);
    setCallMode(null);
    setLiveMetrics(null);
    setHistoryData([]);
    setSummaryData(null);
    setErrorMessage(null);
    setActivePage('dashboard');
  };

  const handleNavigate = (page) => {
    setActivePage(page);
    if (page === 'dashboard' || page === 'workflow') {
      if (viewState !== 'live') setViewState('setup');
    }
    if (page === 'session-log') {
      if (viewState !== 'live') setViewState('summary');
    }
  };

  const handleNewSession = () => {
    cleanupStreams();
    setViewState('setup');
    setSessionId(null);
    setCallMode(null);
    setLiveMetrics(null);
    setHistoryData([]);
    setSummaryData(null);
    setErrorMessage(null);
    setActivePage('dashboard');
  };

  return (
    <div className="clay-app min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Sidebar
        activePage={activePage}
        onNavigate={handleNavigate}
        onNewSession={handleNewSession}
      />
      {/* Top Navigation */}
      <Navbar
        transactionContext={transactionContext}
        noiseReductionActive={noiseReductionActive}
        onOpenScalePanel={() => setIsScalePanelOpen(true)}
      />

      {/* Global Error Banner */}
      {errorMessage && (
        <div className="max-w-7xl mx-auto w-full px-4 pt-4">
          <div className="p-3.5 rounded-xl bg-red-950/80 border border-red-500/50 text-red-300 text-xs flex items-center justify-between">
            <span>{errorMessage}</span>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-400 hover:text-white font-bold ml-4"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Main Screen Content */}
      <main className="flex-1 flex flex-col justify-center">
        {/* Invisible audio element for playing remote stream in Mode B */}
        {remoteStream && (
          <audio
            autoPlay
            ref={audio => {
              if (audio && audio.srcObject !== remoteStream) {
                audio.srcObject = remoteStream;
              }
            }}
            className="hidden"
          />
        )}

        {viewState === 'setup' && (activePage === 'dashboard' || activePage === 'workflow') && (
          <CallSetup
            onStartModeA={handleStartModeA}
            onStartModeB={handleStartModeB}
            transactionContext={transactionContext}
            setTransactionContext={setTransactionContext}
            loading={loading}
          />
        )}

        {viewState === 'live' && (activePage === 'dashboard' || activePage === 'workflow') && (
          <LiveDashboard
            sessionId={sessionId}
            mode={callMode}
            transactionContext={transactionContext}
            onChangeContext={handleChangeContext}
            onEndCall={handleEndCall}
            liveMetrics={liveMetrics}
            historyData={historyData}
            thresholds={thresholds}
          />
        )}

        {viewState === 'summary' && activePage === 'session-log' && (
          <SessionLog
            summaryData={summaryData}
            historyData={historyData}
            onStartNew={handleNewSession}
          />
        )}

        {viewState === 'summary' && activePage !== 'session-log' && (
          <PostCallSummary
            summaryData={summaryData}
            historyData={historyData}
            onReset={handleReset}
            thresholds={thresholds}
          />
        )}

        {activePage === 'api-management' && <ApiManagement />}
      </main>

      {/* Production Scale Architecture Panel (Modal) */}
      <ProductionScalePanel
        isOpen={isScalePanelOpen}
        onClose={() => setIsScalePanelOpen(false)}
      />
    </div>
  );
}
