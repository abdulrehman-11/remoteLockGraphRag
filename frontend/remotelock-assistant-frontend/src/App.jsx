import React from 'react';
import Chatbot from './Chatbot';
import './App.css'; // Your main app CSS

function App() {
  return (
    <div className="app-overall-container">
      <div className="global-header">
        <h1>RemoteLock Support Center</h1>
        <p className="subtitle">How can we help you today?</p>
      </div>

      <div className="main-layout-container">
        {/* Simplified Search Section */}
        <div className="search-section-full-width">
          <input type="text" placeholder="Search our articles..." aria-label="Search articles" />
          <button className="search-button">SEARCH</button>
        </div>

        {/* Simplified Support Content Blocks */}
        <div className="support-topics-section">
            <h2>Popular Topics</h2>
            <div className="simple-grid">
                <div className="simple-grid-item">Topic 1</div>
                <div className="simple-grid-item">Topic 2</div>
                <div className="simple-grid-item">Topic 3</div>
                <div className="simple-grid-item">Topic 4</div>
            </div>
        </div>

        <div className="support-actions-section">
            <h2>Need More Assistance?</h2>
            <div className="simple-grid">
                <div className="simple-grid-item">Submit a Request</div>
                <div className="simple-grid-item">Call Support</div>
            </div>
        </div>

      </div>

      <Chatbot />
    </div>
  );
}

export default App;

