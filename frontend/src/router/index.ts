import { createRouter, createWebHistory } from "vue-router"
import type { RouteRecordRaw } from "vue-router"

import Home from "../views/Home.vue"
import Sources from "../views/Sources.vue"
import Rules from "../views/Rules.vue"
import Channels from "../views/Channels.vue"
import TableViewer from "../views/TableViewer.vue"

const routes: RouteRecordRaw[] = [
    { path: "/", name: "Home", component: Home },
    { path: "/sources", name: "Sources", component: Sources },
    { path: "/channels", name: "Channels", component: Channels },
    { path: "/rules", name: "Rules", component: Rules },
    {
        path: "/table/:sourceName/:tableName",
        name: "TableViewer",
        component: TableViewer,
        props: true,
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes,
})

export default router
