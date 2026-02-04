import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api, { endpoints, getDeviceId } from "../api";
import { Camera } from "lucide-react";

const Verification = () => {
    const navigate = useNavigate();

    const videoRef = useRef(null);
    const canvasRef = useRef(null);

    const [stream, setStream] = useState(null);
    const [image, setImage] = useState(null);
    const [processing, setProcessing] = useState(false);
    const [error, setError] = useState(null);
    const [status, setStatus] = useState("idle"); // idle | capturing | verifying_ready | verifying | success | fail
    const [manualMode, setManualMode] = useState(false);
    const [detectedGender, setDetectedGender] = useState(null);
    const [devices, setDevices] = useState([]);
    const [selectedDeviceId, setSelectedDeviceId] = useState("");

    useEffect(() => {
        const getDevices = async () => {
            try {
                // Must ask for permission first to get labels, but we can try enumerating
                // If labels are empty, we might need to trigger permission first.
                // However, for now let's just list what we can.
                const devs = await navigator.mediaDevices.enumerateDevices();
                const videoDevices = devs.filter(device => device.kind === "videoinput");
                setDevices(videoDevices);
                if (videoDevices.length > 0) {
                    // Prefer the one that acts like a 'user' camera if possible, or just the first one
                    setSelectedDeviceId(videoDevices[0].deviceId);
                }
            } catch (err) {
                console.error("Error enumerating devices:", err);
            }
        };
        getDevices();
    }, []);

    /* ---------------- CLEANUP ON UNMOUNT ---------------- */
    useEffect(() => {
        return () => {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, [stream]);

    /* ---------------- START CAMERA ---------------- */
    const startCamera = async () => {
        try {
            setError(null);

            // Stop old stream if any
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }

            const constraints = selectedDeviceId
                ? { video: { deviceId: { exact: selectedDeviceId } } }
                : { video: { facingMode: "user" } };

            const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);

            setStream(mediaStream);

            // Refresh devices list in case we now have labels/permissions
            try {
                const devs = await navigator.mediaDevices.enumerateDevices();
                const videoDevices = devs.filter(device => device.kind === "videoinput");
                setDevices(videoDevices);
            } catch (e) {
                console.warn("Could not refresh devices", e);
            }

            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;

                // IMPORTANT: wait until metadata is loaded
                videoRef.current.onloadedmetadata = () => {
                    videoRef.current
                        .play()
                        .catch(err => console.error("Video play failed:", err));
                };
            }

            setStatus("capturing");
        } catch (err) {
            console.error("Camera error:", err);

            let msg = "Could not access camera.";
            if (err.name === "NotAllowedError")
                msg = "Camera permission denied. Please allow access.";
            if (err.name === "NotFoundError")
                msg = "No camera found on this device.";
            if (err.name === "NotReadableError")
                msg = "Camera is being used by another app.";

            setError(msg);
        }
    };

    /* ---------------- STOP CAMERA ---------------- */
    const stopCamera = () => {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
        }
    };

    /* ---------------- CAPTURE IMAGE ---------------- */
    const captureImage = () => {
        if (!videoRef.current || !canvasRef.current) return;

        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        canvas.toBlob(
            blob => {
                setImage(blob);
                stopCamera();
                setStatus("verifying_ready");
            },
            "image/jpeg",
            0.85
        );
    };

    /* ---------------- AI VERIFY ---------------- */
    const handleVerify = async () => {
        if (!image) return;

        setProcessing(true);
        setStatus("verifying");
        setError(null);

        const formData = new FormData();
        formData.append("device_id", getDeviceId());
        formData.append("image", image, "verification.jpg");

        try {
            const res = await api.post(endpoints.verifyGenderAi, formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });

            handleSuccess(res.data);
        } catch (err) {
            handleError(err);
        }
    };

    /* ---------------- MANUAL VERIFY (DEV) ---------------- */
    const handleManualVerify = async gender => {
        setProcessing(true);

        try {
            const res = await api.post(endpoints.manualVerification, {
                device_id: getDeviceId(),
                gender
            });

            handleSuccess(res.data);
        } catch (err) {
            handleError(err);
        }
    };

    /* ---------------- SUCCESS ---------------- */
    const handleSuccess = data => {
        setDetectedGender(data.gender);
        setStatus("success");

        setTimeout(() => {
            navigate("/queue");
        }, 3000);
    };

    /* ---------------- ERROR ---------------- */
    const handleError = err => {
        console.error("Verification failed:", err);
        setProcessing(false);
        setStatus("fail");

        if (err?.response?.data?.reason) {
            setError(err.response.data.reason);
        } else {
            setError("Verification failed. Please try again.");
        }
    };

    const retake = () => {
        setImage(null);
        startCamera();
    };

    /* ---------------- UI ---------------- */
    return (
        <div className="container">
            <div className="card animate-fade-in" style={{ textAlign: "center" }}>
                <h1 style={{ fontSize: "1.8rem" }}>Identity Verification</h1>
                <p className="subtitle">
                    Live camera verification to ensure safety and fairness.
                </p>

                {error && <div className="error-msg">{error}</div>}

                {!manualMode ? (
                    <>
                        {/* CAMERA BOX */}
                        <div
                            style={{
                                width: "100%",
                                height: "300px",
                                background: "#000",
                                borderRadius: "12px",
                                marginBottom: "1.5rem",
                                overflow: "hidden",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center"
                            }}
                        >
                            {!stream && !image && (
                                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
                                    <button
                                        onClick={startCamera}
                                        style={{
                                            background: "transparent",
                                            border: "none",
                                            color: "#666",
                                            display: "flex",
                                            flexDirection: "column",
                                            alignItems: "center",
                                            cursor: "pointer"
                                        }}
                                    >
                                        <Camera size={48} />
                                        <span style={{ marginTop: 8 }}>Start Camera</span>
                                    </button>

                                    {devices.length > 0 && (
                                        <select
                                            value={selectedDeviceId}
                                            onChange={(e) => setSelectedDeviceId(e.target.value)}
                                            style={{
                                                padding: "0.5rem",
                                                borderRadius: "8px",
                                                background: "#333",
                                                color: "#fff",
                                                border: "1px solid #444",
                                                marginTop: "0.5rem"
                                            }}
                                        >
                                            {devices.map((device, index) => (
                                                <option key={device.deviceId} value={device.deviceId}>
                                                    {device.label || `Camera ${index + 1}`}
                                                </option>
                                            ))}
                                        </select>
                                    )}
                                </div>
                            )}

                            {stream && (
                                <video
                                    ref={videoRef}
                                    autoPlay
                                    playsInline
                                    muted
                                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                                />
                            )}

                            {image && (
                                <img
                                    src={URL.createObjectURL(image)}
                                    alt="Captured"
                                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                                />
                            )}
                        </div>

                        <canvas ref={canvasRef} style={{ display: "none" }} />

                        {/* ACTIONS */}
                        {status === "capturing" && (
                            <div style={{ display: "flex", gap: "10px" }}>
                                <button onClick={stopCamera} style={{ flex: 1 }}>
                                    Stop/Switch
                                </button>
                                <button className="primary" onClick={captureImage} style={{ flex: 2 }}>
                                    Capture Photo
                                </button>
                            </div>
                        )}

                        {(status === "verifying_ready" || status === "fail") && (
                            <div style={{ display: "flex", gap: 10 }}>
                                <button onClick={retake} style={{ flex: 1 }}>
                                    Retake
                                </button>
                                <button
                                    onClick={handleVerify}
                                    className="primary"
                                    disabled={processing}
                                    style={{ flex: 1 }}
                                >
                                    {processing ? "Verifying..." : "Verify"}
                                </button>
                            </div>
                        )}

                        {status === "verifying" && <div className="spinner" />}

                        <p style={{ fontSize: "0.9rem", marginTop: "1rem", color: "#666" }}>
                            Camera not working?
                            <button
                                onClick={() => setManualMode(true)}
                                style={{
                                    background: "none",
                                    border: "none",
                                    color: "#646cff",
                                    marginLeft: 6,
                                    cursor: "pointer"
                                }}
                            >
                                Manual verification
                            </button>
                        </p>
                    </>
                ) : (
                    <>
                        <h3>Manual Verification (Dev)</h3>
                        <button onClick={() => handleManualVerify("male")}>Male</button>
                        <button onClick={() => handleManualVerify("female")}>Female</button>
                        <button onClick={() => setManualMode(false)}>Back</button>
                    </>
                )}

                {status === "success" && (
                    <div style={{ marginTop: "1.5rem" }}>
                        <h3 style={{ color: "#4caf50" }}>✅ Verification Successful</h3>
                        <p>
                            Detected Gender:{" "}
                            <strong style={{ color: "#646cff" }}>{detectedGender}</strong>
                        </p>
                        <p style={{ color: "#888" }}>Redirecting to matchmaking…</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Verification;
