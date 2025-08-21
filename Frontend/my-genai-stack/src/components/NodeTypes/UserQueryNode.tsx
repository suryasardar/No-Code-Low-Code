// components/NodeTypes/UserQueryNode.tsx
import React, { memo, useCallback } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { MessageSquare, Settings, Trash2 } from 'lucide-react';
import { useWorkflowStore } from '../../store/workflowStore.ts';
import type { NodeData } from '../../store/workflowStore.ts';

// The local 'WorkflowStore' type definition is not needed and was causing a type conflict.
// We can simply use the strongly-typed store directly.

export const UserQueryNode = memo(({ data, id, selected }: NodeProps<NodeData>) => {
  // Destructure the actions from the store. No type assertion is needed here.
  const { updateNodeConfig, removeNode } = useWorkflowStore();
  
  // This function is now correctly typed and passed to the store's update function.
  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    // The `updateNodeConfig` function correctly expects a Partial<NodeConfig> object.
    // The `query` property lives within the `config` object, not at the top level of `NodeData`.
    updateNodeConfig(id, { query: e.target.value });
  }, [id, updateNodeConfig]);

  const handleDelete = useCallback(() => {
    removeNode(id);
  }, [id, removeNode]);

  return (
    <div className={`bg-white rounded-lg shadow-lg border-2 ${
      selected ? 'border-blue-500' : 'border-gray-200'
    } min-w-[300px] hover:shadow-xl transition-all duration-200`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-t-lg p-3 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-blue-600" />
            <span className="font-semibold text-sm text-gray-800">User Query</span>
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
      <div className="p-4">
        <label className="block text-xs font-medium text-gray-600 mb-2">
          Enter point for queries
        </label>
        <textarea
          value={data.config?.query || ''}
          onChange={handleQueryChange}
          placeholder="Write your query here"
          className="w-full p-3 border border-gray-300 rounded-md text-sm resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
          rows={3}
          onKeyDown={(e) => {
    if (e.key === "Backspace" || e.key === "Delete") {
      e.stopPropagation(); // ✅ Prevent React Flow from deleting node
    }
  }}
        />
      </div>
      
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="query-output"
        className="w-3 h-3 !bg-orange-500 !border-2 !border-white cursor-crosshair"
        style={{ right: '-6px' }}
      />
    </div>
  );
});

UserQueryNode.displayName = 'UserQueryNode';
