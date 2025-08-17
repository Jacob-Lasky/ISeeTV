import { apiGet } from "@/utils/apiUtils"
import type { MeiliSearchResponse } from "@/types/types"

export interface SearchQueryParams {
    q: string
    offset?: number
    limit?: number
    filter?: string
    sort?: string[]
    facets?: string[]
}

export async function searchIndex<T = Record<string, any>>(
    source: string,
    index: string,
    params: SearchQueryParams,
    showLoadingToast = false
): Promise<MeiliSearchResponse<T>> {
    const qs = new URLSearchParams()
    if (params.q !== undefined) qs.set("q", params.q)
    if (typeof params.offset === "number") qs.set("offset", String(params.offset))
    if (typeof params.limit === "number") qs.set("limit", String(params.limit))
    if (params.filter) qs.set("filter", params.filter)
    if (params.sort && params.sort.length > 0) {
        for (const s of params.sort) qs.append("sort", s)
    }
    if (params.facets && params.facets.length > 0) {
        for (const f of params.facets) qs.append("facets", f)
    }

    const url = `/api/${encodeURIComponent(source)}/search/${encodeURIComponent(index)}${qs.toString() ? `?${qs.toString()}` : ""}`
    return apiGet<MeiliSearchResponse<T>>(url, showLoadingToast, { showSuccessToast: false })
}
