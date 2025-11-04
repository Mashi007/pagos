export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {
      // Configuración para evitar propiedades problemáticas
      overrideBrowserslist: [
        'defaults',
        'not IE 11',
        'not op_mini all'
      ],
    },
  },
}
