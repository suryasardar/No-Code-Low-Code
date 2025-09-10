// components/NodeTypes/KnowledgeBaseNode.tsx
import React, { memo, useCallback, useRef, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { FileText, Upload, Settings, Trash2, X, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { useWorkflowStore, NodeData, NodeConfig } from '../../store/workflowStore';

// API configuration
const API_BASE_URL = 'http://127.0.0.1:8000';

// UUID validation function
const isValidUUID = (str: string): boolean => {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
};

// API Functions
const uploadDocument = async (file: File, stackId: string, apiKey?: string, embeddingModel?: string) => {
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

export const KnowledgeBaseNode = memo(({ data, id, selected }: NodeProps<NodeData>) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Get state and actions directly from the store
  const selectedWorkflowId = useWorkflowStore((state) => state.selectedWorkflowId);
  const { updateNodeConfig, removeNode } = useWorkflowStore();

  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [uploadError, setUploadError] = useState<string | null>(null);

  const config = data.config || {};

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const stackId = selectedWorkflowId;
    
    if (!stackId || !isValidUUID(stackId)) {
      setUploadStatus('error');
      setUploadError('Workflow must be saved first to have a valid ID for document uploads.');
      return;
    }

    setIsUploading(true);
    setUploadStatus('idle');
    setUploadError(null);

    try {
      // Update UI immediately
      updateNodeConfig(id, { uploadedFileName: file.name });

      const result = await uploadDocument(
        file,
        stackId,
        config.apiKey || undefined,
        config.embeddingModel
      );

      console.log('Upload successful:', result);
      setUploadStatus('success');
      
      updateNodeConfig(id, {
        uploadedFileName: file.name,
        documentId: result.id,
        uploadedAt: new Date().toISOString()
      });

    } catch (error) {
      console.error('Upload failed:', error);
      setUploadStatus('error');
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
      
      updateNodeConfig(id, { uploadedFileName: null, documentId: null, uploadedAt: null });
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } finally {
      setIsUploading(false);
    }
  }, [id, updateNodeConfig, selectedWorkflowId, config.apiKey, config.embeddingModel]);

  const handleRemoveFile = useCallback(() => {
    updateNodeConfig(id, { 
      uploadedFileName: null,
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
  updateNodeConfig(id, { 
    ...data.config,
    [key]: value 
  });
}, [id, updateNodeConfig, data.config]);

  const handleDelete = useCallback(() => {
    removeNode(id);
  }, [id, removeNode]);

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

        {/* Workflow ID */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            Workflow ID
          </label>
          <div className="w-full p-2 border border-gray-300 rounded-md text-sm bg-gray-100 truncate">
            {selectedWorkflowId || 'Not Saved'}
          </div>
          {!selectedWorkflowId && (
            <div className="text-xs text-red-600 mt-1">
              Save your workflow to enable document uploads.
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
              isUploading || !selectedWorkflowId 
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
            disabled={isUploading || !selectedWorkflowId}
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
            value={config.embeddingModel || ''}
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
            value={config.apiKey || ''}
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
