// src/components/Layout/Sidebar.jsx
import React from 'react';
import { Cpu } from 'lucide-react';

const Sidebar = ({ componentTypes, onDragStart }) => {
  return (
    <aside className="w-10 lg:w-20 xl:w-64  bg-white border-r shadow-sm flex flex-col">
      {/* Header */}
      {/* <div className="p-4 border-b bg-gradient-to-r from-green-500 to-green-600">
        <div className="flex items-center gap-2 text-white">
          <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
            <Cpu className="w-5 h-5" />
          </div>
          <span className="font-bold">GenAI Stack</span>
        </div>
      </div>
       */}
      {/* Components Section */}
      <div className="p-4 flex-1 overflow-y-auto">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
          Chat With AI
        </h3>
        
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Components</h4>
          
          {componentTypes.map((component) => {
            const Icon = component.icon;
            return (
              <div
                key={component.type}
                className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg cursor-move hover:bg-gray-100 transition-colors border border-gray-200 hover:border-gray-300"
                draggable
                onDragStart={(e) => onDragStart(e, component.type)}
                title={`Drag to add ${component.label}`}
              >
                <Icon className={`w-4 h-4 text-${component.color}-600`} />
                <span className="text-sm text-gray-700">{component.label}</span>
              </div>
            );
          })}
        </div>

        {/* Instructions */}
        <div className="mt-6 p-3 bg-blue-50 rounded-lg">
          <h5 className="text-xs font-semibold text-blue-900 mb-1">
            How to use:
          </h5>
          <ul className="text-xs text-blue-800 space-y-1">
            <li>• Drag components to canvas</li>
            <li>• Connect nodes by dragging handles</li>
            <li>• Configure each node</li>
            <li>• Execute workflow when ready</li>
          </ul>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t bg-gray-50">
        <div className="text-xs text-gray-500 text-center">
          Version 1.0.0
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;