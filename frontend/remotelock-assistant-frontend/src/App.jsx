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

        {/* Enhanced Need More Assistance Section */}
        <div className="need-assistance-section">
            <h2>Need More Assistance?</h2>
            <div className="assistance-options-grid">
                <a href="mailto:support@remotelock.com" className="assistance-option-item">
                    <h3>Email Support</h3>
                    <p>Send us a detailed message.</p>
                    <p className="contact-info">support@remotelock.com</p>
                </a>
                <a href="https://calendly.com/d/ckmv-yqz-drr/remotelock-technical-support-appointment" target="_blank" rel="noopener noreferrer" className="assistance-option-item">
                    <h3>General Tech Support</h3> {/* Shortened title */}
                    <p>Book an appointment for technical assistance.</p>
                    <p className="contact-info">Schedule Call</p> {/* Changed button text */}
                </a>
                 <a href="https://calendly.com/d/cm2c-sx2-ktk/ack-acs-support-appointment-only" target="_blank" rel="noopener noreferrer" className="assistance-option-item">
                    <h3>ACS Only Support</h3> {/* Shortened title */}
                    <p>Book an appointment for ACS-specific issues.</p>
                    <p className="contact-info">Schedule Call</p> {/* Changed button text */}
                </a>
                <a href="https://stonly.com/guide/en/need-help-OyEmJ8vLwo/Steps/2309428" target="_blank" rel="noopener noreferrer" className="assistance-option-item">
                    <h3>Submit a Ticket</h3>
                    <p>Open a new support request.</p>
                    <p className="contact-info">Open Form</p> {/* Changed button text */}
                </a>
            </div>
        </div>

      </div>

      <Chatbot />
    </div>
  );
}

export default App;























// import React from 'react';
// import Chatbot from './Chatbot';
// import './App.css'; // Your main app CSS

// function App() {
//   return (
//     <div className="app-overall-container">
//       <div className="global-header">
//         <h1>RemoteLock Support Center</h1>
//         <p className="subtitle">How can we help you today?</p>
//       </div>

//       <div className="main-layout-container">
//         {/* Simplified Search Section */}
//         <div className="search-section-full-width">
//           <input type="text" placeholder="Search our articles..." aria-label="Search articles" />
//           <button className="search-button">SEARCH</button>
//         </div>

//         {/* Simplified Support Content Blocks */}
//         <div className="support-topics-section">
//             <h2>Popular Topics</h2>
//             <div className="simple-grid">
//                 <div className="simple-grid-item">Topic 1</div>
//                 <div className="simple-grid-item">Topic 2</div>
//                 <div className="simple-grid-item">Topic 3</div>
//                 <div className="simple-grid-item">Topic 4</div>
//             </div>
//         </div>

//         <div className="support-actions-section">
//             <h2>Need More Assistance?</h2>
//             <div className="simple-grid">
//                 <div className="simple-grid-item">Submit a Request</div>
//                 <div className="simple-grid-item">Call Support</div>
//             </div>
//         </div>

//       </div>

//       <Chatbot />
//     </div>
//   );
// }

// export default App;

