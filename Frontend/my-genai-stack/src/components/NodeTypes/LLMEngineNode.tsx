// components/NodeTypes/LLMEngineNode.tsx
import React, { memo, useCallback } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Cpu, Settings, Trash2 } from 'lucide-react';
import { useWorkflowStore } from '../../store/workflowStore.ts';
import type { NodeData } from '../../store/workflowStore.ts';


export const LLMNode = memo(({ data, id, selected }: NodeProps<NodeData>) => {
  const { updateNodeConfig, removeNode } = useWorkflowStore();
  
  const handleConfigChange = useCallback((key: string, value: any) => {
    updateNodeConfig(id, { [key]: value });
  }, [id, updateNodeConfig]);

  const handleDelete = useCallback(() => {
    removeNode(id);
  }, [id, removeNode]);

  const config = data.config || {
    model: 'gemini-1.5-flash',
    apiKey: '',
    temperature: '0.7',
    webSearchEnabled: false,
    serpApiKey: '',
    prompt: `You are a helpful AI assistant. Use web search if the context lacks information.

CONTEXT: {context}
User Query: {query}

Please provide a comprehensive answer.`
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg border-2 ${
      selected ? 'border-purple-500' : 'border-gray-200'
    } min-w-[350px] hover:shadow-xl transition-all duration-200`}>
      
      {/* Input Handles */}
      <Handle
        type="target"
        position={Position.Left}
        id="context-input"
        className="w-3 h-3 !bg-orange-500 !border-2 !border-white cursor-crosshair"
        style={{ left: '-6px', top: '30%' }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="query-input"
        className="w-3 h-3 !bg-orange-500 !border-2 !border-white cursor-crosshair"
        style={{ left: '-6px', top: '70%' }}
      />
      
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-t-lg p-3 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-purple-600" />
            <span className="font-semibold text-sm text-gray-800">LLM (OpenAI)</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => console.log('Settings clicked')}
              className="p-1 hover:bg-purple-200 rounded transition-colors"
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
        <div className="text-xs text-gray-600 mb-2">Run a query with OpenAI LLM</div>
        
        {/* Model Selection */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Model</label>
          <select
            value={config.model}
            onChange={(e) => handleConfigChange('model', e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
          >
            <option value="GPT-4o-Mini">GPT-4o-Mini</option>
            <option value="GPT-4">GPT-4</option>
            <option value="GPT-3.5-Turbo">GPT-3.5-Turbo</option>
            <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
            <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
          </select>
        </div>

        {/* API Key */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">API Key</label>
          <input
            type="password"
            value={config.apiKey}
            onChange={(e) => handleConfigChange('apiKey', e.target.value)}
            placeholder="••••••••••••••••••••"
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
          />
        </div>

        {/* Prompt */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Prompt</label>
          <textarea
            value={config.prompt}
            onChange={(e) => handleConfigChange('prompt', e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md text-sm resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
            rows={4}
            placeholder="Enter your prompt template..."
          />
        </div>

        {/* Temperature */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Temperature</label>
          <input
            type="number"
            step="0.1"
            min="0"
            max="2"
            value={config.temperature}
            onChange={(e) => handleConfigChange('temperature', e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
          />
        </div>

        {/* Web Search Toggle */}
        <div className="border-t pt-3">
          <div className="flex items-center justify-between mb-2">
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
          
          {/* SERP API Key - Only show when web search is enabled */}
          {config.webSearchEnabled && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">SERP API</label>
              <input
                type="password"
                value={config.serpApiKey}
                onChange={(e) => handleConfigChange('serpApiKey', e.target.value)}
                placeholder="••••••••••••••••••••"
                className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
              />
            </div>
          )}
        </div>
      </div>
      
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="llm-output"
        className="w-3 h-3 !bg-green-500 !border-2 !border-white cursor-crosshair"
        style={{ right: '-6px' }}
      />
    </div>
  );
});

LLMNode.displayName = 'LLMNode';