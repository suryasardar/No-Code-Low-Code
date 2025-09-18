// src/components/GenAIStackHomepage.jsx
import React, { useState, useEffect } from "react";
import { Plus, X, ExternalLink, Grid, List, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useWorkflowStore } from "../store/workflowStore";

const GenAIStackHomepage = () => {
  const navigate = useNavigate();
  const { resetWorkflowBuilder } = useWorkflowStore();
  
  const [workflows, setWorkflows] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [newWorkflow, setNewWorkflow] = useState({ name: "", description: "" });
  const [searchTerm, setSearchTerm] = useState("");
  const [viewMode, setViewMode] = useState("grid"); // grid or list
  const [isLoading, setIsLoading] = useState(false);

  // Load saved workflows from API only
  useEffect(() => {
    loadWorkflows();
  }, []);

  const API_BASE_URL = 'http://43.205.119.16:8000';


  const loadWorkflows = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/stack`);
      if (response.ok) {
        const data = await response.json();
        setWorkflows(data.workflows || data || []);
        console.log('Loaded workflows:', data.workflows || data);
         
      } else {
        console.error('Failed to load workflows from API');
        setWorkflows([]);
      }
    } catch (error) {
      console.error('Error loading workflows:', error);
      setWorkflows([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateWorkflow = async () => {
    if (newWorkflow.name.trim()) {
      
      // Create workflow object for API
      const newWorkflowItem = {
        name: newWorkflow.name,
        description: newWorkflow.description,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      try {
        // Save to backend
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/stack`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newWorkflowItem)
        });

        if (response.ok) {
          // Reset form and close modal
          setNewWorkflow({ name: "", description: "" });
          setShowModal(false);

          // Navigate to workflow builder
          resetWorkflowBuilder();
          navigate(`/workflow/${workflows.id}`);
        } else {
          console.error('Failed to create workflow');
          alert('Failed to create workflow. Please try again.');
        }
      } catch (error) {
        console.error('Error creating workflow:', error);
        alert('Error creating workflow. Please check your connection and try again.');
      }
    }
  };

  const handleEditWorkflow = (workflowId) => {
    navigate(`/workflow/${workflowId}`);
  };

  const handleCancel = () => {
    setNewWorkflow({ name: "", description: "" });
    setShowModal(false);
  };

  // Filter workflows based on search
  const filteredWorkflows = workflows.filter(workflow => {
    if (!workflow || typeof workflow !== 'object') return false;
    const name = workflow.name || '';
    const description = workflow.description || '';
    const searchLower = searchTerm.toLowerCase();
    return name.toLowerCase().includes(searchLower) || 
           description.toLowerCase().includes(searchLower);
  });

  return (
    <div className="w-full h-screen bg-gray-50 border border-solid border-black">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 shadow-sm">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center shadow-md">
              <span className="text-white text-lg font-bold">G</span>
            </div>
            <div>
              <span className="text-xl font-bold text-gray-900">GenAI Stack</span>
              {/* <p className="text-xs text-gray-500">Build AI Workflows</p> */}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-purple-500 rounded-full flex items-center justify-center shadow-md">
              <span className="text-white text-sm font-bold">U</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-7xl mx-auto">
          {/* Header with Search */}
          <div className="mb-8">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">My Stacks</h1>
                
              </div>
              
              <div className="flex flex-col sm:flex-row gap-3">
                {/* Search Bar */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    type="text"
                    placeholder="Search workflows..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 w-full sm:w-64"
                  />
                </div>
                 <button
              onClick={() => setShowModal(true)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-all transform hover:scale-105 shadow-md"
            >
              <Plus className="w-4 h-4" />
              <span>New Stack</span>
            </button>
              </div>
            </div>
          </div>

          {/* Loading State */}
          {isLoading ? (
            <div className="flex items-center justify-center min-h-96">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
            </div>
          ) : filteredWorkflows.length === 0 && searchTerm === "" ? (
            // Empty State (only show when not searching)
            <div className="flex flex-col items-center justify-center min-h-96 text-center">
              <div className="bg-white rounded-xl border border-gray-200 p-12 max-w-md shadow-sm">
                <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Plus className="w-10 h-10 text-green-600" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Create Your First Workflow
                </h2>
                <p className="text-gray-600 mb-8">
                  Start building powerful AI workflows with our intuitive drag-and-drop builder
                </p>
                <button
                  onClick={() => setShowModal(true)}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg flex items-center space-x-2 mx-auto transition-all transform hover:scale-105 shadow-md"
                >
                  <Plus className="w-5 h-5" />
                  <span>Create Workflow</span>
                </button>
              </div>
            </div>
          ) : filteredWorkflows.length === 0 && searchTerm !== "" ? (
            // No search results
            <div className="flex flex-col items-center justify-center min-h-96 text-center">
              <div className="bg-white rounded-xl border border-gray-200 p-8 max-w-md shadow-sm">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  No workflows found
                </h3>
                <p className="text-gray-600">
                  No workflows match your search for "{searchTerm}"
                </p>
              </div>
            </div>
          ) : viewMode === 'grid' ? (
            // Grid View
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredWorkflows.map((item) => (
                <div
                  key={item.id || item._id || Math.random()}
                  className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-all hover:border-green-300 group cursor-pointer"
                  onClick={() => handleEditWorkflow(item.id || item._id)}
                >
                  <div className="flex flex-col h-full">
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-3">
                        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-green-600 transition-colors">
                          {item.name || 'Untitled Workflow'}
                        </h3>
                      </div>
                      <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                        {item.description || 'No description available'}
                      </p>
                    </div>

                    <div className="flex gap-2 mt-auto">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditWorkflow(item.id || item._id);
                        }}
                        className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg flex items-center justify-center space-x-2 transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                        <span>Edit Workflow</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            // List View
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredWorkflows.map((item) => (
                    <tr key={item.id || item._id || Math.random()} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {item.name || 'Untitled Workflow'}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-600 max-w-xs truncate">
                          {item.description || 'No description'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">
                          {item.createdAt ? new Date(item.createdAt).toLocaleDateString() : 'N/A'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          onClick={() => handleEditWorkflow(item.id || item._id)}
                          className="text-green-600 hover:text-green-800 font-medium"
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Create Workflow Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-xl w-full p-6 shadow-xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900">
                Create New stack
              </h2>
              <button
                onClick={handleCancel}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-5">
              <div>
                <label className="block text-sm text-left font-medium text-gray-700 mb-2">
                   Name *
                </label>
                <input
                  type="text"
                  value={newWorkflow.name}
                  onChange={(e) =>
                    setNewWorkflow({ ...newWorkflow, name: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  placeholder="your workflow name"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm text-left font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={newWorkflow.description}
                  onChange={(e) =>
                    setNewWorkflow({ ...newWorkflow, description: e.target.value })
                  }
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none"
                  placeholder="Describe what this workflow does..."
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-8">
              <button
                onClick={handleCancel}
                className="px-5 py-2.5 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateWorkflow}
                disabled={!newWorkflow.name.trim()}
                className="px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all transform hover:scale-105 disabled:hover:scale-100"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GenAIStackHomepage;