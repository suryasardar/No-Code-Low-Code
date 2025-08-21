// components/NodeTypes/OutputNode.tsx
import React, { memo, useCallback } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { FileOutput, Settings, Trash2, Copy, CheckCircle } from 'lucide-react';
import { useWorkflowStore } from '../../store/workflowStore.ts';
import type { NodeData } from '../../store/workflowStore.ts';

type WorkflowStore = {
  removeNode: (id: string) => void;
  // add other properties if needed
};

export const OutputNode = memo(({ data, id, selected }: NodeProps<NodeData>) => {
  const { removeNode } = useWorkflowStore() as WorkflowStore;
  const [copied, setCopied] = React.useState(false);
  
  const handleDelete = useCallback(() => {
    removeNode(id);
  }, [id, removeNode]);

  const handleCopyOutput = useCallback(() => {
    const output = data.config?.output || '';
    navigator.clipboard.writeText(output).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [data.config?.output]);

  const output = data.config?.output || 'Workflow output will appear here.';
  const hasOutput = output !== 'Workflow output will appear here.';

  return (
    <div className={`bg-white rounded-lg shadow-lg border-2 ${
      selected ? 'border-emerald-500' : 'border-gray-200'
    } min-w-[320px] hover:shadow-xl transition-all duration-200`}>
      
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="output-input"
        className="w-3 h-3 !bg-green-500 !border-2 !border-white cursor-crosshair"
        style={{ left: '-6px' }}
      />
      
      {/* Header */}
      <div className="bg-gradient-to-r from-emerald-50 to-emerald-100 rounded-t-lg p-3 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileOutput className="w-5 h-5 text-emerald-600" />
            <span className="font-semibold text-sm text-gray-800">Output</span>
          </div>
          <div className="flex items-center gap-1">
            {hasOutput && (
              <button
                onClick={handleCopyOutput}
                className="p-1 hover:bg-emerald-200 rounded transition-colors"
                title="Copy output"
              >
                {copied ? (
                  <CheckCircle className="w-4 h-4 text-green-600" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-500 hover:text-gray-700" />
                )}
              </button>
            )}
            <button
              onClick={() => console.log('Settings clicked')}
              className="p-1 hover:bg-emerald-200 rounded transition-colors"
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
      <div className="p-4">
        <label className="block text-xs font-medium text-gray-600 mb-2">
          Output of the result nodes as text
        </label>
        <div className={`bg-gray-50 rounded-md p-4 min-h-[120px] max-h-[300px] overflow-y-auto ${
          hasOutput ? 'border border-emerald-200' : 'border border-gray-200'
        }`}>
          <p className={`text-sm whitespace-pre-wrap ${
            hasOutput ? 'text-gray-700' : 'text-gray-500 italic'
          }`}>
            {output}
          </p>
        </div>
        {hasOutput && (
          <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
            <span>Output generated</span>
            <span>{output.length} characters</span>
          </div>
        )}
      </div>
    </div>
  );
});

OutputNode.displayName = 'OutputNode';