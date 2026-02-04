import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FingerprintJS from '@fingerprintjs/fingerprintjs';
import api, { endpoints, setDeviceId, setFingerprint, getDeviceId } from '../api';

const Landing = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const initialize = async () => {
            try {
                // Check if we already have a device ID stored
                const existingDeviceId = getDeviceId();
                console.log("DEBUG: Existing Device ID:", existingDeviceId);
                if (existingDeviceId) {
                    // Start checking status to see where to send them
                    checkStatus(existingDeviceId);
                    return;
                }

                // Initialize FingerprintJS
                const fpPromise = FingerprintJS.load();
                const fp = await fpPromise;
                const result = await fp.get();
                // Append random suffix to ensure uniqueness for testing on same machine
                const fingerprint = `${result.visitorId}-${Date.now()}`;

                setFingerprint(fingerprint);

                // Register Device
                const response = await api.post(endpoints.registerDevice, {
                    fingerprint: fingerprint
                });

                const { device_id, is_new_user } = response.data;
                console.log("DEBUG: Registration Success. Device ID:", device_id);
                setDeviceId(device_id);

                // Verify it was set
                console.log("DEBUG: Verified LocalStorage:", getDeviceId());

                // Route accordingly
                checkStatus(device_id);

            } catch (err) {
                console.error("Initialization error:", err);
                let msg = "Failed to initialize.";
                if (err.message) msg += ` Error: ${err.message}`;
                if (err.response && err.response.data) msg += ` Server: ${JSON.stringify(err.response.data)}`;
                setError(msg);
                setLoading(false);
            }
        };

        initialize();
    }, [navigate]);

    const checkStatus = async (deviceId) => {
        try {
            const response = await api.get(endpoints.getProfileStatus(deviceId));
            const { next_step } = response.data;

            // Map backend next_step to frontend routes
            switch (next_step) {
                case 'create_profile':
                    navigate('/setup-profile');
                    break;
                case 'verify_gender':
                    navigate('/verify');
                    break;
                case 'start_matching':
                case 'complete_onboarding': // Fallback
                    navigate('/home');
                    break;
                default:
                    navigate('/setup-profile');
            }
        } catch (err) {
            console.error("Status check failed:", err);
            // If device not found (maybe DB reset), try re-registering by clearing local storage?
            // For now, show error
            setError("Failed to sync with server.");
            setLoading(false);
        }
    };

    return (
        <div className="container" style={{ textAlign: 'center', marginTop: '20vh' }}>
            <h1 className="logo-text">Veil</h1>
            <p className="subtitle">Anonymous. Secure. You.</p>

            {loading && <div className="spinner"></div>}

            {error && (
                <div className="error-card">
                    <p className="error-msg">{error}</p>
                    <button onClick={() => window.location.reload()}>Retry</button>
                </div>
            )}
        </div>
    );
};

export default Landing;
