// src/pages/WorkflowBuilderPage.jsx
import React, { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  MiniMap,
  Controls,
  BackgroundVariant,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useParams, useNavigate } from 'react-router-dom';
import { useWorkflowStore } from '../store/workflowStore';
import ChatPopup from '../components/chat/ChatPopup';

// Import node components
import { nodeTypes } from '../components/NodeTypes';

// Import Layout components
import Header from '../components/Layout/Header';
import Sidebar from '../components/Layout/Sidebar';

// Import icons
import { Brain, Database, FileOutput, MessageSquare, Globe, Save, CheckCircle, XCircle } from 'lucide-react';

// Component types for sidebar
const componentTypes = [
  { type: 'userQueryNode', label: 'User Query', icon: MessageSquare, color: 'blue' },
  { type: 'llmNode', label: 'LLM (OpenAI)', icon: Brain, color: 'purple' },
  { type: 'knowledgeBaseNode', label: 'Knowledge Base', icon: Database, color: 'green' },
  { type: 'outputNode', label: 'Output', icon: FileOutput, color: 'emerald' },
];

const WorkflowBuilderPage = () => {
  const { workflowId } = useParams();
  console.log('Workflow ID:', workflowId);
  const navigate = useNavigate();
  const { screenToFlowPosition } = useReactFlow();
  
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    draggedType,
    setDraggedType,
    removeNode,
    removeEdge,
    loadWorkflow,
    saveAndExecuteWorkflow,
    saveWorkflow,
    updateNodeConfig,
    workflowName,
    workflowDescription,
    setWorkflowName,
    setWorkflowDescription,
    setSelectedWorkflowId,
  } = useWorkflowStore();

  const [isLoading, setIsLoading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [showResult, setShowResult] = useState(false);

  // Set workflow ID in store
  useEffect(() => {
    if (workflowId) {
      setSelectedWorkflowId(workflowId);
    }
  }, [workflowId, setSelectedWorkflowId]);

  // Load workflow on mount
  useEffect(() => {
    if (workflowId && workflowId !== 'new') {
      loadWorkflowData();
    }
  }, [workflowId]);

  const loadWorkflowData = async () => {
    setIsLoading(true);
    try {
      await loadWorkflow(workflowId);
    } catch (error) {
      console.error('Error loading workflow:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Delete selected nodes/edges
      if (event.key === 'Delete' || event.key === 'Backspace') {
        const selectedNodes = nodes.filter((node) => node.selected);
        const selectedEdges = edges.filter((edge) => edge.selected);
        
        selectedNodes.forEach((node) => removeNode(node.id));
        selectedEdges.forEach((edge) => removeEdge(edge.id));
      }
      
      // Save workflow (Ctrl+S)
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        handleSaveWorkflow();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [nodes, edges, removeNode, removeEdge]);

  // Drag and drop handlers
  const onDragStart = useCallback((event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
    setDraggedType(nodeType);
  }, [setDraggedType]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback((event) => {
    event.preventDefault();

    const type = event.dataTransfer.getData('application/reactflow');
    
    if (type) {
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode = {
        id: `${type}_${Date.now()}`,
        type,
        position,
        data: {
          label: getNodeLabel(type),
          name: getNodeName(type),
          type: type,
          config: getDefaultConfig(type),
        },
      };

      addNode(newNode);
    }
  }, [screenToFlowPosition, addNode]);

  // Helper functions
  const getNodeLabel = (type) => {
    const component = componentTypes.find(c => c.type === type);
    return component ? component.label : type;
  };

  const getNodeName = (type) => {
    switch (type) {
      case 'userQueryNode': return 'UserQuery';
      case 'knowledgeBaseNode': return 'KnowledgeBase';
      case 'llmNode': return 'LLMEngine';
      case 'outputNode': return 'Output';
      default: return type;
    }
  };

  const getDefaultConfig = (type) => {
    switch (type) {
      case 'llmNode':
        return {
          model: 'GPT-4o-Mini',
          apiKey: '',
          temperature: '0.7',
          webSearchEnabled: false,
          serpApiKey: '',
          prompt: 'You are a helpful AI assistant.',
        };
      case 'knowledgeBaseNode':
        return {
          embeddingModel: 'text-embedding-3-large',
          apiKey: '',
          uploadedFileName: '',
          uploadedFile: null,
        };
      case 'userQueryNode':
        return {
          query: 'Write your query here',
        };
      case 'outputNode':
        return {
          output: 'Workflow output will appear here.',
        };
      default:
        return {};
    }
  };

  // Save workflow only
  const handleSaveWorkflow = async () => {
    setIsSaving(true);
    try {
      const result = await saveWorkflow();
      if (result) {
        console.log('Workflow saved successfully');
        // You can add a toast notification here
        setShowResult(true);
        setExecutionResult({
          success: true,
          message: 'Workflow saved successfully!',
          type: 'save'
        });
        
        // Hide success message after 3 seconds
        setTimeout(() => {
          setShowResult(false);
        }, 3000);
      }
    } catch (error) {
      console.error('Error saving workflow:', error);
      setShowResult(true);
      setExecutionResult({
        success: false,
        message: 'Failed to save workflow. Please try again.',
        type: 'save',
        error: error.message
      });
      
      // Hide error message after 5 seconds
      setTimeout(() => {
        setShowResult(false);
      }, 5000);
    } finally {
      setIsSaving(false);
    }
  };

  // Execute workflow (saves first, then executes)
  const handleRunWorkflow = async () => {
    setIsExecuting(true);
    setExecutionResult(null);
    setShowResult(false);
    
    try {
      // Validate workflow
      const userQueryNode = nodes.find(node => node.type === 'userQueryNode');
      if (!userQueryNode) {
        throw new Error('Please add a User Query node to your workflow');
      }

      const userQuery = userQueryNode?.data?.config?.query || '';
      if (!userQuery || userQuery === 'Write your query here') {
        throw new Error('Please enter a query in the User Query node');
      }

      const outputNode = nodes.find(node => node.type === 'outputNode');
      if (!outputNode) {
        throw new Error('Please add an Output node to your workflow');
      }

      const llmNode = nodes.find(node => node.type === 'llmNode');
      if (!llmNode) {
        throw new Error('Please add an LLM node to your workflow');
      }

      // Check if LLM node has API key
      if (!llmNode.data?.config?.apiKey) {
        throw new Error('Please configure an API key in your LLM node');
      }

      console.log('Starting workflow execution...');
      console.log('User query:', userQuery);
      console.log('Current nodes:', nodes);
      console.log('Current edges:', edges);

      // Save and execute workflow
      const result = await saveAndExecuteWorkflow(userQuery);
      
      console.log('Workflow execution completed:', result);
      
      setExecutionResult({
        success: result.success,
        message: result.message,
        type: 'execute',
        saveResult: result.saveResult,
        executeResult: result.executeResult,
        error: result.error
      });
      setShowResult(true);
      
      // If execution was successful, auto-hide after 5 seconds
      if (result.success) {
        setTimeout(() => {
          setShowResult(false);
        }, 5000);
      }
      
    } catch (error) {
      console.error('Error executing workflow:', error);
      setExecutionResult({
        success: false,
        message: error.message,
        type: 'execute',
        error: error.message
      });
      setShowResult(true);
    } finally {
      setIsExecuting(false);
    }
  };

  // Check if web search should be visible
  const isWebSearchVisible = () => {
    const userQueryNodes = nodes.filter(n => n.type === 'userQueryNode');
    const llmNodes = nodes.filter(n => n.type === 'llmNode');
    
    for (const uqNode of userQueryNodes) {
      for (const llmNode of llmNodes) {
        const hasConnection = edges.some(edge => 
          (edge.source === uqNode.id && edge.target === llmNode.id) ||
          (edge.source === llmNode.id && edge.target === uqNode.id)
        );
        if (hasConnection) return true;
      }
    }
    return false;
  };

  // Add web search to component types if visible
  const visibleComponentTypes = [...componentTypes];
  if (isWebSearchVisible()) {
    visibleComponentTypes.push({
      type: 'webSearchNode',
      label: 'Web Search',
      icon: Globe,
      color: 'blue'
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-xl text-gray-700">Loading workflow...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-gray-50">
      <Header 
        workflowName={workflowName}
        workflowDescription={workflowDescription}
        onNameChange={setWorkflowName}
        onDescriptionChange={setWorkflowDescription}
        onBack={() => navigate('/')}
      />
      
      <div className="flex flex-1 overflow-hidden">
        <Sidebar 
          componentTypes={visibleComponentTypes}
          onDragStart={onDragStart}
        />
        
        <div 
          className="flex-1 relative"
          onDrop={onDrop}
          onDragOver={onDragOver}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            className="bg-gray-50"
          >
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
            <Controls />
            {/* <MiniMap 
              className="!absolute !top-4 !right-4"
              nodeColor={(node) => {
                switch(node.type) {
                  case 'userQueryNode': return '#3B82F6';
                  case 'llmNode': return '#9333EA';
                  case 'knowledgeBaseNode': return '#10B981';
                  case 'outputNode': return '#10B981';
                  default: return '#6B7280';
                }
              }}
            /> */}
          </ReactFlow>

          {/* Empty state */}
          {nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 text-gray-300">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                    <rect x="3" y="3" width="7" height="7" rx="1" />
                    <rect x="14" y="3" width="7" height="7" rx="1" />
                    <rect x="14" y="14" width="7" height="7" rx="1" />
                    <rect x="3" y="14" width="7" height="7" rx="1" />
                    <path d="M10 6.5h4m-2 0v4m-2 3.5h4m-2 0v4" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-700 mb-1">
                  Drag & drop to get started
                </h3>
                <p className="text-sm text-gray-500">
                  Add components from the sidebar to build your workflow
                </p>
              </div>
            </div>
          )}

          {/* Status/Result Notification */}
          {(isSaving || isExecuting || showResult) && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
              {isSaving && (
                <div className="bg-white px-4 py-2 rounded-lg shadow-lg border flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                  <span className="text-sm font-medium text-gray-700">Saving workflow...</span>
                </div>
              )}
              
              {isExecuting && (
                <div className="bg-white px-4 py-2 rounded-lg shadow-lg border flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-500"></div>
                  <span className="text-sm font-medium text-gray-700">
                    {executionResult?.type === 'execute' ? 'Executing workflow...' : 'Saving and executing...'}
                  </span>
                </div>
              )}
              
              {showResult && executionResult && (
                <div className={`px-4 py-2 rounded-lg shadow-lg border flex items-center gap-2 max-w-md ${
                  executionResult.success 
                    ? 'bg-green-50 border-green-200 text-green-800' 
                    : 'bg-red-50 border-red-200 text-red-800'
                }`}>
                  {executionResult.success ? (
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-600" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm font-medium">{executionResult.message}</p>
                    {executionResult.error && (
                      <p className="text-xs opacity-75 mt-1">{executionResult.error}</p>
                    )}
                    {executionResult.executeResult && (
                      <div className="mt-2 text-xs">
                        <p><strong>Execution Time:</strong> {executionResult.executeResult.execution_time?.toFixed(2)}s</p>
                        {executionResult.executeResult.sources_used?.length > 0 && (
                          <p><strong>Sources:</strong> {executionResult.executeResult.sources_used.length}</p>
                        )}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => setShowResult(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ×
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Action buttons */}
          <div className="absolute bottom-4 right-4 flex flex-col gap-3 p-2 ">
            <button
              onClick={handleSaveWorkflow}
              disabled={isSaving || isExecuting || nodes.length === 0}
              className="px-4 py-2 bg-white text-gray-700 rounded-lg shadow-md hover:shadow-lg transition-all border flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  {/* Save Workflow */}
                </>
              )}
            </button>
            
            <button
              onClick={handleRunWorkflow}
              disabled={isExecuting || isSaving || nodes.length === 0}
              className="px-4 py-2 bg-green-500 text-white rounded-lg shadow-md hover:bg-green-600 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isExecuting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Executing...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v18l15-9-15-9z" />
                  </svg>
                  {/* Execute Workflow */}
                </>
              )}
            </button>
            
            <button
              onClick={() => setIsChatOpen(true)}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg shadow-md hover:bg-blue-600 transition-colors flex items-center gap-2"
            >
              <MessageSquare className="w-4 h-4" />
              {/* Chat with Stack */}
            </button>
          </div>
        </div>
      </div>

      {/* Chat Modal */}
      {isChatOpen && (
        <ChatPopup
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          stackId={workflowId}
        />
      )}
    </div>
  );
};

// Chat Modal Component
const ChatModal = ({ isOpen, onClose, workflowId }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');

  const sendMessage = () => {
    if (inputValue.trim()) {
      setMessages([...messages, { text: inputValue, sender: 'user' }]);
      // Simulate AI response
      setTimeout(() => {
        setMessages(prev => [...prev, { 
          text: 'I can help you with your workflow. What would you like to know?', 
          sender: 'ai' 
        }]);
      }, 1000);
      setInputValue('');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-96 h-[500px] flex flex-col shadow-xl">
        <div className="p-4 border-b flex items-center justify-between">
          <h3 className="font-semibold">Chat with Stack</h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-xl"
          >
            ×
          </button>
        </div>
        <div className="flex-1 p-4 overflow-y-auto">
          {messages.map((msg, idx) => (
            <div key={idx} className={`mb-3 ${msg.sender === 'user' ? 'text-right' : ''}`}>
              <div className={`inline-block p-3 rounded-lg ${
                msg.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100'
              }`}>
                {msg.text}
              </div>
            </div>
          ))}
        </div>
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type your message..."
              className="flex-1 p-2 border rounded-lg"
            />
            <button
              onClick={sendMessage}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkflowBuilderPage;