import { toastService } from "@/services/toastService"
import type { ApiMessage } from "@/types/types"

/**
 * Options for API requests
 */
interface ApiOptions {
    showSuccessToast?: boolean
    showErrorToast?: boolean
    successMessage?: string
    errorPrefix?: string
}

/**
 * Default API options
 */
const defaultApiOptions: ApiOptions = {
    showSuccessToast: true,
    showErrorToast: true,
    successMessage: "Operation completed successfully",
    errorPrefix: "Error",
}

/**
 * Fetch API wrapper with toast notifications
 * @param url - API endpoint URL
 * @param options - Fetch options
 * @param apiOptions - Toast notification options
 * @returns Promise with response data
 */
export async function apiFetch<T = unknown>(
    url: string,
    options?: RequestInit,
    showLoadingToast?: boolean,
    apiOptions: ApiOptions = {}
): Promise<T> {
    // Merge default options with provided options
    const mergedApiOptions = { ...defaultApiOptions, ...apiOptions }

    try {
        // Show loading toast for long operations (optional)
        if (showLoadingToast) {
            toastService.showInfo("Loading...", "Please wait")
        }
        // put a synthetic delay to make the loading visible
        // await new Promise((resolve) => setTimeout(resolve, 1000))

        // Make the API request
        const response = await fetch(url, options)

        // Handle non-OK responses
        if (!response.ok) {
            const errorText = await response.text()
            throw new Error(
                `HTTP ${response.status}: ${errorText || response.statusText}`
            )
        }

        // Parse the response
        const data = await response.json()

        // Show success toast if enabled
        // if it's a post, then the data was saved successfully
        // if it's a get, then the data was gotten from source successfully
        if (mergedApiOptions.showSuccessToast) {
            toastService.showSuccess(
                mergedApiOptions.successMessage || "Success",
                options?.method === "POST"
                    ? "Data saved to file successfully"
                    : options?.method === "GET"
                      ? "Data loaded from file successfully"
                      : undefined
            )
        }

        return data
    } catch (error) {
        // Show error toast if enabled
        if (mergedApiOptions.showErrorToast) {
            const errorMessage =
                error instanceof Error ? error.message : String(error)
            toastService.showError(
                `${mergedApiOptions.errorPrefix || "Error"}`,
                errorMessage
            )
        }

        // Re-throw the error for the caller to handle
        throw error
    }
}

/**
 * GET request with toast notifications
 * @param url - API endpoint URL
 * @param apiOptions - Toast notification options
 * @returns Promise with response data
 */
export function apiGet<T = unknown>(
    url: string,
    showLoadingToast?: boolean,
    apiOptions?: ApiOptions
): Promise<T> {
    return apiFetch<T>(url, { method: "GET" }, showLoadingToast, apiOptions)
}

/**
 * POST request with toast notifications
 * @param url - API endpoint URL
 * @param data - Data to send
 * @param apiOptions - Toast notification options
 * @returns Promise with response data
 */
export function apiPost<T = ApiMessage>(
    url: string,
    data: unknown,
    showLoadingToast?: boolean,
    apiOptions?: ApiOptions
): Promise<T> {
    return apiFetch<T>(
        url,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        },
        showLoadingToast,
        apiOptions
    )
}
