// store/workflowStore.js
import { create } from 'zustand';
import { applyNodeChanges, applyEdgeChanges, addEdge } from 'reactflow';

// ==================== Helper Functions ====================
function getNodeName(type) {
  switch (type) {
    case 'userQueryNode':
      return 'UserQuery';
    case 'knowledgeBaseNode':
      return 'KnowledgeBase';
    case 'llmNode':
      return 'LLMEngine';
    case 'outputNode':
      return 'Output';
    case 'webSearchNode':
      return 'WebSearch';
    default:
      return type;
  }
}

function determineEdgeName(connection, nodes) {
  const { source, target, sourceHandle, targetHandle } = connection;
  const sourceNode = nodes.find((node) => node.id === source);
  const targetNode = nodes.find((node) => node.id === target);

  if (!sourceNode || !targetNode) return 'Unknown';

  // User Query connections
  if (sourceNode.data.type === 'userQueryNode') {
    return 'Query';
  }
  
  // Knowledge Base connections
  if (targetNode.data.type === 'knowledgeBaseNode' && targetHandle === 'kb-input') {
    return 'Query Intake';
  }
  if (sourceNode.data.type === 'knowledgeBaseNode' && sourceHandle === 'kb-output') {
    return 'Context';
  }
  
  // LLM connections
  if (targetNode.data.type === 'llmNode') {
    if (targetHandle === 'context-input') return 'Context';
    if (targetHandle === 'query-input') return 'Query';
  }
  if (sourceNode.data.type === 'llmNode' && sourceHandle === 'llm-output') {
    return 'Answer';
  }
  
  // Output connections
  if (targetNode.data.type === 'outputNode') {
    return 'Final Output';
  }

  return 'Connection';
}

// ==================== TYPE CONVERSION FUNCTIONS ====================

// Convert frontend node types to backend node types
function convertNodeType(type) {
  const typeMapping = {
    'userQueryNode': 'userQuery',
    'outputNode': 'output',
    'llmNode': 'llmEngine',
    'knowledgeBaseNode': 'knowledgeBase',
    'webSearchNode': 'webSearch'
  };
  return typeMapping[type] || type;
}

// Convert backend node types to frontend node types
function convertBackendNodeType(type) {
  const typeMapping = {
    'userQuery': 'userQueryNode',
    'output': 'outputNode', 
    'llmEngine': 'llmNode',
    'knowledgeBase': 'knowledgeBaseNode',
    'webSearch': 'webSearchNode'
  };
  return typeMapping[type] || type;
}

// ==================== CONVERSION FUNCTIONS ====================

// Convert nodes array to dictionary for backend (using node IDs as keys)
function nodesToDict(nodes) {
  const nodesDict = {};
  nodes.forEach((node) => {
    nodesDict[node.id] = {
      id: node.id,
      type: convertNodeType(node.type || node.data?.type), // Convert to backend type
      position: node.position,
      data: {
        ...node.data,
        // Ensure type is set in data as well
        type: convertNodeType(node.data?.type || node.type),
        // Remove file object before sending
        config: node.data?.config ? {
          ...node.data.config,
          uploadedFile: undefined
        } : {}
      }
    };
  });
  return nodesDict;
}

// Convert edges array to dictionary for backend
function edgesToDict(edges) {
  const edgesDict = {};
  edges.forEach(edge => {
    edgesDict[edge.id] = {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle || null,
      targetHandle: edge.targetHandle || null,
      type: edge.type || 'smoothstep',
      data: edge.data || {}
    };
  });
  return edgesDict;
}

// Convert nodes dictionary from backend to array for React Flow
function dictToNodes(nodesDict) {
  if (!nodesDict || typeof nodesDict !== 'object') return [];
  
  return Object.values(nodesDict).map((node) => ({
    id: node.id,
    type: convertBackendNodeType(node.type), // Convert from backend type
    position: node.position || { x: 0, y: 0 },
    data: {
      ...node.data,
      // Ensure frontend type is set
      type: convertBackendNodeType(node.type || node.data?.type)
    }
  }));
}

// Convert edges dictionary from backend to array for React Flow
function dictToEdges(edgesDict) {
  if (!edgesDict || typeof edgesDict !== 'object') return [];
  
  return Object.values(edgesDict).map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle,
    targetHandle: edge.targetHandle,
    type: edge.type || 'smoothstep',
    animated: true,
    style: { stroke: '#FF6B6B', strokeWidth: 2 },
    data: edge.data || {}
  }));
}

