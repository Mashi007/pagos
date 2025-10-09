FROM node:20-alpine

WORKDIR /app

# Copiar solo el directorio pagos
COPY pagos/package*.json ./
RUN npm ci --only=production

COPY pagos/ ./

# Build si es necesario
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
