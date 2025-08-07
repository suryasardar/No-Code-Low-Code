// components/NodeTypes/index.ts
export { UserQueryNode } from './UserQueryNode';
export { LLMNode } from './LLMEngineNode';
export { KnowledgeBaseNode } from './KnowledgeBaseNode';
export { OutputNode } from './OutputNode';
export { WebSearchNode } from './WebSearchNode';

// Node types registration for React Flow
import { UserQueryNode } from './UserQueryNode';
import { LLMNode } from './LLMEngineNode';
import { KnowledgeBaseNode } from './KnowledgeBaseNode';
import { OutputNode } from './OutputNode';
import { WebSearchNode } from './WebSearchNode';

export const nodeTypes = {
  userQueryNode: UserQueryNode,
  llmNode: LLMNode,
  knowledgeBaseNode: KnowledgeBaseNode,
  outputNode: OutputNode,
  webSearchNode: WebSearchNode,
};