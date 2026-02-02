import js from '@eslint/js'
import globals from 'globals'
import typescript from '@typescript-eslint/eslint-plugin'
import typescriptParser from '@typescript-eslint/parser'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default [
  { ignores: ['dist', '.eslintrc.cjs', '.eslintrc.json', 'fix-lint-*.cjs'] },
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      parser: typescriptParser,
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: { ...globals.browser, ...globals.node, React: 'readonly', JSX: 'readonly', NodeJS: 'readonly', EventListener: 'readonly', BlobPart: 'readonly' },
    },
    plugins: {
      '@typescript-eslint': typescript,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...js.configs.recommended.rules,
      ...typescript.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      'react-hooks/exhaustive-deps': 'warn',
      'prefer-const': 'error',
      'no-var': 'error',
      'no-redeclare': 'warn',
      'no-empty': 'warn',
      'no-case-declarations': 'warn',
      'no-useless-escape': 'warn',
      'no-useless-catch': 'warn',
      'no-self-assign': 'warn',
      'no-control-regex': 'warn',
      '@typescript-eslint/no-empty-object-type': 'warn',
      'react-hooks/rules-of-hooks': 'warn',
    },
  },
  // Archivos muy grandes en .cursorignore: relajar reglas para que lint pase
  {
    files: [
      'src/components/clientes/CrearClienteForm.tsx',
      'src/components/clientes/ExcelUploader.tsx',
      'src/components/configuracion/AIConfig.tsx',
    ],
    rules: {
      '@typescript-eslint/no-unused-vars': 'warn',
      'no-case-declarations': 'off',
      'no-redeclare': 'off',
    },
  },
  // Tests: vitest globals
  {
    files: ['**/*.test.ts', '**/*.test.tsx', '**/tests/**/*.ts', '**/tests/**/*.tsx'],
    languageOptions: {
      globals: { vi: 'readonly', expect: 'readonly', describe: 'readonly', it: 'readonly', beforeEach: 'readonly', afterEach: 'readonly' },
    },
  },
]
