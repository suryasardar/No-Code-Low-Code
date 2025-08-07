// src/components/Layout/Header.jsx
import React from 'react';
import { ArrowLeft, Save, Settings, Play } from 'lucide-react';

const Header = ({ 
  workflowName, 
  workflowDescription, 
  onNameChange, 
  onDescriptionChange, 
  onSave, 
  isSaving,
  onBack 
}) => {
  return (
    <header className="bg-white border-b shadow-sm">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between">
          {/* Left section */}
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Back to Home"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            
            <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center shadow-md">
              <span className="text-white text-lg font-bold">G</span>
            </div>
            <div>
              <span className="text-xl font-bold text-gray-900">GenAI Stack</span>
              {/* <p className="text-xs text-gray-500">Build AI Workflows</p> */}
            </div>
          </div>
          
            {/* <div>
              <input
                type="text"
                value={workflowName || 'Untitled Workflow'}
                onChange={(e) => onNameChange(e.target.value)}
                className="text-lg font-semibold text-gray-800 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none transition-colors px-1"
                placeholder="Workflow Name"
              />
              <input
                type="text"
                value={workflowDescription || ''}
                onChange={(e) => onDescriptionChange(e.target.value)}
                className="block text-sm text-gray-600 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none transition-colors px-1 mt-1 w-full"
                placeholder="Add a description..."
              />
            </div> */}
          </div>

          {/* Right section */}
          <div className="flex items-center gap-3">
            <button
              onClick={onSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save'}
            </button>
            
            <button
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Settings"
            >
              <Settings className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;