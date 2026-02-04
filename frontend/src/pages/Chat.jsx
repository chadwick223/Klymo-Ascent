import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import api, { endpoints, getDeviceId } from '../api';
import { Send, LogOut, ArrowRight, Flag, X, Sparkles } from 'lucide-react';
import './Chat.css'; // Import the new CSS

const Chat = () => {
    const { chatId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const deviceId = getDeviceId();

    // State
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState('');
    const [isActive, setIsActive] = useState(true);
    const [connecting, setConnecting] = useState(true);
    const [partnerStatus, setPartnerStatus] = useState('Connected');

    // Report State
    const [showReport, setShowReport] = useState(false);
    const [reportReason, setReportReason] = useState('');
    const [reportSubmitting, setReportSubmitting] = useState(false);
    const [partnerId, setPartnerId] = useState(location.state?.partnerId || null);

    // Refs
    const messagesEndRef = useRef(null);
    const eventSourceRef = useRef(null);

    // Fetch Partner ID if missing
    useEffect(() => {
        if (!partnerId && deviceId) {
            const fetchPartner = async () => {
                try {
                    const res = await api.get(endpoints.matchStatus(deviceId));
                    if (res.data.status === 'matched' && res.data.chat_id === chatId) {
                        setPartnerId(res.data.partner_id);
                    }
                } catch (e) {
                    console.error("Failed to fetch partner details", e);
                }
            };
            fetchPartner();
        }
    }, [partnerId, deviceId, chatId]);

    const handleReport = async () => {
        if (!reportReason.trim() || reportReason.length < 5) {
            alert("Please provide a reason (min 5 chars).");
            return;
        }
        setReportSubmitting(true);
        try {
            await api.post(endpoints.reportUser, {
                device_id: deviceId,
                session_id: chatId,
                reported: partnerId,
                reason: reportReason
            });
            alert("User reported. Leaving chat.");
            setShowReport(false);
            handleLeave();
        } catch (err) {
            console.error("Report failed:", err);
            alert("Failed to submit report.");
        } finally {
            setReportSubmitting(false);
        }
    };

    useEffect(() => {
        if (!chatId || !deviceId) return;
        console.log(`Setting up SSE for chat ${chatId}`);
        const url = `${api.defaults.baseURL}/chat/${chatId}/stream/?device_id=${deviceId}`;

        eventSourceRef.current = new EventSource(url);

        eventSourceRef.current.onopen = () => setConnecting(false);
        eventSourceRef.current.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'ping') return;

                if (data.type === 'chat_ended') {
                    setIsActive(false);
                    setPartnerStatus("Partner disconnected");
                    setMessages(prev => [...prev, { type: 'system', text: 'Partner has left the chat.' }]);
                } else {
                    setMessages(prev => {
                        const exists = prev.some(msg =>
                            msg.sender === data.sender &&
                            msg.text === data.message &&
                            (Date.now() - (msg.timestamp || 0) < 500)
                        );
                        if (exists) return prev;
                        return [...prev, {
                            type: 'user',
                            sender: data.sender,
                            text: data.message,
                            isMe: data.sender === deviceId,
                            timestamp: Date.now()
                        }];
                    });
                }
            } catch (e) { console.error("Error parsing SSE", e); }
        };
        eventSourceRef.current.onerror = () => setConnecting(true);
        return () => eventSourceRef.current?.close();
    }, [chatId, deviceId]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!inputText.trim() || !isActive) return;
        const text = inputText;
        setInputText('');
        try {
            await api.post(endpoints.sendMessage, { chat_id: chatId, device_id: deviceId, message: text });
        } catch (err) { console.error("Send failed:", err); }
    };

    const handleLeave = async () => {
        try {
            if (isActive) await api.post(endpoints.leaveChat, { chat_id: chatId, device_id: deviceId });
            navigate('/home');
        } catch (err) { navigate('/home'); }
    };

    const handleNext = async () => {
        try {
            if (isActive) await api.post(endpoints.leaveChat, { chat_id: chatId, device_id: deviceId });
            navigate('/queue', { state: { autoStart: true } });
        } catch (err) { navigate('/queue', { state: { autoStart: true } }); }
    };

    return (
        <div className="chat-container">
            {/* Header */}
            <header className="chat-header">
                <div className="status-indicator">
                    <div className={`status-dot ${isActive ? 'active' : ''}`} style={{ backgroundColor: isActive ? '#4caf50' : '#ff4d4f' }}></div>
                    <span className="status-text">Anonymous User</span>
                </div>
                <div className="header-actions">
                    <button onClick={() => setShowReport(true)} className="btn-report" title="Report User">
                        <Flag size={16} fill="white" /> Report
                    </button>
                    <button onClick={handleLeave} className="btn-outline">
                        <LogOut size={16} /> Leave
                    </button>
                    <button onClick={handleNext} className="btn-outline">
                        Next <ArrowRight size={16} />
                    </button>
                </div>
            </header>

            {/* Messages Area */}
            <div className="messages-area">
                {messages.map((msg, idx) => {
                    if (msg.type === 'system') {
                        return <div key={idx} className="system-msg">{msg.text}</div>;
                    }
                    return (
                        <div key={idx} className={`message-wrapper ${msg.isMe ? 'me' : 'them'}`}>
                            <div className={`message-bubble ${msg.isMe ? 'me' : 'them'}`}>
                                {msg.text}
                            </div>
                        </div>
                    );
                })}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="input-area">
                {isActive ? (
                    <div className="input-container">
                        <form onSubmit={handleSend}>
                            <input
                                type="text"
                                className="chat-input"
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                placeholder="Type a message..."
                                autoFocus
                            />
                            <button type="submit" className="btn-send" disabled={!inputText.trim()}>
                                <Send size={20} />
                            </button>
                        </form>
                    </div>
                ) : (
                    <div style={{ textAlign: 'center' }}>
                        <p style={{ color: '#666', marginBottom: '1rem' }}>Conversation ended.</p>
                        <button onClick={handleNext} className="primary" style={{ width: '100%', maxWidth: '300px' }}>
                            Find Next Match
                        </button>
                    </div>
                )}
                {/* Sparkle Decoration in bottom right */}
                <Sparkles className="sparkle-decor" size={32} />
            </div>

            {/* Report Modal */}
            {showReport && (
                <div className="modal-overlay">
                    <div className="modal-content animate-fade-in">
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Report User</h2>
                            <button onClick={() => setShowReport(false)} style={{ background: 'none', border: 'none', padding: 0, color: '#888', cursor: 'pointer' }}><X size={24} /></button>
                        </div>
                        <p style={{ marginBottom: '1rem', color: '#aaa', fontSize: '0.9rem' }}>
                            Help us keep the community safe. This report will be reviewed.
                        </p>
                        <textarea
                            value={reportReason}
                            onChange={(e) => setReportReason(e.target.value)}
                            placeholder="Reason for reporting (e.g. harassment, spam)..."
                            style={{ width: '100%', height: '100px', marginBottom: '1rem', backgroundColor: '#000', border: '1px solid #333', borderRadius: '8px', padding: '0.8rem', color: '#fff' }}
                        />
                        <button
                            style={{ width: '100%', backgroundColor: '#dc2626', color: 'white', border: 'none', borderRadius: '8px', padding: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
                            onClick={handleReport}
                            disabled={reportSubmitting}
                        >
                            {reportSubmitting ? 'Submitting...' : 'Submit Report'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Chat;