// Extract API keys from nodes
function extractApiKeys(nodes) {
  const apiKeys = {
    llm: '',
    knowledge: '',
    websearch: ''
  };

  nodes.forEach(node => {
    if (node.data?.config) {
      const config = node.data.config;
      
      if ((node.data.type === 'llmNode' || node.type === 'llmNode') && config.apiKey) {
        apiKeys.llm = config.apiKey;
      }
      
      if ((node.data.type === 'knowledgeBaseNode' || node.type === 'knowledgeBaseNode') && config.apiKey) {
        apiKeys.knowledge = config.apiKey;
      }
      
      if (((node.data.type === 'llmNode' || node.type === 'llmNode') && config.serpApiKey) || 
          ((node.data.type === 'webSearchNode' || node.type === 'webSearchNode') && config.serpApiKey)) {
        apiKeys.websearch = config.serpApiKey;
      }
    }
  });

  // Only include keys that have values
  const filteredApiKeys = {};
  if (apiKeys.llm) filteredApiKeys.llm = apiKeys.llm;
  if (apiKeys.knowledge) filteredApiKeys.knowledge = apiKeys.knowledge;
  if (apiKeys.websearch) filteredApiKeys.websearch = apiKeys.websearch;

  return filteredApiKeys;
}

// ==================== API Configuration ====================
const API_BASE_URL = 'http://127.0.0.1:8000';

