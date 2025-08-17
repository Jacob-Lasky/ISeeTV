import { apiGet } from "@/utils/apiUtils"
import type { TablePageQueryParams, TablePageResponse } from "@/types/types"

export function buildQuery(params: TablePageQueryParams): string {
    const q = new URLSearchParams()
    if (params.page) q.set("page", String(params.page))
    if (params.page_size) q.set("page_size", String(params.page_size))
    if (params.sort_field) q.set("sort_field", params.sort_field)
    if (params.sort_order) q.set("sort_order", params.sort_order)
    if (params.global_filter) q.set("global_filter", params.global_filter)
    if (params.column_filters && Object.keys(params.column_filters).length > 0) {
        q.set("column_filters", JSON.stringify(params.column_filters))
    }
    if (typeof params.apply_rules === "boolean") {
        q.set("apply_rules", String(params.apply_rules))
    }
    if (params.filter_view) q.set("filter_view", params.filter_view)
    const s = q.toString()
    return s
}

export async function fetchTablePage<T = Record<string, any>>(
    source: string,
    table: string,
    params: TablePageQueryParams,
    showLoadingToast = false
): Promise<TablePageResponse<T>> {
    const query = buildQuery(params)
    const url = `/api/${encodeURIComponent(source)}/tables/${encodeURIComponent(
        table
    )}/page${query ? `?${query}` : ""}`
    return apiGet<TablePageResponse<T>>(url, showLoadingToast, {
        showSuccessToast: false,
    })
}
