import { defineStore } from "pinia"
import { ref, watch } from "vue"

export type ThemeMode = "light" | "dark" | "system"

export const useThemeStore = defineStore("theme", () => {
    // State
    const theme = ref<ThemeMode>("system")
    const isDark = ref(false)

    // Actions
    function setTheme(newTheme: ThemeMode) {
        theme.value = newTheme
        applyTheme()
    }

    function applyTheme() {
        // Determine if we should use dark mode
        if (theme.value === "system") {
            // Use system preference
            isDark.value = window.matchMedia(
                "(prefers-color-scheme: dark)"
            ).matches
        } else {
            // Use explicit setting
            isDark.value = theme.value === "dark"
        }

        document.documentElement.classList.toggle("p-dark", isDark.value)
    }

    // Initialize theme
    function init() {
        // Load theme from localStorage if available
        const savedTheme = localStorage.getItem("theme") as ThemeMode | null
        if (savedTheme && ["light", "dark", "system"].includes(savedTheme)) {
            theme.value = savedTheme
        }

        // Apply the theme
        applyTheme()

        // Watch for system preference changes
        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
        mediaQuery.addEventListener("change", () => {
            if (theme.value === "system") {
                applyTheme()
            }
        })

        // Watch for theme changes to persist to localStorage
        watch(theme, (newTheme) => {
            localStorage.setItem("theme", newTheme)
        })
    }

    return {
        theme,
        isDark,
        setTheme,
        init,
    }
})
