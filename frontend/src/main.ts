import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"

import PrimeVue from "primevue/config"
import Aura from "@primeuix/themes/aura"
import { ConfirmationService, ToastService } from "primevue"

import "primeicons/primeicons.css"

// Optional: switch to 'material', 'lara', or 'nora' later
const app = createApp(App)

app.use(router)
app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: {
            prefix: "p", // default CSS variable prefix
            darkModeSelector: "system", // use user's system theme
            cssLayer: false, // or set to true if you want custom cascade layers
        },
    },
})
app.use(ConfirmationService)
app.use(ToastService)

app.mount("#app")
