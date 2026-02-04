import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { endpoints, getDeviceId } from '../api';

const ProfileSetup = () => {
    const navigate = useNavigate();
    const [nickname, setNickname] = useState('');
    const [bio, setBio] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setError(null);

        const deviceId = getDeviceId();
        if (!deviceId) {
            setError("Device ID missing. Please restart the app.");
            setSubmitting(false);
            return;
        }

        try {
            await api.post(endpoints.createProfile, {
                device_id: deviceId,
                nickname: nickname,
                bio: bio
            });

            // Success, move to verification
            navigate('/verify');
        } catch (err) {
            console.error("Profile creation failed:", err);
            if (err.response && err.response.data) {
                // Handle serializer errors
                const msg = Object.values(err.response.data).flat().join(', ');

                // If profile exists, just move on (idempotent behavior)
                if (msg && msg.toLowerCase().includes("exists")) {
                    console.log("Profile already exists, proceeding to verification.");
                    navigate('/verify');
                    return;
                }

                setError(msg || "Failed to create profile.");
            } else {
                setError("Network error. Please try again.");
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="container">
            <div className="card animate-fade-in">
                <h1 style={{ fontSize: '1.8rem', marginBottom: '0.5rem' }}>Create Profile</h1>
                <p className="subtitle" style={{ marginBottom: '1.5rem' }}>Set up your anonymous identity.</p>

                {error && <div className="error-msg">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="input-group">
                        <label className="input-label">Nickname</label>
                        <input
                            type="text"
                            value={nickname}
                            onChange={(e) => setNickname(e.target.value)}
                            placeholder="e.g. ShadowWalker"
                            maxLength={20}
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">Bio (Optional)</label>
                        <input
                            type="text"
                            value={bio}
                            onChange={(e) => setBio(e.target.value)}
                            placeholder="Just here to chat..."
                            maxLength={150}
                        />
                    </div>

                    <button
                        type="submit"
                        className="primary"
                        style={{ width: '100%' }}
                        disabled={submitting}
                    >
                        {submitting ? <div className="spinner" style={{ width: '20px', height: '20px' }}></div> : 'Continue'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ProfileSetup;
