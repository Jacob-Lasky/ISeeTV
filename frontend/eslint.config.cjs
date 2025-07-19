// eslint.config.cjs

const vue = require("eslint-plugin-vue")
const ts = require("@typescript-eslint/eslint-plugin")
const prettier = require("eslint-plugin-prettier")
const vueRecommended = require("eslint-plugin-vue/lib/configs/vue3-recommended")
const tsRecommended = require("@typescript-eslint/eslint-plugin").configs
    .recommended
const prettierRecommended = require("eslint-plugin-prettier").configs
    .recommended

const config = [
    // Global ignores (applies to everything)
    {
        ignores: [
            "node_modules/",
            "dist/",
            "public/",
            "*.config.js",
            "vite.config.ts",
        ],
    },

    // TypeScript and Vue Single File Components
    {
        files: ["**/*.ts", "**/*.vue"],
        languageOptions: {
            parser: require("vue-eslint-parser"),
            parserOptions: {
                parser: require("@typescript-eslint/parser"),
                ecmaVersion: 2021,
                sourceType: "module",
                project: "./tsconfig.eslint.json",
                extraFileExtensions: [".vue"],
            },
        },
        plugins: {
            vue,
            prettier,
            "@typescript-eslint": ts,
        },
        rules: {
            ...vueRecommended.rules,
            ...tsRecommended.rules,
            ...prettierRecommended.rules,
            "prettier/prettier": "error",

            // TypeScript type safety rules - surface type errors as lint errors
            "@typescript-eslint/no-unsafe-member-access": "error",
            "@typescript-eslint/no-unsafe-assignment": "warn",
            "@typescript-eslint/no-unsafe-call": "warn",
            "@typescript-eslint/no-unsafe-return": "error",
            "@typescript-eslint/no-unsafe-argument": "error",
            "@typescript-eslint/no-explicit-any": "error",
            "@typescript-eslint/strict-boolean-expressions": "error",
            "@typescript-eslint/no-unnecessary-type-assertion": "error",
            "@typescript-eslint/prefer-as-const": "error",
            "@typescript-eslint/no-non-null-assertion": "error",

            // Catch type assignment errors
            "@typescript-eslint/no-misused-new": "error",
            "@typescript-eslint/no-this-alias": "error",
            "@typescript-eslint/prefer-readonly": "error",
        },
    },

    // JavaScript config files (e.g., eslint.config.cjs)
    {
        files: ["**/*.js", "**/*.cjs"],
        languageOptions: {
            ecmaVersion: 2021,
            sourceType: "module",
            globals: {
                console: "readonly",
                module: "readonly",
                require: "readonly",
                __dirname: "readonly",
            },
        },
        plugins: {
            prettier,
            "@typescript-eslint": ts,
        },
        rules: {
            ...prettierRecommended.rules,
            "prettier/prettier": "error",
        },
    },
]

// Downgrade to warnings if ONLY_WARN=true (for development)
if (process.env.ONLY_WARN === "true") {
    const onlyWarn = require("eslint-plugin-only-warn")
    module.exports = onlyWarn(config)
} else {
    module.exports = config
}
