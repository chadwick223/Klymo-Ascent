import React from 'react';
import { useNavigate } from 'react-router-dom';

const Home = () => {
    const navigate = useNavigate();

    return (
        <div className="container" style={{ textAlign: 'center', marginTop: '20vh' }}>
            <h1 className="logo-text">Veil</h1>
            <p className="subtitle">Anonymous. Secure. You.</p>

            <div className="card animate-fade-in" style={{ marginTop: '2rem' }}>
                <h2 style={{ marginBottom: '1.5rem' }}>Main Menu</h2>

                <button
                    className="primary"
                    style={{ width: '100%', marginBottom: '1rem', padding: '1rem' }}
                    onClick={() => navigate('/queue')}
                >
                    Find a Match
                </button>

                <button
                    style={{ width: '100%', padding: '1rem' }}
                    onClick={() => navigate('/setup-profile')}
                >
                    Edit Profile
                </button>
            </div>
        </div>
    );
};

export default Home;
