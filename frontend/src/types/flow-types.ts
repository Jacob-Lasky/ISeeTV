/**
 * Flow Editor Types - Atomic node definitions for visual rule/plugin editor
 *
 * Following atomic design principles:
 * - Each node type has single responsibility
 * - Clear interfaces and contracts
 * - Modular and extensible architecture
 */

import type { Node, Edge } from "@vue-flow/core"

// Connection validation interfaces
export interface ConnectionValidation {
    validSources?: string[] // Node IDs that can connect to this node
    validTargets?: string[] // Node IDs this node can connect to
    validSourceTables?: string[] // Table names this node can accept
    validTargetTables?: string[] // Table names this node can output
}

// Base node data interface
export interface BaseNodeData {
    label: string
    stats?: {
        processed: number
        passed: number
        caught: number
    }
    isExecuting?: boolean
    lastExecuted?: Date
    validation?: ConnectionValidation
}

// Source node - starting point of the flow
export interface SourceNodeData extends BaseNodeData {
    sourceName: string
    totalRecords: number
    tables: Array<{
        name: string
        recordCount: number
        description?: string
    }>
}

// Rule node - simple pattern matching
export interface RuleNodeData extends BaseNodeData {
    ruleName: string
    pattern: string
    field: string
    table: string
    enabled: boolean
    labels?: {
        match: string // Custom label for when rule matches (default: "passed")
        noMatch: string // Custom label for when rule doesn't match (default: "caught")
    }
}

// Plugin node - complex filtering logic
export interface PluginNodeData extends BaseNodeData {
    pluginName: string
    pluginType: string
    parameters: Record<string, any>
    enabled: boolean
}

// Branch node - logic gates and routing
export interface BranchNodeData extends BaseNodeData {
    branchType: "AND" | "OR" | "NOT"
    condition?: string
}

// Stream node - final output endpoint
export interface StreamNodeData extends BaseNodeData {
    streamType: "accepted" | "rejected"
    description?: string
}

// Node types enum for type safety
export enum FlowNodeType {
    SOURCE = "source",
    RULE = "rule",
    PLUGIN = "plugin",
    BRANCH = "branch",
    STREAM = "stream",
}

// Typed node definitions
export type SourceNode = Node<SourceNodeData, any, FlowNodeType.SOURCE>
export type RuleNode = Node<RuleNodeData, any, FlowNodeType.RULE>
export type PluginNode = Node<PluginNodeData, any, FlowNodeType.PLUGIN>
export type BranchNode = Node<BranchNodeData, any, FlowNodeType.BRANCH>
export type StreamNode = Node<StreamNodeData, any, FlowNodeType.STREAM>

// Union type for all flow nodes
export type FlowNode =
    | SourceNode
    | RuleNode
    | PluginNode
    | BranchNode
    | StreamNode

// Edge data for connections
export interface FlowEdgeData {
    label?: string
    pathType: "passed" | "caught" | "default"
    stats?: {
        recordCount: number
        percentage: number
    }
}

// Typed edge definition
export type FlowEdge = Edge<FlowEdgeData>

// Flow configuration
export interface FlowConfiguration {
    id: string
    name: string
    description?: string
    nodes: FlowNode[]
    edges: FlowEdge[]
    createdAt: Date
    updatedAt: Date
    isActive: boolean
}

// Node creation helpers
export interface NodeCreationOptions {
    position: { x: number; y: number }
    data: Partial<BaseNodeData>
}

// Flow execution result
export interface FlowExecutionResult {
    flowId: string
    executionId: string
    startTime: Date
    endTime?: Date
    status: "running" | "completed" | "failed"
    totalProcessed: number
    totalPassed: number
    totalCaught: number
    nodeResults: Record<
        string,
        {
            processed: number
            passed: number
            caught: number
            executionTime: number
        }
    >
}

// Flow validation result
export interface FlowValidationResult {
    isValid: boolean
    errors: string[]
    warnings: string[]
    suggestions: string[]
}

// Connection validation helpers
export interface ConnectionValidationResult {
    isValid: boolean
    reason?: string
}

// Connection validation functions
export function validateConnection(
    sourceNode: FlowNode,
    targetNode: FlowNode,
    sourceHandle?: string,
    targetHandle?: string
): ConnectionValidationResult {
    // For rule nodes, get table from node data instead of handle name
    let sourceTable: string | null = null
    
    if (sourceNode.type === "rule" && (sourceHandle === "passed" || sourceHandle === "caught")) {
        // Rule nodes output the same table they operate on
        sourceTable = (sourceNode.data as RuleNodeData).table
    } else if (sourceHandle?.startsWith('table-')) {
        // Legacy format: "table-{tableName}"
        sourceTable = sourceHandle.replace('table-', '')
    }

    // For rule-to-rule connections, check table compatibility
    if (sourceNode.type === "rule" && targetNode.type === "rule") {
        const sourceRuleTable = (sourceNode.data as RuleNodeData).table
        const targetRuleTable = (targetNode.data as RuleNodeData).table
        
        if (sourceRuleTable !== targetRuleTable) {
            return {
                isValid: false,
                reason: `Rule tables must match: '${sourceRuleTable}' → '${targetRuleTable}'`
            }
        }
        return { isValid: true }
    }

    // Check if target node can accept this table type
    if (sourceTable && targetNode.data.validation?.validSourceTables) {
        const isTableCompatible = targetNode.data.validation.validSourceTables.includes(sourceTable)
        if (!isTableCompatible) {
            return {
                isValid: false,
                reason: `Table '${sourceTable}' is not compatible with ${targetNode.data.label}`
            }
        }
    }

    // Check node-level validation if specified
    if (sourceNode.data.validation?.validTargets) {
        const isTargetValid = sourceNode.data.validation.validTargets.includes(targetNode.id)
        if (!isTargetValid) {
            return {
                isValid: false,
                reason: `${sourceNode.data.label} cannot connect to ${targetNode.data.label}`
            }
        }
    }

    if (targetNode.data.validation?.validSources) {
        const isSourceValid = targetNode.data.validation.validSources.includes(sourceNode.id)
        if (!isSourceValid) {
            return {
                isValid: false,
                reason: `${targetNode.data.label} cannot accept connections from ${sourceNode.data.label}`
            }
        }
    }

    return { isValid: true }
}
