import js from '@eslint/js'
import vuePlugin from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import tsParser from '@typescript-eslint/parser'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import globals from 'globals'

export default [
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'coverage/**',
      'src/views/temp2.vue',
    ],
  },
  {
    files: ['**/*.{js,mjs,cjs}', '**/*.{ts,mts,cts}', '**/*.vue'],
    ...js.configs.recommended,
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
  {
    files: ['**/*.vue', '**/*.{ts,mts,cts}'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
      globals: {
        ...globals.browser,
        ...globals.node,
        defineProps: 'readonly',
        defineEmits: 'readonly',
        defineExpose: 'readonly',
        withDefaults: 'readonly',
      },
    },
    plugins: {
      vue: vuePlugin,
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      ...vuePlugin.configs['vue3-essential'].rules,
      ...tsPlugin.configs.recommended.rules,

      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off',
      'vue/valid-v-for': 'error',
      'vue/no-mutating-props': 'error',

      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-empty-object-type': 'off',

      'no-console': 'off',
      'no-debugger': 'error',
      'no-empty': 'warn',
      'no-useless-catch': 'warn',
      'no-undef': 'off',
    },
  },
  {
    files: ['**/*.vue'],
    rules: {
      '@typescript-eslint/no-unused-vars': 'off',
      'no-unused-vars': 'off',
    },
  },
  {
    files: ['**/*.test.js', '**/*.spec.js', '**/*.test.ts', '**/*.spec.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
]
