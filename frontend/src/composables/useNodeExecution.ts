/**
 * Composable for Node Execution API calls
 * 
 * Provides atomic, modular functions for executing individual nodes and partial flows.
 * Follows the user's atomic design principles with single-responsibility functions.
 */

import { ref, type Ref } from 'vue'
import { useToast } from 'primevue/usetoast'

export interface NodeExecutionOptions {
  source: string
  nodeId: string
  flowData: any
  tableName?: string
  limit?: number
}

export interface NodeExecutionConfig {
  onRefresh?: () => Promise<void>
}

export interface NodeExecutionResult {
  success: boolean
  data?: any
  error?: string
}

export function useNodeExecution(config?: NodeExecutionConfig) {
  const toast = useToast()
  const isExecuting = ref(false)
  const executionResult: Ref<NodeExecutionResult | null> = ref(null)

  /**
   * Execute a single node independently
   */
  const executeSingleNode = async (options: NodeExecutionOptions): Promise<NodeExecutionResult> => {
    isExecuting.value = true
    executionResult.value = null

    try {
      const response = await fetch(`/api/${options.source}/flows/nodes/${options.nodeId}/execute?table_name=${options.tableName || 'm3u_channels'}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nodes: options.flowData.nodes,
          edges: options.flowData.edges,
          layout: options.flowData.layout,
          source: options.source,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to execute node: ${response.statusText}`)
      }

      const result = await response.json()
      
      executionResult.value = {
        success: true,
        data: result.data
      }

      // Show success notification
      toast.add({
        severity: 'success',
        summary: 'Node Executed',
        detail: `Successfully executed node with ${result.data?.execution_results?.stats?.total || 0} records processed`,
        life: 3000,
      })

      // Refresh flow data if callback provided
      if (config?.onRefresh) {
        await config.onRefresh()
      }

      return executionResult.value

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      
      executionResult.value = {
        success: false,
        error: errorMessage
      }

      // Show error notification
      toast.add({
        severity: 'error',
        summary: 'Execution Failed',
        detail: errorMessage,
        life: 5000,
      })

      return executionResult.value

    } finally {
      isExecuting.value = false
    }
  }

  /**
   * Execute flow from start up to (and including) the specified node
   */
  const executeFlowToNode = async (options: NodeExecutionOptions): Promise<NodeExecutionResult> => {
    isExecuting.value = true
    executionResult.value = null

    try {
      const response = await fetch(`/api/${options.source}/flows/nodes/${options.nodeId}/execute-to?table_name=${options.tableName || 'm3u_channels'}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nodes: options.flowData.nodes,
          edges: options.flowData.edges,
          layout: options.flowData.layout,
          source: options.source,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to execute flow to node: ${response.statusText}`)
      }

      const result = await response.json()
      
      executionResult.value = {
        success: true,
        data: result.data
      }

      // Show success notification
      toast.add({
        severity: 'success',
        summary: 'Flow Executed',
        detail: `Successfully executed flow up to node with ${result.data?.execution_results?.stats?.total || 0} records processed`,
        life: 3000,
      })

      // Refresh flow data if callback provided
      if (config?.onRefresh) {
        await config.onRefresh()
      }

      return executionResult.value

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      
      executionResult.value = {
        success: false,
        error: errorMessage
      }

      // Show error notification
      toast.add({
        severity: 'error',
        summary: 'Execution Failed',
        detail: errorMessage,
        life: 5000,
      })

      return executionResult.value

    } finally {
      isExecuting.value = false
    }
  }

  /**
   * Execute flow from the specified node to the end
   */
  const executeFlowFromNode = async (options: NodeExecutionOptions): Promise<NodeExecutionResult> => {
    isExecuting.value = true
    executionResult.value = null

    try {
      const response = await fetch(`/api/${options.source}/flows/nodes/${options.nodeId}/execute-from?table_name=${options.tableName || 'm3u_channels'}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nodes: options.flowData.nodes,
          edges: options.flowData.edges,
          layout: options.flowData.layout,
          source: options.source,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to execute flow from node: ${response.statusText}`)
      }

      const result = await response.json()
      
      executionResult.value = {
        success: true,
        data: result.data
      }

      // Show success notification
      toast.add({
        severity: 'success',
        summary: 'Flow Executed',
        detail: `Successfully executed flow from node with ${result.data?.execution_results?.stats?.total || 0} records processed`,
        life: 3000,
      })

      // Refresh flow data if callback provided
      if (config?.onRefresh) {
        await config.onRefresh()
      }

      return executionResult.value

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      
      executionResult.value = {
        success: false,
        error: errorMessage
      }

      // Show error notification
      toast.add({
        severity: 'error',
        summary: 'Execution Failed',
        detail: errorMessage,
        life: 5000,
      })

      return executionResult.value

    } finally {
      isExecuting.value = false
    }
  }

  return {
    // State
    isExecuting,
    executionResult,
    
    // Actions
    executeSingleNode,
    executeFlowToNode,
    executeFlowFromNode,
  }
}
