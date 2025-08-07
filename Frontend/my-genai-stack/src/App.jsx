// src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ReactFlowProvider } from 'reactflow';
import 'reactflow/dist/style.css';
import './App.css';

// Import pages
import GenAIStackHomePage from './pages/GenAIStackHomePage';
import WorkflowBuilderPage from './pages/WorkflowBuilderPage';

function App() {
  return (
    <Router>
      <ReactFlowProvider>
        <div className="App">
          <Routes>
            {/* Home Page */}
            <Route path="/" element={<GenAIStackHomePage />} />
            
            {/* Workflow Builder */}
            <Route path="/workflow/:workflowId" element={<WorkflowBuilderPage />} />
            
            {/* Default redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </ReactFlowProvider>
    </Router>
  );
}

export default App;