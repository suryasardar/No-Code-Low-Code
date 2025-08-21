// components/NodeTypes/WebSearchNode.tsx
import React, { memo, useCallback } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Globe, Settings, Trash2 } from 'lucide-react';
import { useWorkflowStore } from '../../store/workflowStore.ts';
import type { NodeData } from '../../store/workflowStore.ts';

type WorkflowStore = {
  updateNodeConfig: (id: string, config: Partial<NodeData>) => void;
  removeNode: (id: string) => void;
  // add other properties if needed
};


export const WebSearchNode = memo(({ data, id, selected }: NodeProps<NodeData>) => {
  const { updateNodeConfig, removeNode } = useWorkflowStore() as WorkflowStore;
  
  const handleConfigChange = useCallback((key: string, value: any) => {
    updateNodeConfig(id, { [key]: value });
  }, [id, updateNodeConfig]);

  const handleDelete = useCallback(() => {
    removeNode(id);
  }, [id, removeNode]);

  const config = data.config || {
    webSearchEnabled: true,
    serpApiKey: ''
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg border-2 ${
      selected ? 'border-blue-500' : 'border-gray-200'
    } min-w-[280px] hover:shadow-xl transition-all duration-200`}>
      
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="search-input"
        className="w-3 h-3 !bg-blue-500 !border-2 !border-white cursor-crosshair"
        style={{ left: '-6px' }}
      />
      
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-t-lg p-3 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-blue-600" />
            <span className="font-semibold text-sm text-gray-800">Web Search</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => console.log('Settings clicked')}
              className="p-1 hover:bg-blue-200 rounded transition-colors"
              title="Settings"
            >
              <Settings className="w-4 h-4 text-gray-500 hover:text-gray-700" />
            </button>
            <button
              onClick={handleDelete}
              className="p-1 hover:bg-red-200 rounded transition-colors"
              title="Delete"
            >
              <Trash2 className="w-4 h-4 text-gray-500 hover:text-red-600" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Enable/Disable Toggle */}
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-gray-600">WebSearch Tool</label>
          <button
            onClick={() => handleConfigChange('webSearchEnabled', !config.webSearchEnabled)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              config.webSearchEnabled ? 'bg-green-500' : 'bg-gray-300'
            }`}
            aria-label="Toggle Web Search"
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              config.webSearchEnabled ? 'translate-x-6' : 'translate-x-1'
            }`} />
          </button>
        </div>
        
        {/* SERP API Key */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">SERP API</label>
          <input
            type="password"
            value={config.serpApiKey}
            onChange={(e) => handleConfigChange('serpApiKey', e.target.value)}
            placeholder="••••••••••••••••••••"
            disabled={!config.webSearchEnabled}
            className={`w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none ${
              !config.webSearchEnabled ? 'bg-gray-100 cursor-not-allowed' : ''
            }`}
          />
        </div>
        
        {config.webSearchEnabled && (
          <div className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
            Web search will enhance LLM responses with real-time information
          </div>
        )}
      </div>
      
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="search-output"
        className="w-3 h-3 !bg-green-500 !border-2 !border-white cursor-crosshair"
        style={{ right: '-6px' }}
      />
    </div>
  );
});

WebSearchNode.displayName = 'WebSearchNode';