// ==================== Zustand Store ====================
export const useWorkflowStore = create((set, get) => ({
  // State
  selectedWorkflowId: null,
  nodes: [],
  edges: [],
  workflowName: '',
  workflowDescription: '',
  workflowConfig: {},
  draggedType: null,

  // Basic Setters
  setSelectedWorkflowId: (id) => set({ selectedWorkflowId: id }),
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setWorkflowName: (name) => set({ workflowName: name }),
  setWorkflowDescription: (description) => set({ workflowDescription: description }),
  setDraggedType: (type) => set({ draggedType: type }),
  setWorkflowConfig: (config) => set({ workflowConfig: config }),

  // Reset Workflow
  resetWorkflowBuilder: () =>
    set({
      selectedWorkflowId: null,
      nodes: [],
      edges: [],
      workflowName: '',
      workflowDescription: '',
      workflowConfig: {},
      draggedType: null,
    }),

  // Node Management
  addNode: (node) => {
    set((state) => {
      // Initialize config based on node type
      let initialConfig = {};
      
      switch (node.data.type) {
        case 'llmNode':
          initialConfig = {
            model: 'GPT-4o-Mini',
            apiKey: '',
            temperature: '0.7',
            webSearchEnabled: false,
            serpApiKey: '',
            prompt: `You are a helpful AI assistant. Use the provided context to answer questions.

CONTEXT: {context}
User Query: {query}

Please provide a comprehensive answer.`,
          };
          break;
        case 'knowledgeBaseNode':
          initialConfig = {
            embeddingModel: 'text-embedding-3-large',
            apiKey: '',
            uploadedFileName: '',
            uploadedFile: null,
          };
          break;
        case 'userQueryNode':
          initialConfig = {
            query: 'Write your query here',
          };
          break;
        case 'outputNode':
          initialConfig = {
            output: 'Workflow output will appear here.',
          };
          break;
        case 'webSearchNode':
          initialConfig = {
            serpApiKey: '',
          };
          break;
      }

      const nodeWithDefaults = {
        ...node,
        data: {
          ...node.data,
          name: node.data.name || getNodeName(node.data.type),
          config: { ...initialConfig, ...node.data.config },
        },
      };

      return {
        nodes: [...state.nodes, nodeWithDefaults],
      };
    });
  },

  removeNode: (nodeId) =>
    set((state) => ({
      nodes: state.nodes.filter((node) => node.id !== nodeId),
      edges: state.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
    })),

  removeEdge: (edgeId) =>
    set((state) => ({
      edges: state.edges.filter((edge) => edge.id !== edgeId),
    })),

  updateNodeConfig: (nodeId, newConfig) => {
    set((state) => {
      const updatedNodes = state.nodes.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...node.data,
                config: { ...node.data.config, ...newConfig },
              },
            }
          : node
      );

      return {
        nodes: updatedNodes,
      };
    });
  },

  // React Flow Handlers
  onNodesChange: (changes) => {
    set((state) => ({
      nodes: applyNodeChanges(changes, state.nodes),
    }));
  },

  onEdgesChange: (changes) => {
    set((state) => ({
      edges: applyEdgeChanges(changes, state.edges),
    }));
  },

  onConnect: (connection) => {
    set((state) => {
      const edgeName = determineEdgeName(connection, state.nodes);
      const newEdge = {
        ...connection,
        id: `e${connection.source}-${connection.target}-${Date.now()}`,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#FF6B6B', strokeWidth: 2 },
        data: { name: edgeName },
      };

      return {
        edges: addEdge(newEdge, state.edges),
      };
    });
  },

  // ==================== API OPERATIONS ====================
  
  // POST /api/workflow - Save workflow
  saveWorkflow: async () => {
    const state = get();
    
    const workflowId = state.selectedWorkflowId;
    
    if (!workflowId) {
      console.error('No workflow ID set');
      throw new Error('No workflow ID available');
    }

    console.log('Saving workflow with ID:', workflowId);

    // Convert arrays to dictionaries for backend
    const nodesDict = nodesToDict(state.nodes);
    const edgesDict = edgesToDict(state.edges);
    const apiKeys = extractApiKeys(state.nodes);

    const payload = {
      stack_id: workflowId,
      nodes: nodesDict,  // Dictionary with node IDs as keys
      edges: edgesDict,  // Dictionary with edge IDs as keys
      api_keys: Object.keys(apiKeys).length > 0 ? apiKeys : null
    };

    try {
      console.log('Saving workflow with payload:', JSON.stringify(payload, null, 2));
      
      const response = await fetch(`${API_BASE_URL}/api/workflow`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to save workflow:', errorText);
        throw new Error(`Failed to save workflow: ${response.status} ${errorText}`);
      }

      const result = await response.json();
      console.log('Workflow saved successfully:', result);
      
      // Update selectedWorkflowId if API returns a different ID
      if (result.stack_id && result.stack_id !== workflowId) {
        set({ selectedWorkflowId: result.stack_id });
      }
      
      return result;
    } catch (error) {
      console.error('Error saving workflow:', error);
      throw error;
    }
  },

  // GET /api/workflow/{stack_id} - Load workflow
  loadWorkflow: async (workflowId) => {
    try {
      // Skip loading for new/temporary workflows
      if (!workflowId || workflowId === 'new' || workflowId.startsWith('temp_')) {
        set({ selectedWorkflowId: workflowId });
        return true;
      }

      console.log('Loading workflow with ID:', workflowId);
      
      const response = await fetch(`${API_BASE_URL}/api/workflow/${workflowId}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          console.log('Workflow not found, creating new workflow');
          set({ 
            selectedWorkflowId: workflowId,
            nodes: [],
            edges: [],
            workflowName: '',
            workflowDescription: ''
          });
          return true;
        }
        throw new Error(`Failed to load workflow: ${response.status}`);
      }

      const data = await response.json();
      console.log('Loaded workflow data:', data);
      
      // Convert dictionaries from backend to arrays for React Flow
      const nodes = dictToNodes(data.nodes);
      const edges = dictToEdges(data.edges);
      
      console.log('Converted nodes:', nodes);
      console.log('Converted edges:', edges);

      set({
        selectedWorkflowId: data.stack_id || workflowId,
        nodes: nodes,
        edges: edges,
        workflowName: data.name || '',
        workflowDescription: data.description || '',
      });

      return true;
    } catch (error) {
      console.error('Error loading workflow:', error);
      // On error, initialize empty workflow
      set({ 
        selectedWorkflowId: workflowId,
        nodes: [],
        edges: [],
        workflowName: '',
        workflowDescription: ''
      });
      return false;
    }
  },

  // Save and Execute workflow - This combines both operations
  saveAndExecuteWorkflow: async (userQuery) => {
    const state = get();
    
    try {
      console.log('🚀 Starting save and execute workflow process...');
      
      // Step 1: Save the workflow first
      console.log('💾 Step 1: Saving workflow...');
      const saveResult = await state.saveWorkflow();
      
      if (!saveResult) {
        throw new Error('Failed to save workflow');
      }
      
      console.log('✅ Workflow saved successfully, now executing...');
      
      // Step 2: Execute the workflow
      console.log('⚡ Step 2: Executing workflow with query:', userQuery);
      const workflowId = state.selectedWorkflowId;
      
      if (!workflowId) {
        throw new Error('No workflow ID available for execution');
      }

      const executePayload = {
        stack_id: workflowId,
        query: userQuery
      };

      console.log('📡 Sending execute request to:', `${API_BASE_URL}/api/workflow/execute`);
      console.log('📡 Execute payload:', executePayload);

      const executeResponse = await fetch(`${API_BASE_URL}/api/workflow/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(executePayload),
      });

      if (!executeResponse.ok) {
        const errorText = await executeResponse.text();
        console.error('❌ Failed to execute workflow:', errorText);
        throw new Error(`Failed to execute workflow: ${executeResponse.status} ${errorText}`);
      }

      const executeResult = await executeResponse.json();
      console.log('🎉 Workflow executed successfully:', executeResult);
      
      // Update the output node with the result
      if (executeResult.result) {
        const outputNode = state.nodes.find(node => node.type === 'outputNode');
        if (outputNode) {
          console.log('📝 Updating output node with result...');
          state.updateNodeConfig(outputNode.id, {
            output: executeResult.result
          });
        }
      }
      
      return {
        success: true,
        saveResult,
        executeResult,
        message: 'Workflow saved and executed successfully'
      };
      
    } catch (error) {
      console.error('💥 Error in save and execute workflow:', error);
      return {
        success: false,
        error: error.message,
        message: `Failed to save and execute workflow: ${error.message}`
      };
    }
  },
}));