import React, { useState, useRef, useEffect } from 'react';
import { X, Send, MessageCircle, FileText, Clock, Database, Settings } from 'lucide-react';

const ChatPopup = ({
  isOpen,
  onClose,
  stackId // Changed from workflowId to stackId to match your backend
}) => {
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [workflowInfo, setWorkflowInfo] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
// const API_BASE_URL = 'http://127.0.0.1:8000';
const API_BASE_URL = 'http://43.205.119.16:8000';

// console.log("API_BASE_URL:", stackId);
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load workflow info when component mounts
    if (isOpen && stackId) {
      loadWorkflowInfo();
    }
  }, [isOpen, stackId]);

  const loadWorkflowInfo = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/chat/validate?stack_id=${stackId}`, {
        method: 'POST'
      });
      if (response.ok) {
        const data = await response.json();
        setWorkflowInfo(data);
      }
    } catch (error) {
      console.error('Failed to load workflow info:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!currentMessage.trim()) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: currentMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const queryText = currentMessage;
    setCurrentMessage('');
    setIsTyping(true);

    try {
      // Call your workflow-based chat endpoint
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          stack_id: stackId,
          query: queryText
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Add AI response with workflow metadata
      const aiResponse = {
        id: Date.now() + 1,
        type: 'ai',
        content: data.response,
        timestamp: new Date(),
        metadata: {
          sources_used: data.sources_used || [],
          chunk_count: data.chunk_count || 0,
          execution_time: data.execution_time || 0,
          context_chunks: data.context_chunks || [],
          execution_flow: data.execution_flow || [],
          workflow_used: data.workflow_used || false
        }
      };

      setMessages(prev => [...prev, aiResponse]);
      
    } catch (error) {
      console.error('Chat error:', error);
      
      // Add error message
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: `I apologize, but I encountered an error while processing your request: ${error.message}. Please make sure your stack is properly configured with API keys and try again.`,
        timestamp: new Date(),
        isError: true
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatExecutionTime = (seconds) => {
    if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
    return `${seconds.toFixed(2)}s`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      {/* Chat Container */}
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[700px] flex flex-col relative overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center shadow-md">
              <span className="text-white text-lg font-bold">G</span>
            </div>
            <div>

              <h2 className="text-xl font-semibold text-gray-900">GenAI Stack</h2>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              title="Chat Settings"
            >
              <Settings className="w-5 h-5 text-gray-500" />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X className="w-6 h-6 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <div className="border-b border-gray-200 p-4 bg-gray-50">
            <div className="space-y-3">
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Workflow Status</h4>
                {workflowInfo ? (
                  <div className="space-y-2">
                    <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
                      workflowInfo.is_chat_ready 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {workflowInfo.is_chat_ready ? '✓ Ready' : '✗ Not Ready'}
                    </div>
                    <div className="text-xs text-gray-600">
                      Flow: {workflowInfo.workflow_validation?.execution_flow?.join(' → ') || 'No flow'}
                    </div>
                    {!workflowInfo.is_chat_ready && workflowInfo.recommendations && (
                      <div className="text-xs text-red-600">
                        {workflowInfo.recommendations.slice(0, 2).map((rec, idx) => (
                          <div key={idx}>• {rec}</div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-gray-500">Loading workflow info...</div>
                )}
              </div>
              
              <button
                onClick={loadWorkflowInfo}
                className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200"
              >
                Refresh Status
              </button>
            </div>
          </div>
        )}

        {/* Messages Container */}
        <div className="flex-1 flex flex-col">
          {messages.length === 0 ? (
            /* Empty State */
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
               <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center shadow-md">
              <span className="text-white text-lg font-bold">G</span>
            </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">GenAI chat Stack</h3>
              <div className="text-xs text-gray-400 bg-gray-100 px-3 py-2 rounded-lg">
               Start a conversation to test your Stack!
              </div>
            </div>
            
          ) : (
            /* Messages List */
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex items-start gap-3 max-w-[85%] ${message.type === 'user' ? 'flex-row-reverse' : ''}`}>
                    {/* Avatar */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      message.type === 'user' 
                        ? 'bg-blue-500' 
                        : message.isError
                          ? 'bg-red-500'
                          : 'bg-gradient-to-br from-green-500 to-blue-500'
                    }`}>
                      <span className="text-white text-xs font-medium">
                        {message.type === 'user' ? '👤' : '🤖'}
                      </span>
                    </div>
                    
                    {/* Message Content */}
                    <div className="flex flex-col max-w-full">
                      {/* Message Bubble */}
                      <div className={`px-4 py-3 rounded-2xl ${
                        message.type === 'user'
                          ? 'bg-blue-500 text-white rounded-br-md'
                          : message.isError
                            ? 'bg-red-50 text-red-800 border border-red-200 rounded-bl-md'
                            : 'bg-gray-100 text-gray-900 rounded-bl-md'
                      }`}>
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        <span className={`text-xs mt-1 block ${
                          message.type === 'user' 
                            ? 'text-blue-100' 
                            : message.isError
                              ? 'text-red-600'
                              : 'text-gray-500'
                        }`}>
                          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      
                      {/* Metadata for AI responses */}
                      {message.type === 'ai' && message.metadata && !message.isError && (
                        <div className="mt-2 space-y-2">
                          {/* Execution Flow */}
                          {message.metadata.execution_flow && message.metadata.execution_flow.length > 0 && (
                            <div className="flex items-center gap-4 text-xs text-gray-500">
                              <div className="flex items-center gap-1">
                                <span className="font-medium">Flow:</span>
                                <span>{message.metadata.execution_flow.join(' → ')}</span>
                              </div>
                            </div>
                          )}
                          
                          {/* Execution Stats */}
                          <div className="flex items-center gap-4 text-xs text-gray-500">
                            <div className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatExecutionTime(message.metadata.execution_time)}
                            </div>
                            <div className="flex items-center gap-1">
                              <Database className="w-3 h-3" />
                              {message.metadata.chunk_count} chunks
                            </div>
                            {message.metadata.workflow_used && (
                              <div className="flex items-center gap-1">
                                <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                                Workflow
                              </div>
                            )}
                          </div>
                          
                          {/* Sources */}
                          {message.metadata.sources_used && message.metadata.sources_used.length > 0 && (
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                              <div className="flex items-center gap-1 mb-2">
                                <FileText className="w-3 h-3 text-blue-600" />
                                <span className="text-xs font-medium text-blue-800">Sources:</span>
                              </div>
                              <div className="flex flex-wrap gap-1">
                                {message.metadata.sources_used.map((source, idx) => (
                                  <span
                                    key={idx}
                                    className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full"
                                  >
                                    {source}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {/* Context Chunks Preview */}
                          {message.metadata.context_chunks && message.metadata.context_chunks.length > 0 && (
                            <details className="bg-gray-50 border border-gray-200 rounded-lg">
                              <summary className="p-2 cursor-pointer text-xs text-gray-600 hover:bg-gray-100">
                                View Context ({message.metadata.context_chunks.length} chunks)
                              </summary>
                              <div className="p-3 border-t border-gray-200 space-y-2">
                                {message.metadata.context_chunks.slice(0, 3).map((chunk, idx) => (
                                  <div key={idx} className="text-xs bg-white p-2 rounded border">
                                    <div className="text-gray-600 mb-1">
                                      {chunk.metadata?.file_name} (Score: {chunk.similarity_score?.toFixed(3)})
                                    </div>
                                    <div className="text-gray-800">
                                      {chunk.text?.substring(0, 200)}...
                                    </div>
                                  </div>
                                ))}
                                {message.metadata.context_chunks.length > 3 && (
                                  <div className="text-xs text-gray-500 text-center">
                                    ... and {message.metadata.context_chunks.length - 3} more chunks
                                  </div>
                                )}
                              </div>
                            </details>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Typing Indicator */}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-blue-500 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs font-medium">🤖</span>
                    </div>
                    <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-bl-md">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Searching documents & generating response...</p>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Input Section */}
          <div className="border-t border-gray-200 p-6">
            <div className="flex items-center gap-3">
              <div className="flex-1 relative">
                <textarea
                  value={currentMessage}
                  onChange={(e) => setCurrentMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={messages.length === 0 ? "Ask a question about your documents..." : "Type your question..."}
                  className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-none"
                  rows="1"
                  style={{ minHeight: '44px', maxHeight: '120px' }}
                  disabled={isTyping}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!currentMessage.trim() || isTyping}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-400 hover:text-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* Demo Message Examples */}
            {messages.length === 0 && (
              <div className="mt-4">
                <p className="text-xs text-gray-400 mb-2">Try asking:</p>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setCurrentMessage("What are the main topics covered in the uploaded documents?")}
                    className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-full transition-colors"
                  >
                    📄 Document topics
                  </button>
                  <button
                    onClick={() => setCurrentMessage("Search the web for latest information about this topic")}
                    className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-full transition-colors"
                  >
                    🌐 Web search
                  </button>
                  <button
                    onClick={() => setCurrentMessage("Analyze and summarize the key points")}
                    className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-full transition-colors"
                  >
                    🤖 AI analysis
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPopup;