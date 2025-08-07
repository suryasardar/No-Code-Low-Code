// components/NodeTypes/KnowledgeBaseNode.tsx
import React, { memo, useCallback, useRef, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { FileText, Upload, Settings, Trash2, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { useWorkflowStore } from '../../store/workflowStore.ts';
import type { NodeData } from '../../store/workflowStore.ts';
import { useParams } from 'react-router-dom';

// Add the correct type for the workflow store
type WorkflowStore = {
  updateNodeConfig: (id: string, config: Partial<NodeData>) => void;
  removeNode: (id: string) => void;
  // add other properties if needed
};

// API configuration
const API_BASE_URL = 'http://127.0.0.1:8000';

// UUID validation function
const isValidUUID = (str: string): boolean => {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
};

// Generate a valid UUID v4
const generateUUID = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

// API Functions
const uploadDocument = async (file: File, stackId: string, apiKey?: string, embeddingModel?: string) => {
  // Validate stackId is a UUID
  if (!isValidUUID(stackId)) {
    throw new Error(`Invalid stack_id format: ${stackId}. Expected UUID format.`);
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('stack_id', stackId);
  
  if (apiKey) {
    formData.append('api_key', apiKey);
  }
  
  if (embeddingModel) {
    formData.append('embedding_model', embeddingModel);
  }

  const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  return await response.json();
};

const getDocuments = async (stackId: string) => {
  // Validate stackId is a UUID
  if (!isValidUUID(stackId)) {
    throw new Error(`Invalid stack_id format: ${stackId}. Expected UUID format.`);
  }

  const response = await fetch(`${API_BASE_URL}/documents/${stackId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.statusText}`);
  }

  return await response.json();
};

export const KnowledgeBaseNode = memo(({ data, id, selected }: NodeProps<NodeData>) => {
  const { updateNodeConfig, removeNode } = useWorkflowStore() as WorkflowStore;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { workflowId } = useParams();
  console.log('KnowledgeBaseNode workflowId:', workflowId);

  // Upload states
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Ensure we have a valid UUID for stackId
  const getValidStackId = () => {
    const configStackId = data.config?.stackId;
    
    // If config has a valid UUID, use it
    if (configStackId && isValidUUID(configStackId)) {
      return configStackId;
    }
    
    // If workflowId is a valid UUID, use it
    if (workflowId && isValidUUID(workflowId)) {
      return workflowId;
    }
    
    // If node id is a valid UUID, use it
    if (isValidUUID(id)) {
      return id;
    }
    
    // Generate a new UUID as fallback
    const newStackId = generateUUID();
    console.warn(`No valid UUID found for stack_id. Generated new UUID: ${newStackId}`);
    return newStackId;
  };

  const config = {
    embeddingModel: 'text-embedding-3-large',
    apiKey: '',
    uploadedFileName: '',
    uploadedFile: null,
    stackId: workflowId, // Use workflowId as default
    ...data.config, // Spread existing config
    // Override stackId if it's invalid
  };

  // Debug logs
  console.log('KnowledgeBaseNode stackId (workflowId):', workflowId);
  console.log('KnowledgeBaseNode config stackId:', config.stackId);
  // console.log('data.config?.stackId:', data.config?.stackId);

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const stackId = config.stackId || getValidStackId();
    
    // Validate stackId before proceeding
    if (!isValidUUID(stackId)) {
      setUploadError('Invalid stack ID format. Please check your configuration.');
      return;
    }

    setIsUploading(true);
    setUploadStatus('idle');
    setUploadError(null);

    try {
      // Update UI immediately
      updateNodeConfig(id, { 
        uploadedFileName: file.name,
        uploadedFile: file 
      });

      // Upload to server
      const result = await uploadDocument(
        file,
        stackId,
        config.apiKey || undefined,
        config.embeddingModel
      );

      console.log('Upload successful:', result);
      setUploadStatus('success');
      
      // Update config with server response if needed
      updateNodeConfig(id, {
        uploadedFileName: file.name,
        uploadedFile: file,
        documentId: result.id, // Store document ID from server
        uploadedAt: new Date().toISOString()
      });

    } catch (error) {
      console.error('Upload failed:', error);
      setUploadStatus('error');
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
      
      // Reset file on error
      updateNodeConfig(id, { 
        uploadedFileName: null,
        uploadedFile: null 
      });
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } finally {
      setIsUploading(false);
    }
  }, [id, updateNodeConfig, config.stackId, config.apiKey, config.embeddingModel]);

  const handleRemoveFile = useCallback(() => {
    updateNodeConfig(id, { 
      uploadedFileName: null,
      uploadedFile: null,
      documentId: null,
      uploadedAt: null
    });
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setUploadStatus('idle');
    setUploadError(null);
  }, [id, updateNodeConfig]);

  const handleConfigChange = useCallback((key: string, value: any) => {
    updateNodeConfig(id, { [key]: value });
  }, [id, updateNodeConfig]);

  const handleDelete = useCallback(() => {
    removeNode(id);
  }, [id, removeNode]);

  const handleFetchDocuments = useCallback(async () => {
    const stackId = config.stackId || getValidStackId();
    
    if (!isValidUUID(stackId)) {
      console.error('Invalid stack ID format for fetching documents');
      return;
    }

    try {
      const documents = await getDocuments(stackId);
      console.log('Documents fetched:', documents);
      // You can update the node config with fetched documents if needed
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  }, [config.stackId]);

  const getUploadStatusIcon = () => {
    if (isUploading) return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
    if (uploadStatus === 'success') return <CheckCircle className="w-4 h-4 text-green-500" />;
    if (uploadStatus === 'error') return <AlertCircle className="w-4 h-4 text-red-500" />;
    return null;
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg border-2 ${
      selected ? 'border-green-500' : 'border-gray-200'
    } min-w-[320px] hover:shadow-xl transition-all duration-200`}>
      
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="kb-input"
        className="w-3 h-3 !bg-blue-500 !border-2 !border-white cursor-crosshair"
        style={{ left: '-6px' }}
      />
      
      {/* Header */}
      <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-t-lg p-3 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-green-600" />
            <span className="font-semibold text-sm text-gray-800">Knowledge Base</span>
            {getUploadStatusIcon()}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={handleFetchDocuments}
              className="p-1 hover:bg-green-200 rounded transition-colors"
              title="Fetch Documents"
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
        <div className="text-xs text-gray-600">
          Let LLM search info in your file
        </div>

        {/* Stack ID with validation indicator */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Stack ID {!isValidUUID(config.stackId || '') && <span className="text-red-500">(Invalid UUID)</span>}
          </label>
          <input
            type="text"
            value={config.stackId}
            onChange={(e) => handleConfigChange('stackId', e.target.value)}
            placeholder="Enter valid UUID (e.g., 123e4567-e89b-12d3-a456-426614174000)"
            className={`w-full p-2 border rounded-md text-sm focus:ring-2 focus:border-transparent outline-none ${
              isValidUUID(config.stackId || '') 
                ? 'border-gray-300 focus:ring-green-500' 
                : 'border-red-300 focus:ring-red-500'
            }`}
          />
          {!isValidUUID(config.stackId || '') && (
            <div className="text-xs text-red-600 mt-1">
              Stack ID must be a valid UUID format
            </div>
          )}
        </div>

        {/* File Upload */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            File for Knowledge Base
          </label>
          <div
            onClick={() => !isUploading && fileInputRef.current?.click()}
            className={`border-2 border-dashed border-gray-300 rounded-lg p-4 text-center transition-all ${
              isUploading 
                ? 'cursor-not-allowed opacity-50' 
                : 'cursor-pointer hover:border-gray-400 hover:bg-gray-50'
            }`}
          >
            {config.uploadedFileName ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-1">
                  <FileText className="w-5 h-5 text-green-600 flex-shrink-0" />
                  <span className="text-sm text-gray-700 truncate">
                    {config.uploadedFileName}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFile();
                  }}
                  disabled={isUploading}
                  className="p-1 hover:bg-gray-200 rounded ml-2 disabled:opacity-50"
                  title="Remove file"
                >
                  <X className="w-4 h-4 text-gray-500 hover:text-red-600" />
                </button>
              </div>
            ) : (
              <>
                {isUploading ? (
                  <Loader2 className="w-8 h-8 mx-auto mb-2 text-blue-400 animate-spin" />
                ) : (
                  <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                )}
                <p className="text-xs text-gray-500">
                  {isUploading ? 'Uploading...' : 'Upload File'}
                </p>
                <p className="text-xs text-gray-400 mt-1">PDF, TXT, DOC, DOCX</p>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileUpload}
            className="hidden"
            accept=".pdf,.txt,.doc,.docx"
            disabled={isUploading}
          />
        </div>

        {/* Upload Error */}
        {uploadError && (
          <div className="text-xs text-red-600 bg-red-50 p-2 rounded border border-red-200">
            {uploadError}
          </div>
        )}

        {/* Embedding Model */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Embedding Model</label>
          <select
            value={config.embeddingModel}
            onChange={(e) => handleConfigChange('embeddingModel', e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none"
          >
            <option value="text-embedding-3-large">text-embedding-3-large</option>
            <option value="text-embedding-3-small">text-embedding-3-small</option>
            <option value="text-embedding-ada-002">text-embedding-ada-002</option>
            <option value="models/embedding-001">embedding-001 (Free, Recommended)</option>

          </select>
        </div>

        {/* API Key */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">API Key (Optional)</label>
          <input
            type="password"
            value={config.apiKey}
            onChange={(e) => handleConfigChange('apiKey', e.target.value)}
            placeholder="••••••••••••••••••••"
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent outline-none"
          />
        </div>
      </div>
      
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="kb-output"
        className="w-3 h-3 !bg-green-500 !border-2 !border-white cursor-crosshair"
        style={{ right: '-6px' }}
      />
    </div>
  );
});

KnowledgeBaseNode.displayName = 'KnowledgeBaseNode';