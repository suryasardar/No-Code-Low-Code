-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Stack table
CREATE TABLE IF NOT EXISTS stack (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow table  
CREATE TABLE IF NOT EXISTS workflow (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stack_id UUID NOT NULL REFERENCES stack(id) ON DELETE CASCADE,
    nodes JSONB NOT NULL,
    edges JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES workflow(id) ON DELETE CASCADE,
    key_type TEXT NOT NULL, -- 'llm', 'knowledge', 'websearch'
    encrypted_key TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stack_id UUID NOT NULL REFERENCES stack(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    embedding_id TEXT NOT NULL,
    file_name TEXT,
    file_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat logs table (optional)
CREATE TABLE IF NOT EXISTS chat_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stack_id UUID NOT NULL REFERENCES stack(id) ON DELETE CASCADE,
    user_query TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    execution_time FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_workflow_stack_id ON workflow(stack_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_workflow_id ON api_keys(workflow_id);
CREATE INDEX IF NOT EXISTS idx_documents_stack_id ON documents(stack_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_stack_id ON chat_logs(stack_id);

-- RLS (Row Level Security) policies if needed
-- ALTER TABLE stack ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE workflow ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE chat_logs ENABLE ROW LEVEL SECURITY;