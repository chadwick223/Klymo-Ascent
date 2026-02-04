import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api, { endpoints, getDeviceId } from '../api';

const MatchQueue = () => {
    const navigate = useNavigate();
    const [preference, setPreference] = useState('any'); // male, female, any
    const [inQueue, setInQueue] = useState(false);
    const [statusText, setStatusText] = useState("Ready to connect");
    const [error, setError] = useState(null);
    const [cooldown, setCooldown] = useState(0);
    const pollInterval = useRef(null);

    const deviceId = getDeviceId();

    const location = useLocation();

    useEffect(() => {
        if (!deviceId) {
            console.warn("No device ID found in MatchQueue, redirecting to Landing.");
            navigate('/');
            return;
        }

        // Check if we came from "Next" button
        if (location.state?.autoStart) {
            // Clear state so reload doesn't re-trigger
            window.history.replaceState({}, document.title);
            handleEnterQueue();
        } else {
            // Initial status check usually done
            checkMatchStatus();
        }

        return () => stopPolling();
    }, [deviceId, navigate]);

    useEffect(() => {
        let timer;
        if (cooldown > 0) {
            timer = setInterval(() => {
                setCooldown(c => Math.max(0, c - 1));
            }, 1000);
        }
        return () => clearInterval(timer);
    }, [cooldown]);

    const stopPolling = () => {
        if (pollInterval.current) {
            clearInterval(pollInterval.current);
            pollInterval.current = null;
        }
    };

    const startPolling = () => {
        stopPolling();
        pollInterval.current = setInterval(checkMatchStatus, 2000); // Poll every 2 seconds
    };

    const checkMatchStatus = async () => {
        try {
            const response = await api.get(endpoints.matchStatus(deviceId));
            const { status, chat_id, partner_id, remaining_seconds } = response.data;

            if (status === 'matched') {
                stopPolling();
                navigate(`/chat/${chat_id}`, { state: { partnerId: partner_id } });
            } else if (status === 'in_queue') {
                setInQueue(true);
                setStatusText("Searching for a match...");
                if (!pollInterval.current) startPolling(); // Ensure we are polling
            } else if (status === 'cooldown') {
                setInQueue(false);
                setCooldown(Math.ceil(remaining_seconds || 0));
                setStatusText(`Cooldown active: ${Math.ceil(remaining_seconds)}s`);
            } else {
                // Idle
                setInQueue(false);
                setStatusText("Ready to connect");
                stopPolling();
            }
        } catch (err) {
            console.error("Match status check error:", err);
            // Don't show error to user for every poll failure, just log it.
        }
    };

    const handleEnterQueue = async () => {
        setError(null);
        try {
            const response = await api.post(endpoints.enterQueue, {
                device_id: deviceId,
                preference: preference
            });

            if (response.data.matched) {
                navigate(`/chat/${response.data.chat_id}`, {
                    state: { partnerId: response.data.partner_device_id }
                });
            } else {
                setInQueue(true);
                setStatusText("Searching for a match...");
                startPolling();
            }

        } catch (err) {
            console.error("Enter queue error:", err);
            if (err.response && err.response.data && err.response.data.error) {
                setError(err.response.data.error);
                if (err.response.data.error.includes("cooldown")) {
                    // trigger refresh to get cooldown time
                    checkMatchStatus();
                }
            } else {
                setError("Failed to join queue.");
            }
        }
    };

    const handleLeaveQueue = async () => {
        try {
            await api.post(endpoints.leaveQueue, { device_id: deviceId });
            setInQueue(false);
            setStatusText("Left queue");
            stopPolling();
            // Usually leaving queue triggers cooldown, let's verify
            checkMatchStatus();
        } catch (err) {
            console.error("Leave queue error:", err);
        }
    };

    return (
        <div className="container" style={{ textAlign: 'center' }}>
            <h1 className="logo-text">Veil</h1>

            <div className="card animate-fade-in" style={{ marginTop: '2rem' }}>
                <h2 style={{ marginBottom: '1rem' }}>Find a Partner</h2>

                {error && <div className="error-msg">{error}</div>}

                <div style={{ marginBottom: '2rem' }}>
                    <p style={{ color: '#888', marginBottom: '0.5rem' }}>I want to chat with:</p>
                    <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                        {['any', 'male', 'female'].map(opt => (
                            <button
                                key={opt}
                                // Fix specific lint: check if property exists before accessing.
                                // Actually, logic is fine.
                                className={preference === opt ? 'primary' : ''}
                                onClick={() => !inQueue && setPreference(opt)}
                                disabled={inQueue || cooldown > 0}
                                style={{ textTransform: 'capitalize', flex: 1 }}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                </div>

                <div style={{ minHeight: '60px', marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                    {statusText}
                    {inQueue && <div className="spinner" style={{ marginTop: '10px', width: '20px', height: '20px' }}></div>}
                </div>

                {!inQueue ? (
                    <button
                        className="primary"
                        style={{ width: '100%', fontSize: '1.1rem', padding: '1rem' }}
                        onClick={handleEnterQueue}
                        disabled={cooldown > 0}
                    >
                        {cooldown > 0 ? `Wait ${cooldown}s` : 'Start Matching'}
                    </button>
                ) : (
                    <button
                        style={{ width: '100%', borderColor: '#ff4d4f', color: '#ff4d4f' }}
                        onClick={handleLeaveQueue}
                    >
                        Cancel Search
                    </button>
                )}
            </div>
        </div>
    );
};

export default MatchQueue;
