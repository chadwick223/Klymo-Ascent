import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000'; // Adjust if backend is on a different port

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Helper to get device ID from local storage
export const getDeviceId = () => localStorage.getItem('veil_device_id');
export const setDeviceId = (id) => localStorage.setItem('veil_device_id', id);

// Helper to get fingerprint
export const getFingerprint = () => localStorage.getItem('veil_fingerprint');
export const setFingerprint = (fp) => localStorage.setItem('veil_fingerprint', fp);


// Interceptor to add device_id if needed, though most endpoints take it in body/params
// We can just rely on explicit passing for now as per the API design.

export const endpoints = {
    registerDevice: '/register-devices/',
    createProfile: '/create-profile/',
    getProfileStatus: (deviceId) => `/status/${deviceId}/`,
    verifyGenderAi: '/verify-gender-ai/',
    manualVerification: '/manual-verification/',
    enterQueue: '/enter-queue/',
    leaveQueue: '/leave-queue/',
    matchStatus: (deviceId) => `/match-status/${deviceId}/`,
    sendMessage: '/chat/send/',
    leaveChat: '/chat/leave/',
    reportUser: '/report/',
};

export default api;
